#!/usr/bin/env python3
"""Generate an UEFI ISO using mtools, dosfstools and xorriso."""
# SPDX-License-Identifier: MIT
import shutil
import subprocess
import sys
from pathlib import Path

if len(sys.argv) != 4:
    sys.exit("Usage: build_iso.py ROOTFS_OUTPUT ISO_PATH KERNEL_BZIMAGE")
work = Path(sys.argv[1]).resolve()
iso = Path(sys.argv[2]).resolve()
kernel = Path(sys.argv[3]).resolve()
here = Path(__file__).resolve().parent
stage = work / "iso-stage"
esp = stage / "efi.img"
boot = stage / "EFI/BOOT"
boot.mkdir(parents=True, exist_ok=True)
for source, target in ((here / "BOOTX64.EFI", "BOOTX64.EFI"),
                       (kernel, "VMLINUZ"), (work / "initrd.img", "INITRD.IMG")):
    if not source.is_file():
        sys.exit(f"Missing required file: {source}")
    shutil.copy2(source, boot / target)
shutil.copy2(here / "README.md", stage / "README.TXT")
# FAT16 ESP, with ample space for the initramfs and kernel.
files = [boot / name for name in ("BOOTX64.EFI", "VMLINUZ", "INITRD.IMG")]
size = sum(f.stat().st_size for f in files)
mib = 1024 * 1024
image_size = max(64 * mib, ((size + 16 * mib + 16 * mib - 1) // (16 * mib)) * 16 * mib)
with esp.open("wb") as f:
    f.truncate(image_size)
subprocess.run(["mkfs.fat", "-F", "16", "-n", "RODSO_BOOT", str(esp)], check=True)
subprocess.run(["mmd", "-i", str(esp), "::/EFI", "::/EFI/BOOT"], check=True)
for f in files:
    subprocess.run(["mcopy", "-i", str(esp), str(f), "::/EFI/BOOT/" + f.name], check=True)
iso.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["xorriso", "-as", "mkisofs", "-R", "-J",
                "-V", "RODSO_LIVE_0_2", "-o", str(iso),
                "-eltorito-alt-boot", "-e", "efi.img", "-no-emul-boot",
                "-isohybrid-gpt-basdat", str(stage)], check=True)
print("Created", iso)
