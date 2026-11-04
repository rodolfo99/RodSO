# RodSO GNU/Linux

**RodSO 0.2** es un proyecto experimental de sistema operativo *live*, basado en el kernel Linux y herramientas GNU, pensado para arrancar desde una memoria USB en equipos **x86-64 con UEFI**.

## Estado

Este repositorio contiene el **código fuente y los scripts de construcción** para una imagen ISO que utiliza **Linux 7.3.1**. **No incluye** el código del kernel, una ISO compilada ni garantías de arranque. El constructor descarga el kernel desde kernel.org, lo compila y genera una ISO. La compilación completa y el arranque UEFI de RodSO con Linux 7.3.1 **todavía no se han probado**.

## Contenido

- `bootx64.c`: cargador de arranque UEFI propio (código fuente).
- `construir_rodso_7.3.1.sh`: descarga, configura y compila Linux 7.3.1; prepara la ISO.
- `build_initramfs.py`: construye el sistema GNU en RAM usando herramientas del anfitrión.
- `build_iso.py`: genera ISO9660 con entrada El Torito UEFI y partición FAT16 EFI.
- `verify_iso.py`: comprobaciones estructurales del contenedor ISO/EFI.
- `LEEME.txt`: guía detallada de construcción, uso y limitaciones.

## Construcción en Ubuntu x86-64

```bash
sudo apt update
sudo apt install -y build-essential bc bison flex libssl-dev libelf-dev \
    cpio gzip curl xz-utils python3 file binutils busybox tar \
    util-linux coreutils grep sed gawk findutils clang lld libarchive13
chmod +x construir_rodso_7.3.1.sh
./construir_rodso_7.3.1.sh
```

El constructor crea `BOOTX64.EFI` desde `bootx64.c` con Clang/LLD, obtiene el kernel oficial y genera:

`resultados/RodSO-Live-0.2-Linux-7.3.1-x86_64-UEFI.iso`

**Atención:** este proyecto es experimental. Prueba primero la ISO en una VM UEFI. No se incluye un instalador y el escritorio no es gráfico. Secure Boot debe estar desactivado para este cargador sin firma. El sistema corre en RAM; para persistencia hay que montar conscientemente una partición escribible y guardar allí los archivos.

## Licencias

El código original de RodSO se publica bajo la licencia MIT (consulta `LICENSE`). El kernel Linux tiene su propia licencia GPL-2.0-only. Las herramientas GNU y otras dependencias conservan sus licencias respectivas. El repositorio no incorpora el código fuente ni binarios redistribuidos de Linux o las herramientas GNU.
