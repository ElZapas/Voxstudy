# Arquitectura

VoxStudy separa las interfaces de usuario, los flujos de trabajo, el formato de notas y los adaptadores externos. `cli.py` mantiene los subcomandos de terminal y abre la aplicación Textual cuando se ejecuta `voxstudy` sin argumentos. La configuración y el estado de una captura viven en el directorio del usuario (`~/.config/voxstudy`), mientras que las notas terminadas van a la bóveda indicada.

## Flujo de transcripción

1. `cli.py` recibe `setup`, `start`, `stop` o `status`.
2. `workflow.py` coordina la operación y comprueba la configuración y la sesión.
3. `adapters/audio_capture.py` obtiene el monitor de salida predeterminado y captura con FFmpeg; no captura el micrófono.
4. Al detener, el audio se divide en bloques de 30 segundos. `adapters/voxtype.py` invoca Voxtype con Whisper local para cada bloque, extrae la línea con el texto reconocido y descarta logs de diagnóstico y códigos de color.
5. El progreso y los segmentos quedan en el estado local mientras se procesa. `markdown.py` crea una nota con frontmatter y marcas temporales.
6. `adapters/obsidian.py` guarda la nota en la carpeta de transcripciones de la bóveda. Tras guardarla, el flujo elimina los archivos temporales y limpia la sesión.

Si el procesamiento se interrumpe, `status` muestra el progreso y una nueva ejecución de `stop` continúa desde los segmentos completados, siempre que el audio temporal siga disponible.

## Flujo de guía

1. `workflow.py` selecciona una transcripción, por defecto la más reciente.
2. `adapters/obsidian.py` lee el cuerpo de la nota y excluye el frontmatter. `workflow.py` vuelve a limpiar logs de Voxtype, incluso en notas creadas antes de este filtro.
3. `application/vault_index.py` construye un índice local de la bóveda y rankea hasta 12 notas candidatas con BM25, excluyendo la transcripción fuente.
4. `prompts.py` carga el prompt de sistema predeterminado o la personalización del usuario desde `~/.config/voxstudy/guide_prompt.md`. `adapters/deepseek.py` envía la transcripción limpia y metadatos limitados de las candidatas a la API oficial de DeepSeek (`https://api.deepseek.com/chat/completions`) con `DEEPSEEK_API_KEY`, usando el modelo `deepseek-flash` y solicitando JSON con estructura para guía, mapa conceptual y relaciones con la bóveda.
5. `markdown.py` renderiza resumen por niveles, preguntas guía, desarrollo, términos, mapa conceptual Mermaid, relaciones wikilink validadas, autoevaluación plegable y tarjetas. La guía no incluye marcas de tiempo.
6. `adapters/obsidian.py` guarda la guía en su propia carpeta dentro de la bóveda.

La transcripción se mantiene local durante la captura. La generación de guía es una acción separada y comparte el texto con DeepSeek; no envía el audio.

## Operaciones desde la TUI

Las operaciones síncronas de captura, transcripción y generación de guías se ejecutan en workers de hilo de Textual para que la interfaz permanezca receptiva. Los callbacks de `workflow.py` publican mensajes de progreso; los widgets se actualizan en el hilo principal. Al terminar, la pantalla muestra el resultado o el error y actualiza su estado.

`ui/widgets/navbar.py` proporciona la barra de marca y navegación compartida por el panel, la biblioteca y las vistas de nota. `ui/app.py` coordina el cambio de pantallas y la acción de actualizar la vista actual. `ui/screens/vault_picker.py` permite elegir la carpeta de bóveda con el árbol de directorios de Textual o introducir una ruta directamente. El selector se mantiene registrado para conservar el árbol y su posición entre aperturas; recupera el foco del árbol al mostrarse. El cambio se guarda en la configuración del usuario y conserva las carpetas de transcripciones y guías. Las pantallas consumen las consultas de `application/` y no acceden directamente a la bóveda.

## Módulos

| Módulo | Responsabilidad |
| --- | --- |
| `cli.py` | Argumentos y salida para el usuario. |
| `ui/app.py` | Aplicación Textual, tema predeterminado y navegación de pantallas. |
| `ui/theme.py` | Paleta Aether basada en los colores locales de Omarchy. |
| `ui/widgets/navbar.py` | Barra de marca y navegación compartida entre pantallas. |
| `ui/screens/dashboard.py` | Estado de la bóveda y captura, más notas recientes. |
| `ui/screens/library.py` | Búsqueda de transcripciones y guías, con selección por teclado. |
| `ui/screens/transcript.py` y `ui/screens/study_guide.py` | Vista de nota y acción para abrirla en Obsidian. |
| `ui/screens/vault_picker.py` | Navegación y selección de la carpeta de bóveda. |
| `ui/screens/prompt_settings.py` | Edición, guardado y restauración del prompt de sistema de las guías. |
| `ui/messages.py` | Mensajes de progreso y fin de operación enviados desde workers. |
| `application/dashboard.py` | Consulta que reúne datos para el panel sin depender de Textual. |
| `application/library.py` | Búsqueda, lectura y apertura de notas seleccionadas. |
| `application/vault_index.py` | Índice de solo lectura con metadatos y encabezados de las notas Markdown de la bóveda. |
| `config.py` | Rutas de configuración, bóveda, sesión y estado local. |
| `models.py` | Modelos de configuración, captura y segmentos. |
| `prompts.py` | Prompt predeterminado y persistencia del prompt personalizado por usuario. |
| `workflow.py` | Coordinación de casos de uso. |
| `adapters/audio_capture.py` | Monitor de audio, FFmpeg y división en bloques. |
| `adapters/voxtype.py` | Comprobación e invocación de Voxtype local. |
| `adapters/deepseek.py` | Petición compatible con OpenAI a DeepSeek y validación básica de la respuesta estructurada. |
| `adapters/obsidian.py` | Lectura y escritura de notas en la bóveda. |
| `markdown.py` | Renderizado Markdown de transcripciones y guías. |

El índice de la bóveda es una consulta local de solo lectura. Recorre archivos Markdown, excluye `.obsidian`, `.trash` y `.git`, y conserva rutas relativas junto con título, aliases, etiquetas, resumen y encabezados. También guarda frecuencias de términos del cuerpo para la búsqueda local. `rank_related_notes` usa BM25 ponderado por campo para ordenar posibles notas relacionadas con una transcripción; títulos y aliases tienen más peso que las coincidencias del cuerpo. Solo se envía a DeepSeek metadatos acotados de hasta 12 candidatas, no sus cuerpos completos. Este paso no modifica archivos.

## Decisiones actuales

- La captura selecciona el monitor predeterminado de PipeWire/PulseAudio.
- Voxtype y Whisper se ejecutan localmente para transcribir.
- Los bloques de transcripción duran 30 segundos y se conservan como referencias temporales.
- Las guías son optativas y se generan bajo demanda.
- Las notas de transcripción y las guías son archivos independientes para preservar la fuente original.
- La clave de DeepSeek se lee desde `.env` o una variable de entorno; no forma parte de la configuración ni debe incluirse en el repositorio.
- La interfaz consume consultas de `application/`; las pantallas no inspeccionan directamente la bóveda.
