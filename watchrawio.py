#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fast, low-flicker block I/O viewer (Python + curses, stdlib only)

Original Bash script:
  Copyright (C) 2013-2025 Artem S. Tashkinov
  Licensed under the GNU General Public License v2.0 or later (GPL-2.0+)

Python port and enhancements:
  Portions © 2025 ChatGPT5 (OpenAI) — contributed under GPL-2.0+,
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
  - Device prefix filtering (default: physical block devices)
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

# Field indices in /proc/diskstats (Linux kernel docs):
# 0 major, 1 minor, 2 name, 3 reads_completed, 4 reads_merged,
# 5 sectors_read, 6 time_reading_ms, 7 writes_completed, 8 writes_merged,
# 9 sectors_written, 10 time_writing_ms, ...
IDX_NAME = 2
IDX_SEC_READ = 5
IDX_SEC_WRIT = 9

NVME_PART_RE = re.compile(r"^(nvme.+?)p\d+$")
DIGIT_GROUP_RE = re.compile(r"(\d)(?=(\d{3})+(?!\d))")

hide_zeros = False
show_active_only = False

def is_partition(name: str) -> bool:
    return base_of(name) != name

# Put these near the other regex/constants
_NAT_PATTERNS = [
    re.compile(r'^(nvme\d+n\d+)(?:p(\d+))?$'),
    re.compile(r'^(mmcblk\d+)(?:p(\d+))?$'),
    re.compile(r'^(loop\d+)(?:p(\d+))?$'),
    re.compile(r'^((?:sd|vd|xvd|zd)[a-z]+)(\d+)?$'),
    re.compile(r'^(md\d+)(?:p(\d+))?$'),
    re.compile(r'^(dm-\d+)(?:p(\d+))?$'),
]

def natural_key(devname: str) -> tuple:
    """Sort base devices first, then their partitions numerically."""
    for pat in _NAT_PATTERNS:
        m = pat.match(devname)
        if m:
            base, p = m.group(1), m.group(2)
            if p is None:
                return (base, 0, 0)
            return (base, 1, int(p))
    # Fallback: keep as-is
    return (devname, 0, 0)

def base_of(dev: str) -> str:
    """Return the base device for lbsize lookups (nvme0n1p2 -> nvme0n1, sda1 -> sda, etc.)."""
    for pat in _NAT_PATTERNS:
        m = pat.match(dev)
        if m:
            return m.group(1)
    return dev  # unknown pattern: treat as base

def is_partition(name: str) -> bool:
    """Classify partitions precisely across device families."""
    if re.match(r'^nvme\d+n\d+p\d+$', name): return True
    if re.match(r'^mmcblk\d+p\d+$', name):   return True
    if re.match(r'^loop\d+p\d+$', name):     return True
    if re.match(r'^((?:sd|vd|xvd|zd)[a-z]+)\d+$', name): return True
    if re.match(r'^(md\d+|dm-\d+)p\d+$', name): return True
    return False

def parse_args():
    ap = argparse.ArgumentParser(description="Watch block I/O per device without flicker.")
    ap.add_argument("-r", "--refresh", type=float, default=2.0, help="Refresh rate (seconds). Default: 2.0")
    ap.add_argument("--locale", action="store_true", help="Use system locale for digit grouping.")
    ap.add_argument("--sep", type=str, default=None, help="Hardcode thousands separator (e.g., ',', '.', ' ').")
    ap.add_argument("--devices", nargs="*", default=DEFAULT_PREFIXES,
                    help=f"Device name prefixes to include. Default: {', '.join(DEFAULT_PREFIXES)}")
    return ap.parse_args()


def set_locale(use_locale: bool):
    if not use_locale:
        return
    try:
        # '' => use environment (LC_ALL/LC_NUMERIC/LANG)
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error:
        # Fall back silently; grouping will still work with custom sep or commas.
        pass


def group_num(n: int, use_locale: bool, sep: str | None) -> str:
    """Format integer with thousands grouping."""
    if sep is not None:
        # Hardcoded separator (no locale): insert every 3 digits
        s = str(n)
        return DIGIT_GROUP_RE.sub(rf"\1{sep}", s)
    if use_locale:
        # Locale-aware grouping
        try:
            return locale.format_string("%d", n, grouping=True)
        except Exception:
            pass
    # Default: comma
    return f"{n:,}"


def base_of(dev: str) -> str:
    # sdX1 -> sdX, vdX1 -> vdX, dm-0 -> dm-0, nvme0n1p2 -> nvme0n1
    m = NVME_PART_RE.match(dev)
    if m:
        return m.group(1)
    # strip trailing digits for typical devices (sdX1, vdX1, xvdX1, etc.)
    i = len(dev) - 1
    while i >= 0 and dev[i].isdigit():
        i -= 1
    return dev if i == len(dev) - 1 else dev[:i + 1]


def load_lb_sizes(prefixes: list[str]) -> dict[str, int]:
    """Read logical block size per base device from /sys/block."""
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
    """Map device name (e.g., sda1, nvme0n1p2, dm-0) to mountpoint."""
    byname: dict[str, str] = {}
    try:
        with open(MOUNTS, "rt") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 2:
                    continue
                src, mnt = parts[0], parts[1]
                if src.startswith("/dev/"):
                    name = os.path.basename(src)
                    byname[name] = mnt
                elif src.startswith("/dev/disk/"):
                    # resolve symlink if possible
                    try:
                        real = os.path.realpath(src)
                        if real.startswith("/dev/"):
                            name = os.path.basename(real)
                            byname[name] = mnt
                        # also record the mapper name, e.g., /dev/mapper/vg-lv
                        if real.startswith("/dev/mapper/"):
                            mapper = os.path.basename(real)
                            byname[mapper] = mnt
                    except Exception:
                        pass
    except FileNotFoundError:
        pass

    # kernel cmdline root fallback
    try:
        with open("/proc/cmdline", "rt") as f:
            cmd = f.read()
        m = re.search(r"root=/dev/(\S+)", cmd)
        if m:
            byname.setdefault(m.group(1), "/")
    except Exception:
        pass
    return byname


