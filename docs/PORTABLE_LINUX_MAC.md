# EvalúaFP: distribución portátil Linux y macOS

Estas compilaciones se crean en GitHub Actions sobre el sistema operativo real. **No son instaladores de Windows** y no pueden ejecutarse en otro SO.

## Linux (x64)

1. Descargue `EvaluaFPCanarias_Portatil_1.0.6_linux_x64.tar.gz` y extráigalo en una carpeta que permita ejecución.
2. Abra una terminal dentro de esa carpeta y ejecute `./INICIAR_EVALUAFP.sh`.
3. El programa necesita una sesión gráfica, bibliotecas del sistema Qt/X11 y permisos de escritura en la ubicación elegida. No requiere instalar Python.
4. Si copia la carpeta completa a un USB, mantenga juntas `EvaluaFPCanarias.portable.json`, `EvaluaFPCanarias_Datos` y `EvaluaFPCanarias_Copias`. Evite unidades montadas con `noexec`.

No se garantiza compatibilidad con todas las distribuciones. La compilación CI utiliza Ubuntu 22.04 x64 y debe probarse en las distribuciones de destino.

## macOS (Intel / Apple Silicon)

1. Descargue el ZIP para su arquitectura: `macos_x64` (Intel) o `macos_arm64` (Apple Silicon).
2. Extraiga **toda la carpeta** a una ubicación con permisos de escritura.
3. Inicie `EvaluaFPCanarias_Portatil.app`, o utilice `INICIAR_EVALUAFP.command` si necesita fijar expresamente la carpeta de datos del USB.
4. Conserve los directorios `EvaluaFPCanarias_Datos` y `EvaluaFPCanarias_Copias` al lado de la aplicación. Nunca modifique el interior del paquete `.app`.

**Seguridad de macOS:** los primeros binarios carecen de firma de desarrollador y notarización de Apple. Gatekeeper puede impedir su apertura. Antes de publicar una edición general es recomendable firmar y notarizar la aplicación; no se debe recomendar a los usuarios desactivar Gatekeeper globalmente.

## Seguridad y portabilidad

- Las claves API portátiles se guardan cifradas y se desbloquean con contraseña maestra; la contraseña no se guarda.
- Los originales y calificaciones **no quedan cifrados** por el hecho de llevarse en un USB: use un dispositivo cifrado.
- SQLite y las copias de seguridad son independientes de la letra de unidad o del punto de montaje.
- Detenga EvalúaFP antes de retirar la unidad. Conserve copias en otra ubicación física.
- La compilación y `--selftest` no sustituyen una prueba visual de la ventana nativa, de las importaciones ni de las llamadas reales de IA.

## Compilar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
python scripts/build_portable_unix.py --test
```

En Linux las librerías necesarias de Qt/WebEngine deben estar disponibles. En macOS PyObjC/WebKit. **PyInstaller no permite compilar macOS desde Windows ni Linux desde macOS**: cree cada paquete en su sistema operativo.

Para compilar automáticamente: GitHub → **Actions → Compilar portátiles Linux y macOS → Run workflow**. Al terminar, descargue los artefactos y suba los ZIP/TAR.GZ a la carpeta `descargas/` de la landing. El instalador de Windows y su script no se modifican.
