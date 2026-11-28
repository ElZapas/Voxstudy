# VoxStudy

VoxStudy captura el audio del sistema, lo transcribe localmente con Voxtype y guarda la transcripción en una bóveda de Obsidian. Puede enviar esa transcripción a DeepSeek para crear una guía de estudio con temas, términos clave, preguntas de práctica y marcas de tiempo.

## Requisitos

- Linux con PipeWire/PulseAudio y `pactl`
- Python 3.11 o posterior
- Voxtype configurado con Whisper local (`engine=whisper`, `whisper.mode=local`)
- FFmpeg con entrada PulseAudio
- Una bóveda de Obsidian

La captura usa el monitor de salida predeterminado y excluye el micrófono. El audio se transcribe localmente y se elimina después de guardar la nota. La guía requiere conexión y una clave de API de DeepSeek; solo se envía el texto de la transcripción.

## Instalación

```bash
cd /home/greep/Projects/Coding-Projects/voxstudy
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Configura la bóveda:

```bash
voxstudy setup --vault "/ruta/a/tu/boveda"
```

También puedes abrir `voxstudy` y pulsar `b` en el panel para elegir una bóveda navegando carpetas o escribiendo una ruta. VoxStudy conserva la bóveda configurada hasta que elijas otra. La ruta predeterminada de esta instalación es `/home/greep/Documents/Obsidian/MDY`; cada usuario puede establecer la suya. La configuración local queda en `~/.config/voxstudy/config.json`. De forma predeterminada, las transcripciones se guardan en `Transcripciones/` y las guías en `Guías de estudio/`.

Desde **✎ Prompt** en la barra superior puedes personalizar el prompt de sistema de las guías. Se guarda en `~/.config/voxstudy/guide_prompt.md` y se aplica a las próximas guías. **Restaurar predeterminado** elimina la personalización y vuelve al prompt incluido en VoxStudy.

## Interfaz de terminal

Ejecuta `voxstudy` sin argumentos para abrir la interfaz interactiva (TUI) en la terminal. La barra superior de VoxStudy está disponible en el panel, la biblioteca y las vistas de notas. El tema predeterminado usa la paleta Aether/Omarchy.

| Vista | Contenido |
| --- | --- |
| Panel | Estado de la bóveda y captura, controles para iniciar/detener y cinco notas recientes. |
| Biblioteca | Búsqueda de transcripciones y guías; selecciona una nota para abrir su contenido. |
| Nota | Vista de transcripción o guía; desde una transcripción puedes generar la guía y abrir la nota en Obsidian. |

La barra superior permite volver al panel, abrir la biblioteca, actualizar la vista o salir. Atajos disponibles:

| Tecla | Acción |
| --- | --- |
| `b` | Elegir la carpeta de la bóveda desde el panel. |
| `l` | Abrir la biblioteca desde el panel. |
| `r` | Actualizar el panel. |
| `g` | Generar una guía desde una transcripción. |
| `o` | Abrir la nota actual en Obsidian. |
| `Esc` | Volver a la vista anterior desde biblioteca o nota. |
| `q` | Salir desde el panel. |

En el panel, escribe el título y usa **Iniciar captura** antes de reproducir el video; al terminar, usa **Detener y transcribir**. La interfaz muestra el progreso por bloques y permanece disponible mientras trabaja. Los subcomandos siguen disponibles para uso directo.

Para mostrar una TUI en GitHub sirven dos formatos complementarios: capturas estáticas de las vistas principales y una grabación breve de la navegación. Textual puede exportar la pantalla como SVG, que conserva con nitidez el texto y los bordes; una grabación en asciinema puede mostrar el flujo interactivo. Se pueden guardar en `docs/images/` y enlazar desde aquí cuando estén listas.

Inicia la captura antes de reproducir el video:

```bash
voxstudy start --title "Título del video"
```

Al terminar, detenla y espera a que Voxtype procese los bloques:

```bash
voxstudy stop
```

Consulta el estado de una captura o transcripción pendiente con `voxstudy status`. VoxStudy crea bloques de 30 segundos con marcas de tiempo, guarda el progreso para poder reanudar y limpia el audio temporal al completar la nota.

## Crear una guía de estudio

La guía usa `deepseek-flash` mediante la API oficial de DeepSeek. Crea una clave en [DeepSeek Platform](https://platform.deepseek.com/) y añádela a un archivo `.env` local a partir de la plantilla:

```bash
cp .env.example .env
nvim .env
```

El archivo `.env` está excluido de Git. No publiques ni compartas su contenido. También puedes exportar `DEEPSEEK_API_KEY` en el entorno. Luego ejecuta:

```bash
voxstudy guide
```

Sin argumento, se procesa la transcripción más reciente. Para elegir una nota:

```bash
voxstudy guide 2026-11-26-2202-prueba.md
```

La guía se guarda por separado, enlaza a la transcripción original y registra los tokens de entrada y salida informados por DeepSeek. Incluye resumen, objetivos de aprendizaje, esquema temático, términos clave, relaciones entre ideas, preguntas de práctica y fragmentos dudosos para revisar. Los errores de reconocimiento de nombres propios pueden afectar el resultado; las marcas de tiempo ayudan a comprobarlos en la fuente.

La generación de guías es explícita: `voxstudy stop` solo captura, transcribe y guarda la nota. Para usar otra variante de modelo compatible, indica `--model` al comando `guide`.

## Estructura

- `src/voxstudy/cli.py`: interfaz de línea de comandos.
- `src/voxstudy/ui/`: interfaz interactiva en terminal basada en Textual; contiene el panel, la biblioteca y las vistas de nota.
- `src/voxstudy/ui/theme.py`: paleta Aether/Omarchy usada por defecto.
- `src/voxstudy/application/`: consultas y casos de uso compartidos por las interfaces.
- `src/voxstudy/workflow.py`: coordinación de captura, transcripción y guías.
- `src/voxstudy/adapters/`: integraciones con captura de audio, Voxtype, DeepSeek y Obsidian.
- `src/voxstudy/markdown.py`: formato de las notas.
- `docs/architecture.md`: flujo y límites entre componentes.
