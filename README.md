# Art Publisher Agent+

A desktop publishing assistant for artists. AI assistance is completely optional.

## Core features — no AI required

The application works normally without Ollama or any AI model:

- manually write and edit captions;
- manually add tags;
- create and reuse tag templates;
- browse artwork in `READY` and `POSTED`;
- publish artwork to supported platforms;
- keep publication history with captions, tags and links.

## Optional AI Assistance

AI is **disabled by default**. If enabled, a local Ollama vision model can optionally:

- suggest a caption;
- suggest tags.

AI does **not** generate artwork. The artwork is supplied by the artist.

To enable it in the GUI, open **Settings → AI Assistance** and check:

```text
Enable AI assistance for captions and tags
```

### Run without AI

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

Or run:

```text
run_app.bat
```

### Run with optional Ollama AI support

Install the additional dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ai.txt
ollama pull qwen3-vl:4b
```

Then start the application and enable AI Assistance in Settings.

You can also use:

```text
run_app_with_ai.bat
```

## EXE builds

Two build scripts are provided:

```text
build_exe.bat
```

Builds the normal application **without the Ollama Python dependency**.

```text
build_exe_with_ai.bat
```

Builds a version that contains the optional Ollama Python client. The Ollama application/server and model are still installed separately by the user.

## Tag templates

Templates are stored in:

```text
tag_templates.json
```

Example:

```text
Ulyana basic → female, anthro, furry, ulyana
```

You can replace the current tags with a template, append a template to current tags, save a new template, or delete one.

## READY / POSTED

The **Files READY/POSTED** tab shows both directories as lists.

- Double-click an image in `READY` to load it into the publication editor.
- Double-click an image in `POSTED` to open the file.

## Publication history

New publications are saved in:

```text
publication_history.json
```

The History tab displays the image, platform, date, caption, tags and publication URL when available.

## Platform status

Currently implemented publishing code:

- Telegram
- X
- VK

Configuration placeholders currently exist for:

- e621
- DeviantArt

Their publishing implementations still need to be completed.


## Window resizing fix
- the application no longer forces a 1380x900 startup size
- startup size adapts to the available desktop area
- the main window can be resized both horizontally and vertically
- the Settings tab uses scrollbars on smaller displays instead of forcing the window height
- preview/history widgets now have smaller minimum sizes so other tabs do not block window resizing


## v5 — responsive publication tab
- The Publication tab now uses a scrollable right-hand panel.
- On short windows, controls keep usable sizes instead of overlapping.
- Caption, tags, tag templates, platform selectors and publish buttons are reached with vertical scrolling.
- The preview panel on the left remains visible and resizable.
