# Arquitectura

VoxStudy separa la interfaz de comandos, los flujos de trabajo, el formato de notas y los adaptadores externos. La configuración y el estado de una captura viven en el directorio del usuario (`~/.config/voxstudy`), mientras que las notas terminadas van a la bóveda indicada.

## Flujo de transcripción

1. `cli.py` recibe `setup`, `start`, `stop` o `status`.
2. `workflow.py` coordina la operación y comprueba la configuración y la sesión.
3. `adapters/audio_capture.py` obtiene el monitor de salida predeterminado y captura con FFmpeg; no captura el micrófono.
4. Al detener, el audio se divide en bloques de 30 segundos. `adapters/voxtype.py` invoca Voxtype con Whisper local para cada bloque.
5. El progreso y los segmentos quedan en el estado local mientras se procesa. `markdown.py` crea una nota con frontmatter y marcas temporales.
6. `adapters/obsidian.py` guarda la nota en la carpeta de transcripciones de la bóveda. Tras guardarla, el flujo elimina los archivos temporales y limpia la sesión.

Si el procesamiento se interrumpe, `status` muestra el progreso y una nueva ejecución de `stop` continúa desde los segmentos completados, siempre que el audio temporal siga disponible.

## Flujo de guía

1. `workflow.py` selecciona una transcripción, por defecto la más reciente.
2. `adapters/obsidian.py` lee el cuerpo de la nota y excluye el frontmatter.
3. `adapters/deepseek.py` envía el texto a la API compatible con OpenAI de TokenHarbor usando `TOKENHARBOR_API_KEY` desde `.env` o el entorno, y solicita una respuesta JSON estructurada en el prompt.
4. `markdown.py` presenta la respuesta como una guía de estudio con enlaces a la transcripción original.
5. `adapters/obsidian.py` guarda la guía en su propia carpeta dentro de la bóveda.

La transcripción se mantiene local durante la captura. La generación de guía es una acción separada y comparte el texto con TokenHarbor; no envía el audio.

## Módulos

| Módulo | Responsabilidad |
| --- | --- |
| `cli.py` | Argumentos y salida para el usuario. |
| `config.py` | Rutas de configuración, bóveda, sesión y estado local. |
| `models.py` | Modelos de configuración, captura y segmentos. |
| `workflow.py` | Coordinación de casos de uso. |
| `adapters/audio_capture.py` | Monitor de audio, FFmpeg y división en bloques. |
| `adapters/voxtype.py` | Comprobación e invocación de Voxtype local. |
| `adapters/deepseek.py` | Petición compatible con OpenAI a TokenHarbor y validación básica de la respuesta estructurada. |
| `adapters/obsidian.py` | Lectura y escritura de notas en la bóveda. |
| `markdown.py` | Renderizado Markdown de transcripciones y guías. |

## Decisiones actuales

- La captura selecciona el monitor predeterminado de PipeWire/PulseAudio.
- Voxtype y Whisper se ejecutan localmente para transcribir.
- Los bloques de transcripción duran 30 segundos y se conservan como referencias temporales.
- Las guías son optativas y se generan bajo demanda.
- Las notas de transcripción y las guías son archivos independientes para preservar la fuente original.
- La clave de TokenHarbor se lee desde `.env` o una variable de entorno; no forma parte de la configuración ni debe incluirse en el repositorio.
