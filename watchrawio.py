#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fast, low-flicker block I/O viewer (Python + curses, stdlib only)

Original Bash script:
  © 2013 Artem S. Tashkinov
  Licensed under the GNU General Public License v2.0 or later (GPL-2.0+)

Python port and enhancements:
  A full rewrite by © 2025-2026 ChatGPT (OpenAI) — contributed under GPL-2.0+,
  permission granted to relicense with the original work.

License:
  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program. If not, see <https://www.gnu.org/licenses/>.

Description:
  Interactive, real-time block I/O monitor without flicker.
  - Natural device sort and partition indenting
  - %util from /proc/diskstats
  - Toggle hide zeros ('0')
  - Toggle show active-only ('A')
  - Instant key response
  - Locale-aware or custom thousands separators
  - Device prefix filtering
"""

import argparse
import curses
import locale
import os
import re
import sys
import time
from collections import defaultdict

DEFAULT_PREFIXES = ["sd", "nvme", "md", "vd", "dm-", "mmcblk"]

DISKSTATS = "/proc/diskstats"
MOUNTS = "/proc/mounts"
SYS_BLOCK = "/sys/block"

# /proc/diskstats field indices (0-based after split())
IDX_NAME = 2
IDX_SEC_READ = 5
IDX_SEC_WRIT = 9
IDX_BUSY_MS = 12

DIGIT_GROUP_RE = re.compile(r"(\d)(?=(\d{3})+(?!\d))")

# Device-family patterns used consistently for:
# - natural sort
# - base device lookup
# - partition detection
_NAT_PATTERNS = [
    re.compile(r"^(nvme\d+n\d+)(?:p(\d+))?$"),
    re.compile(r"^(mmcblk\d+)(?:p(\d+))?$"),
    re.compile(r"^(loop\d+)(?:p(\d+))?$"),
    re.compile(r"^((?:sd|vd|xvd|zd)[a-z]+)(\d+)?$"),
    re.compile(r"^(md\d+)(?:p(\d+))?$"),
    re.compile(r"^(dm-\d+)(?:p(\d+))?$"),
]

hide_zeros = False
show_active_only = False
args = None  # filled in __main__


def parse_args():
    ap = argparse.ArgumentParser(description="Watch block I/O per device without flicker.")
    ap.add_argument("-r", "--refresh", type=float, default=2.0,
                    help="Refresh rate (seconds). Default: 2.0")
    ap.add_argument("--locale", action="store_true",
                    help="Use system locale for digit grouping.")
    ap.add_argument("--sep", type=str, default=None,
                    help="Hardcode thousands separator (e.g. ',', '.', ' ').")
    ap.add_argument("--devices", nargs="*", default=DEFAULT_PREFIXES,
                    help=f"Device name prefixes to include. Default: {', '.join(DEFAULT_PREFIXES)}")
    return ap.parse_args()


def set_locale(use_locale: bool):
    if not use_locale:
        return
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        pass


def group_num(n: int, use_locale: bool, sep: str | None) -> str:
    if sep is not None:
        return DIGIT_GROUP_RE.sub(rf"\1{sep}", str(n))
    if use_locale:
        try:
            return locale.format_string("%d", n, grouping=True)
        except Exception:
            pass
    return f"{n:,}"


def natural_key(devname: str) -> tuple:
    for pat in _NAT_PATTERNS:
        m = pat.match(devname)
        if m:
            base, p = m.group(1), m.group(2)
            return (base, 0, 0) if p is None else (base, 1, int(p))
    return (devname, 0, 0)


def base_of(dev: str) -> str:
    for pat in _NAT_PATTERNS:
        m = pat.match(dev)
        if m:
            return m.group(1)
    return dev


def is_partition(name: str) -> bool:
    for pat in _NAT_PATTERNS:
        m = pat.match(name)
        if m:
            return m.group(2) is not None
    return False


def should_keep(name: str, prefixes: list[str]) -> bool:
    return any(name.startswith(p) for p in prefixes)


def load_lb_sizes(prefixes: list[str]) -> dict[str, int]:
    sizes: dict[str, int] = {}
    try:
        for name in os.listdir(SYS_BLOCK):
            if not any(name.startswith(p) for p in prefixes):
                continue
            p = os.path.join(SYS_BLOCK, name, "queue", "logical_block_size")
            try:
                with open(p, "rt") as f:
                    sizes[name] = int(f.read().strip())
            except Exception:
                sizes[name] = 512
    except FileNotFoundError:
        pass
    return sizes


def resolve_mounts() -> dict[str, str]:
    """
    Map block device name -> mountpoint.

    Examples:
      nvme0n1p1 -> /boot/efi
      dm-0      -> /
    """
    byname: dict[str, str] = {}

    try:
        with open(MOUNTS, "rt") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2:
                    continue
                src, mnt = parts[0], parts[1]

                if src.startswith("/dev/"):
                    try:
                        real = os.path.realpath(src)
                    except Exception:
                        real = src

                    # /dev/dm-0 or /dev/nvme0n1p1 etc.
                    if real.startswith("/dev/"):
                        byname[os.path.basename(real)] = mnt

                    # Also capture the literal basename for things like /dev/mapper/NAME
                    byname[os.path.basename(src)] = mnt

                elif src.startswith("/dev/disk/"):
                    try:
                        real = os.path.realpath(src)
                        if real.startswith("/dev/"):
                            byname[os.path.basename(real)] = mnt
                    except Exception:
                        pass
    except FileNotFoundError:
        pass

    # Fallback for root= on kernel cmdline if not already resolved
    try:
        with open("/proc/cmdline", "rt") as f:
            cmd = f.read()
        m = re.search(r"root=/dev/(\S+)", cmd)
        if m:
            byname.setdefault(m.group(1), "/")
    except Exception:
        pass

    return byname


def resolve_dm_names() -> dict[str, str]:
    """
    Map dm-X -> mapper name from sysfs, e.g.
      dm-0 -> luks-uuid...
      dm-1 -> DEPOT
    """
    out: dict[str, str] = {}
    try:
        for name in os.listdir(SYS_BLOCK):
            if not name.startswith("dm-"):
                continue
            p = os.path.join(SYS_BLOCK, name, "dm", "name")
            try:
                with open(p, "rt") as f:
                    dmname = f.read().strip()
                if dmname:
                    out[name] = dmname
            except Exception:
                pass
    except FileNotFoundError:
        pass
    return out


def resolve_dm_slaves() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """
    Returns:
      dm_to_slaves:  dm-0 -> ['nvme0n1p5']
      slave_to_dms: nvme0n1p5 -> ['dm-0']
    """
    dm_to_slaves: dict[str, list[str]] = {}
    slave_to_dms: dict[str, list[str]] = {}

    try:
        for name in os.listdir(SYS_BLOCK):
            if not name.startswith("dm-"):
                continue

            slaves_dir = os.path.join(SYS_BLOCK, name, "slaves")
            slaves: list[str] = []
            try:
                for slave in sorted(os.listdir(slaves_dir), key=natural_key):
                    slaves.append(slave)
                    slave_to_dms.setdefault(slave, []).append(name)
            except FileNotFoundError:
                pass

            if slaves:
                dm_to_slaves[name] = slaves
    except FileNotFoundError:
        pass

    return dm_to_slaves, slave_to_dms


def read_diskstats() -> list[tuple[str, int, int, int]]:
    """
    Return list of:
      (name, sectors_read, sectors_written, busy_ms)
    """
    out: list[tuple[str, int, int, int]] = []
    try:
        with open(DISKSTATS, "rt") as f:
            for line in f:
                parts = line.split()
                if len(parts) <= IDX_BUSY_MS:
                    continue
                try:
                    name = parts[IDX_NAME]
                    sr = int(parts[IDX_SEC_READ])
                    sw = int(parts[IDX_SEC_WRIT])
                    busy_ms = int(parts[IDX_BUSY_MS])
                except (ValueError, IndexError):
                    continue
                out.append((name, sr, sw, busy_ms))
    except FileNotFoundError:
        pass
    return out


def draw_header(stdscr, rr: float):
    stdscr.addstr(0, 0, time.strftime("Date: %a %b %d %T %Z"))
    stdscr.addstr(0, 35, f"[ refresh rate: {rr:g} s ]")
    stdscr.addstr(
        1, 0,
        "{:<14} {:>17} {:>17} {:>17} {:>17} {:>8} {}".format(
            "Device",
            "Read bytes",
            "Written bytes",
            "Interval read",
            "Interval written",
            "%util",
            "Mount point",
        )
    )


def fmt_val(val: int) -> str:
    if hide_zeros and val == 0:
        return ""
    return group_num(val, args.locale, args.sep)


def fmt_util(val: float) -> str:
    if hide_zeros and abs(val) < 0.0001:
        return ""
    return f"{val:.1f}"


def build_context(name: str,
                  mounts: dict[str, str],
                  dm_names: dict[str, str],
                  slave_to_dms: dict[str, list[str]]) -> str:
    """
    Rightmost column policy:
    - normal devices/partitions: mountpoint if mounted
    - partitions backing dm-X: show -> dm-X and mountpoint/name of that dm
    - dm-X rows: show only their own mountpoint, optionally name if not mounted
    """
    mnt = mounts.get(name, "")

    # dm-X rows: show mountpoint; if unmounted but named, show mapper name.
    if name.startswith("dm-"):
        if mnt:
            return mnt
        return dm_names.get(name, "")

    # Non-dm rows: show own mountpoint plus mapping to dm if any.
    ctx = mnt
    dms = slave_to_dms.get(name, [])
    if dms:
        pieces = []
        for dm in sorted(dms, key=natural_key):
            dm_mnt = mounts.get(dm, "")
            dm_name = dm_names.get(dm, "")
            if dm_mnt:
                pieces.append(f"{dm} ({dm_mnt})")
            elif dm_name:
                pieces.append(f"{dm} [{dm_name}]")
            else:
                pieces.append(dm)

        dm_info = ", ".join(pieces)
        if ctx:
            ctx = f"{ctx} -> {dm_info}"
        else:
            ctx = f"-> {dm_info}"

    return ctx


def main(stdscr, parsed_args):
    global hide_zeros, show_active_only, args
    args = parsed_args

    curses.curs_set(0)
    stdscr.nodelay(True)

    lbsize = load_lb_sizes(args.devices)
    mounts = resolve_mounts()
    dm_names = resolve_dm_names()
    _dm_to_slaves, slave_to_dms = resolve_dm_slaves()

    refresh_meta_every = 20
    iter_no = 0

    prev_r = defaultdict(int)
    prev_w = defaultdict(int)
    prev_busy = defaultdict(int)
    primed = set()

    last_sample = time.monotonic()

    ROW0 = 2

    while True:
        iter_no += 1

        if iter_no % refresh_meta_every == 1:
            mounts = resolve_mounts()
            dm_names = resolve_dm_names()
            _dm_to_slaves, slave_to_dms = resolve_dm_slaves()

        now = time.monotonic()
        elapsed = now - last_sample
        last_sample = now
        if elapsed <= 0:
            elapsed = args.refresh if args.refresh > 0 else 1.0

        stats = read_diskstats()
        stats = [t for t in stats if should_keep(t[0], args.devices)]
        stats.sort(key=lambda t: natural_key(t[0]))

        rows_buf = []         # (name, is_part, active, rendered_line)
        active_bases = set()  # base devices whose partitions were active this tick

        for (name, sr, sw, busy_ms) in stats:
            base = base_of(name)
            is_part = is_partition(name)
            lbs = lbsize.get(base, 512)

            if name not in primed:
                prev_r[name] = sr
                prev_w[name] = sw
                prev_busy[name] = busy_ms
                primed.add(name)
                dr = dw = db = 0
            else:
                dr = max(0, sr - prev_r[name])
                dw = max(0, sw - prev_w[name])
                db = max(0, busy_ms - prev_busy[name])

                prev_r[name] = sr
                prev_w[name] = sw
                prev_busy[name] = busy_ms

            total_r = sr * lbs
            total_w = sw * lbs
            int_r = dr * lbs
            int_w = dw * lbs

            util = (db / (elapsed * 1000.0)) * 100.0 if elapsed > 0 else 0.0
            if util > 100.0:
                util = 100.0

            # util for partitions is usually not very meaningful
            util_display = util if not is_part else 0.0

            ctx = build_context(name, mounts, dm_names, slave_to_dms)
            display_name = ("  " + name) if is_part else name

            line = "{:<14} {:>17} {:>17} {:>17} {:>17} {:>8} {}".format(
                display_name,
                fmt_val(total_r),
                fmt_val(total_w),
                fmt_val(int_r),
                fmt_val(int_w),
                fmt_util(util_display),
                ctx,
            )

            active = (int_r != 0) or (int_w != 0)
            rows_buf.append((name, is_part, active, line))

            if is_part and active:
                active_bases.add(base)

        term_rows = []
        for (name, is_part, active, line) in rows_buf:
            if show_active_only:
                if not (active or (not is_part and name in active_bases)):
                    continue
            term_rows.append((name, line))

        stdscr.erase()
        draw_header(stdscr, args.refresh)

        try:
            hdr = (
                f" hide zeros: {'on' if hide_zeros else 'off'}"
                f" | active-only: {'on' if show_active_only else 'off'} "
            )
            y, x = 0, max(0, curses.COLS - len(hdr) - 1)
            stdscr.addstr(y, x, hdr)
        except curses.error:
            pass

        line_no = ROW0
        for _, line in term_rows:
            try:
                stdscr.addstr(line_no, 0, line)
            except curses.error:
                pass
            line_no += 1

        try:
            stdscr.addstr(
                line_no + 1,
                0,
                "Press 'q' to quit | '0' toggle hide zeros | 'A' show active only"
            )
        except curses.error:
            pass

        stdscr.refresh()

        t_end = time.monotonic() + args.refresh
        while True:
            ch = stdscr.getch()
            if ch in (ord('q'), ord('Q')):
                return
            elif ch == ord('0'):
                hide_zeros = not hide_zeros
                break
            elif ch in (ord('A'), ord('a')):
                show_active_only = not show_active_only
                break

            if time.monotonic() >= t_end:
                break
            time.sleep(0.02)


if __name__ == "__main__":
    args = parse_args()
    set_locale(args.locale)

    if not os.path.exists(DISKSTATS):
        print(f"{DISKSTATS} not found. Are you on Linux?", file=sys.stderr)
        sys.exit(1)

    try:
        curses.wrapper(main, args)
    except KeyboardInterrupt:
        pass
