# DocToPng

Simple Python web UI that turns each page of a **PDF** or **DOCX** into a separate PNG image.

| Input | Rendering quality | Engine |
|-------|-------------------|--------|
| **PDF** | Faithful (exact page look) | PyMuPDF |
| **DOCX** | Approximate (text-only layout) | python-docx + Pillow |

No LibreOffice or other external tools required.

## Features

- Upload a `.pdf` or `.docx` file
- One PNG per page
- Adjustable DPI (72–300)
- Preview gallery + ZIP download of all pages
- Fully local, pure-Python stack

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open the URL shown in the terminal (usually http://127.0.0.1:7860).

## How it works

### PDF

Each page is rendered directly with **PyMuPDF** at the chosen DPI. Layout, fonts, images, and vector graphics are preserved.

### DOCX

1. **python-docx** parses the document and extracts text.
2. Explicit page breaks in the XML are respected when present.
3. **Pillow** draws simple text pages (fixed margins, basic wrapping).

**DOCX limitations:** no real layout engine, images/tables/headers/footers are ignored or heavily simplified. For accurate visuals, convert the Word file to PDF first, then upload the PDF.

## Project structure

```
DocToPng/
├── app.py           # Gradio UI
├── converter.py     # PDF + DOCX backends
├── requirements.txt
├── README.md
└── .gitignore
```

## License

MIT
