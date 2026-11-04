#!/usr/bin/env python3
"""RodSO 0.2: generate a RAM-based GNU/Linux initramfs from the Linux host."""
# SPDX-License-Identifier: MIT
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "rodso-out").resolve()
ROOT = OUT / "rootfs"
ROOT.mkdir(parents=True, exist_ok=True)

for directory in ("usr/bin", "usr/sbin", "usr/lib", "usr/lib64", "etc", "proc", "sys",
                  "dev", "tmp", "run", "root", "mnt/usb"):
    (ROOT / directory).mkdir(parents=True, exist_ok=True)
for src, dst in (("usr/bin", "bin"), ("usr/sbin", "sbin"), ("usr/lib", "lib"), ("usr/lib64", "lib64")):
    link = ROOT / dst
    if not link.exists() and not link.is_symlink():
        link.symlink_to(src)

commands = """bash busybox ls cp mv rm mkdir rmdir touch cat dd date df du chmod chown
head tail sort uniq wc uname whoami env sleep sync printf cut tr tee id pwd
readlink realpath stat mktemp test ln basename dirname seq tty stty true false
sha256sum free find grep sed tar gzip gunzip awk clear less lsblk blkid mount
umount mountpoint dmesg fdisk kill ps file""".split()
copied = set()

def add_command(name):
    src = shutil.which(name)
    if not src:
        print("Optional command missing:", name)
        return
    real = Path(src).resolve()
    dest = ROOT / "usr/bin" / name
    shutil.copy2(real, dest)
    copied.add(name)
    ldd = subprocess.run(["ldd", str(real)], capture_output=True, text=True)
    for libname in re.findall(r"(?:=>\s*)?(/[^\s()]+)", ldd.stdout):
        lib = Path(libname)
        if not lib.exists():
            continue
        if libname.startswith("/lib64/"):
            target = ROOT / "usr/lib64" / lib.name
        elif libname.startswith("/lib/"):
            target = ROOT / "usr/lib" / libname.removeprefix("/lib/")
        else:
            target = ROOT / libname.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(lib.resolve(), target)
    readelf = subprocess.run(["readelf", "-l", str(real)], capture_output=True, text=True)
    match = re.search(r"Requesting program interpreter: (.*?)\]", readelf.stdout)
    if match:
        interp = Path(match.group(1))
        if str(interp).startswith("/lib64/"):
            dest = ROOT / "usr/lib64" / interp.name
        else:
            dest = ROOT / interp.as_posix().lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(interp.resolve(), dest)

for command in commands:
    add_command(command)
for name in ("vi", "poweroff", "reboot", "halt"):
    target = ROOT / "usr/bin" / name
    if not target.exists():
        target.symlink_to("busybox")
(ROOT / "usr/bin/sh").symlink_to("bash")
(ROOT / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n")
(ROOT / "etc/group").write_text("root:x:0:\n")
(ROOT / "etc/hostname").write_text("rodso\n")
(ROOT / "etc/os-release").write_text('NAME="RodSO GNU/Linux"\nVERSION_ID="0.2"\n')
(ROOT / "etc/profile").write_text("""export PATH=/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root USER=root SHELL=/bin/bash TERM=linux
export PS1='RodSO:\\w # '
cd /root
""")
(ROOT / "root/BIENVENIDO.txt").write_text("""RodSO GNU/Linux 0.2 - experimental
ayuda                      Mostrar ayuda
lsblk -f                   Consultar particiones
montar-usb                 Elegir partición y montar en modo escritura
guardar-usb archivo.txt    Guardar archivo en unidad montada
desmontar-usb              Desmontar USB
reboot                     Reiniciar
poweroff                   Apagar
Los archivos en /root se pierden al apagar. ¡Guárdalos en una partición USB!
""")
scripts = {
    "ayuda": "#!/bin/bash\ncat /root/BIENVENIDO.txt\n",
    "montar-usb": """#!/bin/bash
set -u
mkdir -p /mnt/usb
if mountpoint -q /mnt/usb; then echo 'Ya montado'; exit 0; fi
lsblk -o NAME,TYPE,SIZE,FSTYPE,LABEL,TRAN,MOUNTPOINTS
if [ "$#" -gt 0 ]; then dev="$1"; else read -r -p 'Partición /dev/... (Enter cancela): ' dev; fi
[ -n "$dev" ] && [ -b "$dev" ] || { echo 'Dispositivo no válido'; exit 1; }
name="${dev##*/}"
[ -e "/sys/class/block/$name/partition" ] || { echo 'Selecciona partición, no disco completo'; exit 1; }
fs=$(blkid -s TYPE -o value "$dev" 2>/dev/null || :)
case "$fs" in vfat|ext4|ext3|ext2|exfat|ntfs) ;; *) echo "Formato no admitido: $fs"; exit 1;; esac
mount -o rw "$dev" /mnt/usb && echo 'Partición montada en /mnt/usb'
""",
    "guardar-usb": """#!/bin/bash
[ "$#" -eq 1 ] && [ -f "$1" ] || { echo 'Uso: guardar-usb ARCHIVO'; exit 1; }
mountpoint -q /mnt/usb || { echo 'Ejecuta montar-usb primero'; exit 1; }
cp -v -- "$1" /mnt/usb/ && sync
""",
    "desmontar-usb": "#!/bin/bash\nsync\numount /mnt/usb\n",
}
for name, content in scripts.items():
    path = ROOT / "usr/bin" / name
    path.write_text(content)
    path.chmod(0o755)
init = ROOT / "init"
init.write_text("""#!/bin/bash
export PATH=/usr/sbin:/usr/bin:/sbin:/bin TERM=linux
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /dev/pts /dev/shm /run /tmp /root /mnt/usb
mount -t devpts devpts /dev/pts
mount -t tmpfs -o size=128M tmpfs /tmp
exec </dev/console >/dev/console 2>&1
clear
echo '=== RodSO GNU/Linux 0.2 ==='
echo 'Sistema experimental en RAM. Teclea ayuda.'
while :; do
    /bin/bash --login
    echo 'Usa poweroff o reboot para salir.'
done
""")
init.chmod(0o755)
OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "initrd.img").open("wb") as output:
    find = subprocess.Popen(["find", ".", "-print0"], cwd=ROOT, stdout=subprocess.PIPE)
    cpio = subprocess.Popen(["cpio", "--null", "-o", "-H", "newc", "--quiet"],
                            cwd=ROOT, stdin=find.stdout, stdout=subprocess.PIPE)
    find.stdout.close()
    gzip = subprocess.Popen(["gzip", "-1", "-n"], stdin=cpio.stdout, stdout=output)
    cpio.stdout.close()
    assert gzip.wait() == 0 and cpio.wait() == 0 and find.wait() == 0
print("Generated", OUT / "initrd.img", "with", len(copied), "host commands")
