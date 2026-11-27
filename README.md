# VoxStudy

VoxStudy captura el audio del sistema, lo transcribe localmente con Voxtype y guarda la transcripción en una bóveda de Obsidian. Puede enviar esa transcripción a TokenHarbor para crear una guía de estudio con temas, términos clave, preguntas de práctica y marcas de tiempo.

## Requisitos

- Linux con PipeWire/PulseAudio y `pactl`
- Python 3.11 o posterior
- Voxtype configurado con Whisper local (`engine=whisper`, `whisper.mode=local`)
- FFmpeg con entrada PulseAudio
- Una bóveda de Obsidian

La captura usa el monitor de salida predeterminado y excluye el micrófono. El audio se transcribe localmente y se elimina después de guardar la nota. La guía requiere conexión y una clave de API de TokenHarbor; solo se envía el texto de la transcripción.

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
voxstudy setup --vault /home/greep/Documents/Obsidian/MDY
```

La configuración local queda en `~/.config/voxstudy/config.json`. De forma predeterminada, las transcripciones se guardan en `Transcripciones/` y las guías en `Guías de estudio/`.

## Capturar y transcribir

Ejecuta `voxstudy` sin argumentos para abrir el panel interactivo en la terminal. Muestra la bóveda configurada, el estado de captura y las cinco notas recientes. Pulsa `l` para buscar en la biblioteca; desde una transcripción puedes generar una guía con `g`. En el panel, escribe el título y usa **Iniciar captura** antes de reproducir el video; al terminar, usa **Detener y transcribir**. El panel muestra el progreso por bloques y permanece disponible mientras trabaja. Pulsa `r` para actualizar o `q` para salir. Los subcomandos siguen disponibles para uso directo.

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

La guía usa el modelo `deepseek-v4.1-flash:free` a través de la API compatible con OpenAI de TokenHarbor. Crea un archivo `.env` local a partir de la plantilla y añade allí tu clave nueva:

```bash
cp .env.example .env
nvim .env
```

El archivo `.env` está excluido de Git. No publiques ni compartas su contenido. También puedes exportar `TOKENHARBOR_API_KEY` en el entorno. Luego ejecuta:

```bash
voxstudy guide
```

Sin argumento, se procesa la transcripción más reciente. Para elegir una nota:

```bash
voxstudy guide 2026-11-26-2202-prueba.md
```

La guía se guarda por separado, enlaza a la transcripción original y registra los tokens de entrada y salida informados por TokenHarbor. Incluye resumen, objetivos de aprendizaje, esquema temático, términos clave, relaciones entre ideas, preguntas de práctica y fragmentos dudosos para revisar. Los errores de reconocimiento de nombres propios pueden afectar el resultado; las marcas de tiempo ayudan a comprobarlos en la fuente.

La generación de guías es explícita: `voxstudy stop` solo captura, transcribe y guarda la nota. Para usar otra variante de modelo compatible, indica `--model` al comando `guide`.

## Estructura

- `src/voxstudy/cli.py`: interfaz de línea de comandos.
- `src/voxstudy/ui/`: interfaz interactiva en terminal basada en Textual; contiene el panel, la biblioteca y las vistas de nota.
- `src/voxstudy/application/`: consultas y casos de uso compartidos por las interfaces.
- `src/voxstudy/workflow.py`: coordinación de captura, transcripción y guías.
- `src/voxstudy/adapters/`: integraciones con captura de audio, Voxtype, DeepSeek y Obsidian.
- `src/voxstudy/markdown.py`: formato de las notas.
- `docs/architecture.md`: flujo y límites entre componentes.
