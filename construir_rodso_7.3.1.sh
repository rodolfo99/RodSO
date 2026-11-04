#!/usr/bin/env bash
# RodSO GNU/Linux 0.2 kernel 7.3.1, from official kernel.org sources.
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PROJ="$PWD"
VER="7.3.1"
WORK="$PROJ/compilacion"
SRC_DIR="$WORK/linux-$VER"
OBJ_DIR="$WORK/objetos-linux-$VER"
TARBALL="$PROJ/linux-$VER.tar.xz"
OUT_DIR="$PROJ/resultados"
ISO="$OUT_DIR/RodSO-Live-0.2-Linux-$VER-x86_64-UEFI.iso"
if [[ "$(uname -m)" != "x86_64" ]]; then echo 'Requiere anfitrión Linux x86_64.' >&2; exit 2; fi
for cmd in curl tar xz make gcc ld as flex bison bc openssl python3 cpio gzip find readelf ldd file sha256sum clang lld-link; do
  if ! command -v "$cmd" >/dev/null 2>&1; then echo "Falta $cmd. Instala las dependencias indicadas en LEEME.txt." >&2; exit 2; fi
done
mkdir -p "$WORK" "$OUT_DIR"
if [[ ! -s "$TARBALL" ]]; then
  echo 'Descargando código fuente Linux 7.3.1 desde kernel.org...'
  curl --fail --location --retry 3 --connect-timeout 20 \
    "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-$VER.tar.xz" -o "$TARBALL"
fi
[[ -s "$TARBALL" ]] || { echo 'No hay un paquete Linux 7.3.1 válido' >&2; exit 1; }
tar -tJf "$TARBALL" >/dev/null
if [[ ! -f "$SRC_DIR/Makefile" ]]; then
  echo 'Extrayendo código fuente...'
  tar -xJf "$TARBALL" -C "$WORK"
fi
mkdir -p "$OBJ_DIR"
if [[ ! -s "$OBJ_DIR/.config" ]]; then
  make -C "$SRC_DIR" O="$OBJ_DIR" x86_64_defconfig
fi
C="$SRC_DIR/scripts/config"
[[ -x "$C" ]] || chmod +x "$C"
opts=(
 EFI EFI_STUB BLK_DEV_INITRD RD_GZIP BINFMT_ELF
 DEVTMPFS DEVTMPFS_MOUNT TMPFS PROC_FS SYSFS UNIX INET
 PCI PCIEPORTBUS VT VT_CONSOLE TTY PRINTK
 FB FB_EFI FRAMEBUFFER_CONSOLE DRM DRM_SIMPLEDRM DRM_FBDEV_EMULATION SYSFB SYSFB_SIMPLEFB
 SCSI BLK_DEV_SD ATA SATA_AHCI ATA_PIIX BLK_DEV_NVME
 USB USB_XHCI_HCD USB_XHCI_PCI USB_EHCI_HCD USB_EHCI_PCI
 USB_OHCI_HCD USB_OHCI_HCD_PCI USB_UHCI_HCD USB_STORAGE USB_UAS
 INPUT INPUT_EVDEV INPUT_KEYBOARD HID HID_GENERIC USB_HID
 FAT_FS MSDOS_FS VFAT_FS NLS NLS_CODEPAGE_437 NLS_ISO8859_1
 EXT4_FS EXFAT_FS NTFS3_FS ISO9660_FS
 VIRTIO VIRTIO_PCI VIRTIO_BLK VIRTIO_SCSI
)
"$C" --file "$OBJ_DIR/.config" --disable MODULES --disable DEBUG_INFO --enable DEBUG_INFO_NONE --enable 64BIT --enable EFI_MIXED
for key in "${opts[@]}"; do "$C" --file "$OBJ_DIR/.config" --enable "$key"; done
make -C "$SRC_DIR" O="$OBJ_DIR" olddefconfig
for required in CONFIG_EFI_STUB=y CONFIG_BLK_DEV_INITRD=y CONFIG_RD_GZIP=y CONFIG_USB_XHCI_HCD=y CONFIG_USB_HID=y CONFIG_VFAT_FS=y CONFIG_DEVTMPFS=y CONFIG_FRAMEBUFFER_CONSOLE=y; do
  if ! grep -qx "$required" "$OBJ_DIR/.config"; then
    echo "No se logró activar $required. Revisa las dependencias Kconfig." >&2; exit 3
  fi
done
if grep -qx 'CONFIG_MODULES=y' "$OBJ_DIR/.config"; then echo 'Error: módulos habilitados sin árbol de módulos.' >&2; exit 3; fi
JOBS="${RODSO_JOBS:-$(nproc)}"
if (( JOBS>4 )); then JOBS=4; fi
printf 'Compilando kernel Linux %s (trabajos paralelos: %s)...\n' "$VER" "$JOBS"
make -C "$SRC_DIR" O="$OBJ_DIR" -j"$JOBS" bzImage
KERNEL="$OBJ_DIR/arch/x86/boot/bzImage"
[[ -s "$KERNEL" ]] || { echo 'No se generó bzImage.' >&2; exit 4; }
if ! file "$KERNEL" | grep -q "version $VER"; then
  echo 'La imagen compilada no informa Linux 7.3.1.' >&2; file "$KERNEL"; exit 4
fi
echo 'Compilando cargador UEFI x86-64 de RodSO...'
clang -target x86_64-pc-win32 -ffreestanding -fshort-wchar -fno-stack-protector -mno-red-zone -O2 -c bootx64.c -o "$WORK/bootx64.obj"
lld-link /subsystem:efi_application /entry:EfiMain /nodefaultlib /machine:x64 /out:BOOTX64.EFI "$WORK/bootx64.obj"
mkdir -p "$WORK/rodso"
python3 "$PROJ/build_initramfs.py" "$WORK/rodso"
python3 "$PROJ/build_iso.py" "$WORK/rodso" "$ISO" "$KERNEL"
python3 "$PROJ/verify_iso.py" "$ISO" "$WORK/rodso/initrd.img" "$KERNEL"
sha256sum "$ISO" > "$ISO.sha256"
cp "$OBJ_DIR/.config" "$OUT_DIR/config-linux-$VER.txt"
echo "ISO preparada: $ISO"
echo "Kernel incluido: $(file -b "$KERNEL")"
echo 'IMPORTANTE: la verificación estructural no reemplaza un arranque real en UEFI.'