def read_diskstats() -> list[tuple[str, int, int, int]]:
    """Return list of (name, sectors_read, sectors_written, busy_ms)."""
    out: list[tuple[str, int, int, int]] = []
    try:
        with open(DISKSTATS, "rt") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 13:  # sanity check
                    continue
                name = parts[IDX_NAME]
                try:
                    sr = int(parts[IDX_SEC_READ])
                    sw = int(parts[IDX_SEC_WRIT])
                    busy_ms = int(parts[12])  # time spent doing I/Os
                except ValueError:
                    continue
                out.append((name, sr, sw, busy_ms))
    except FileNotFoundError:
        pass
    return out


def should_keep(name: str, prefixes: list[str]) -> bool:
    return any(name.startswith(p) for p in prefixes)


def draw_header(stdscr, rr: float):
    stdscr.addstr(0, 0, time.strftime("Date: %a %b %d %T %Z"))
    stdscr.addstr(0, 35, f"[ refresh rate: {rr:g} s ]")
    stdscr.addstr(
        1, 0,
        "{:<14} {:>17} {:>17} {:>17} {:>17} {:>8} {}".format(
            "Device", "Read bytes", "Written bytes", "Interval read", "Interval written", "%util", "Mount point"
        )
    )

def fmt_val(val):
    if hide_zeros and val == 0:
        return ""
    return group_num(val, args.locale, args.sep)

def fmt_util(val):
    if hide_zeros and abs(val) < 0.0001:
        return ""
    return f"{val:.1f}" # one decimal, no float garbage

def main(stdscr, args):
    import curses, time
    from collections import defaultdict

    # We assign to these, so declare globals (you said you made them global).
    global hide_zeros, show_active_only
    try:
        hide_zeros
    except NameError:
        hide_zeros = False
    try:
        show_active_only
    except NameError:
        show_active_only = False

    # Curses setup
    curses.curs_set(0)
    stdscr.nodelay(True)

    # Caches & state
    lbsize = load_lb_sizes(args.devices)
    mounts = resolve_mounts()
    mount_refresh_every = 20
    iter_no = 0

    prev_r   = defaultdict(int)
    prev_w   = defaultdict(int)
    prev_busy = defaultdict(int)
    primed = set()  # devices we’ve initialized

    ROW0 = 2  # first row after header

    while True:
        iter_no += 1
        if iter_no % mount_refresh_every == 1:
            mounts = resolve_mounts()

        # Read all stats once, filter, and natural-sort
        stats = read_diskstats()  # [(name, sr, sw, busy_ms), ...]
        stats = [t for t in stats if should_keep(t[0], args.devices)]
        stats.sort(key=lambda t: natural_key(t[0]))

        # Build rows with activity flags; remember if any partition of a base was active
        rows_buf = []           # (name, base, is_part, active, line)
        base_has_active = {}    # base_name -> True if any child active this tick

        for (name, sr, sw, busy_ms) in stats:
            base   = base_of(name)
            is_part = is_partition(name)
            lbs    = lbsize.get(base, 512)

            dr = max(0, sr - prev_r[name])
            dw = max(0, sw - prev_w[name])
            db = max(0, busy_ms - prev_busy[name])

            prev_r[name]    = sr
            prev_w[name]    = sw
            prev_busy[name] = busy_ms

            total_r = sr * lbs
            total_w = sw * lbs
            int_r   = dr * lbs
            int_w   = dw * lbs

            # util% over the nominal refresh (Option A)
            util = (db / (args.refresh * 1000.0)) * 100.0
            if util > 100.0:
                util = 100.0
            util_display = util if not is_part else 0.0

            mnt = mounts.get(name, "")
            display_name = ("  " + name) if is_part else name

            # NOTE: fmt_val / fmt_util return STRINGS; use {:>..} (no .1f here)
            line = "{:<14} {:>17} {:>17} {:>17} {:>17} {:>8} {}".format(
                display_name,
                fmt_val(total_r),
                fmt_val(total_w),
                fmt_val(int_r),
                fmt_val(int_w),
                fmt_util(util_display),
                mnt
            )

            active = (int_r != 0) or (int_w != 0)
            rows_buf.append((name, base, is_part, active, line))
            if is_part and active:
                base_has_active[base] = True

        # Apply "active-only" filter while keeping active bases visible if any child is active
        term_rows = []
        for (name, base, is_part, active, line) in rows_buf:
            if show_active_only:
                if not (active or (not is_part and base_has_active.get(name, False))):
                    continue
            term_rows.append((name, line))

        # Render
        stdscr.erase()
        draw_header(stdscr, args.refresh)  # your existing header function
        # Optionally show toggle states on the right:
        try:
            hdr = f" hide zeros: {'on' if hide_zeros else 'off'} | active-only: {'on' if show_active_only else 'off'} "
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
            stdscr.addstr(line_no + 1, 0, "Press 'q' to quit | '0' toggle hide zeros | 'A' show active only")
        except curses.error:
            pass

        stdscr.refresh()

        # Key handling with timeout until next refresh
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

    # Basic sanity: require /proc/diskstats
    if not os.path.exists(DISKSTATS):
        print(f"{DISKSTATS} not found. Are you on Linux?", file=sys.stderr)
        sys.exit(1)

    try:
        curses.wrapper(main, args)
    except KeyboardInterrupt:
        pass
