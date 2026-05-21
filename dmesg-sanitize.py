#!/usr/bin/env python3
# 2026-05-21 Gemini 3.5 Flash

import sys
import re
import argparse

# --- Compiled Regex Patterns for Performance ---

# 1. Matches 36-character standard UUID / GUID patterns
UUID_REGEX = re.compile(
    r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b'
)

# 2. Matches standard 6-byte MAC addresses separated by colons or hyphens
MAC_REGEX = re.compile(
    r'\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b'
)

# 3. Matches explicit serial keys (e.g., "SerialNumber: XYZ" or "SerialNumber=XYZ")
# Avoids matching standalone driver names like "Serial: 8250"
SERIAL_KEYWORD_REGEX = re.compile(
    r'(?i)\b(serial\s*num(?:ber)?\s*[:=]\s*)([a-zA-Z0-9_\-\.\:]+)'
)

# Non-unique serial exceptions that should NOT be redacted
SAFE_SERIAL_EXCEPTIONS = [
    re.compile(r'^0000:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9a-fA-F]$'), # PCI Address template
    re.compile(r'^200901010001$'),                                   # Generic default fallback
    re.compile(r'^\d{1,3}$'),                                        # Descriptor index mappings (e.g., SerialNumber=1)
]

def redact_serial(match):
    """Smart replacement function for handling serial numbers."""
    prefix = match.group(1)
    value = match.group(2).strip()
    
    # If it matches any of our safe exclusions, leave it unmodified
    if any(pattern.match(value) for pattern in SAFE_SERIAL_EXCEPTIONS):
        return match.group(0)
    
    return f"{prefix}[redacted]"

def should_drop_line(line):
    """Evaluates whether the row contains audit or user-space daemon contexts."""
    # Remove audit lines completely
    if "audit: type=" in line:
        return True
    
    # Remove systemd and systemd-journald logs completely
    if "systemd[" in line or "systemd-journald[" in line:
        return True
    
    return False

def process_line(line):
    """Applies clean-up operations on a single line string."""
    # 1. Drop line check
    if should_drop_line(line):
        return None
    
    # 2. Redact UUIDs (Except harmless static wmi_bus structural paths)
    if "wmi_bus" not in line:
        line = UUID_REGEX.sub("[redacted]", line)
    
    # 3. Redact MAC addresses
    line = MAC_REGEX.sub("[redacted]", line)
    
    # 4. Redact Smart Serials
    line = SERIAL_KEYWORD_REGEX.sub(redact_serial, line)
    
    return line

def process_stream(stream):
    """Processes open text streams sequentially to stdout."""
    for line in stream:
        cleaned = process_line(line)
        if cleaned is not None:
            sys.stdout.write(cleaned)

def main():
    parser = argparse.ArgumentParser(
        description="Sanitize dmesg outputs automatically by removing specified PII markers."
    )
    parser.add_argument(
        'files', 
        nargs='*', 
        help="Optional log files to process. If empty, the script defaults to reading stdin."
    )
    args = parser.parse_args()

    try:
        if args.files:
            # Loop through file paths passed as arguments
            for file_path in args.files:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    process_stream(f)
        else:
            # Fall back to stdin processing if no arguments are given
            process_stream(sys.stdin)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
