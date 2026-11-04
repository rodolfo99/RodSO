#!/usr/bin/env python3
"""Basic ISO9660/El Torito payload checks; not a boot test."""
# SPDX-License-Identifier: MIT
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    sys.exit("Usage: verify_iso.py ISO INITRD KERNEL")
iso, initrd, kernel = [Path(x) for x in sys.argv[1:]]
for p in (iso, initrd, kernel):
    assert p.is_file() and p.stat().st_size > 0, f"Missing {p}"
with iso.open("rb") as fp:
    fp.seek(16 * 2048)
    assert fp.read(7) == b"\x01CD001\x01", "Invalid ISO9660 volume descriptor"
    fp.seek(17 * 2048)
    assert fp.read(7) == b"\x00CD001\x01", "Missing El Torito descriptor"
listed = subprocess.run(["xorriso", "-indev", str(iso), "-find", "/", "-type", "f", "-print"],
                        check=True, text=True, capture_output=True).stdout.upper()
for name in ("EFI/BOOT/BOOTX64.EFI", "EFI/BOOT/VMLINUZ", "EFI/BOOT/INITRD.IMG", "EFI.IMG"):
    assert name in listed, f"Missing ISO file: {name}"
print("ISO9660/El Torito and expected files: PASS")
print("UEFI boot and kernel 7.3.1 execution: NOT TESTED")
