# DocToPng

Simple Python web UI that converts **DOCX** (Microsoft Word) and **ODT** (OpenDocument / LibreOffice / OpenOffice) documents into one PNG image **per page**.

Two conversion paths are supported so you can compare quality and reliability:

1. **LibreOffice headless** → PDF → **PyMuPDF** (recommended, works for both DOCX and ODT)
2. Pure fallback notes / alternative approaches documented below

## Features

- Upload a `.docx` or `.odt` file
- Renders every page as a separate high-quality PNG
- Download individual pages or a ZIP of all pages
- Clean Gradio interface
- Fully local processing (no cloud services)

## Requirements

### System

- **LibreOffice** (or OpenOffice) must be installed and available on `PATH` as `soffice` / `libreoffice`.
  - Ubuntu/Debian: `sudo apt install libreoffice`
  - macOS: `brew install --cask libreoffice`
  - Windows: install from [libreoffice.org](https://www.libreoffice.org/) and ensure `soffice.exe` is on PATH

### Python

```bash
pip install -r requirements.txt
```

## Quick start

```bash
python app.py
```

Then open the local URL shown in the terminal (usually http://127.0.0.1:7860).

## How it works

1. The uploaded document is saved to a temporary directory.
2. LibreOffice is invoked in headless mode to convert the document to PDF:
   ```bash
   soffice --headless --convert-to pdf --outdir <tmp> <input>
   ```
3. Each page of the resulting PDF is rendered to PNG with **PyMuPDF** (fitz) at 150 DPI (configurable).
4. PNGs are returned to the Gradio UI for preview and download. A ZIP archive of all pages is also provided.

This path works well for both DOCX and ODT and usually produces the most faithful visual results.

## Alternative / experimental paths

You can experiment with other approaches and compare quality:

| Method | DOCX | ODT | Notes |
|--------|------|-----|-------|
| LibreOffice + PyMuPDF (default) | ✅ | ✅ | Best overall fidelity |
| Spire.Doc / Aspose.Words | ✅ | limited | Commercial, good DOCX quality, free tier watermark |
| python-docx + custom rendering | partial | ❌ | Only extracts content, not true page layout |
| GroupDocs / other SDKs | ✅ | ✅ | Commercial |

The default path is intentionally free and open-source.

## Project structure

```
DocToPng/
├── app.py              # Gradio UI
├── converter.py        # Core conversion logic
├── requirements.txt
├── README.md
└── .gitignore
```

## License

MIT
