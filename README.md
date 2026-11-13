# DocToPng

Simple Python web UI that converts **DOCX** (Microsoft Word) and **ODT** (OpenDocument / LibreOffice / OpenOffice) documents into one PNG image **per page**.

Two conversion paths are provided so you can compare which works better for your documents:

| Method | Formats | Layout quality | Dependencies |
|--------|---------|----------------|--------------|
| **LibreOffice** (default) | DOCX + ODT | High – real layout engine | LibreOffice must be installed |
| **python-docx** (experimental) | DOCX only | Low – approximate text rendering | Pure Python (python-docx + Pillow) |

## Features

- Upload a `.docx` or `.odt` file
- Choose conversion method in the UI
- Renders every page as a separate PNG
- Download individual pages or a ZIP of all pages
- Clean Gradio interface
- Fully local processing

## Requirements

### System (for the LibreOffice path)

- **LibreOffice** (or OpenOffice) available on `PATH` as `soffice` / `libreoffice`.
  - Ubuntu/Debian: `sudo apt install libreoffice`
  - macOS: `brew install --cask libreoffice`
  - Windows: install from [libreoffice.org](https://www.libreoffice.org/) and ensure `soffice.exe` is on PATH

The **python-docx** path does **not** need LibreOffice.

### Python

```bash
pip install -r requirements.txt
```

## Quick start

```bash
python app.py
```

Open the local URL shown in the terminal (usually http://127.0.0.1:7860).

## How the paths work

### 1. LibreOffice (recommended)

1. Document is converted to PDF with LibreOffice headless:
   ```bash
   soffice --headless --convert-to pdf --outdir <tmp> <input>
   ```
2. Each PDF page is rendered to PNG with **PyMuPDF** at the chosen DPI.

This produces the most faithful visual results for both DOCX and ODT.

### 2. python-docx (experimental)

1. The DOCX is parsed with **python-docx**.
2. Text is extracted; explicit page breaks are detected when present.
3. Content is rendered to PNG pages with **Pillow** using a simple fixed-width text layout.

**Important limitations of the python-docx path:**

- No real layout engine — fonts, spacing, columns, floating objects, etc. are only roughly approximated.
- Images, complex tables, headers, footers and most formatting are ignored or heavily simplified.
- Page breaks are only respected when they appear as hard breaks in the XML.
- Useful for quick text-only previews or environments where LibreOffice cannot be installed.

## Project structure

```
DocToPng/
├── app.py              # Gradio UI (method selector + gallery + ZIP)
├── converter.py        # Both conversion backends
├── requirements.txt
├── README.md
└── .gitignore
```

## License

MIT
