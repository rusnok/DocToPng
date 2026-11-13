# DocToPng

Simple Python web UI that turns each page of a **PDF** or **DOCX** into a separate PNG image.

| Input | Rendering quality | Engine |
|-------|-------------------|--------|
| **PDF** | High (lossless PNG, RGB, annotations) | PyMuPDF |
| **DOCX** | Approximate (text-only layout) | python-docx + Pillow |

No LibreOffice or other external tools required.

## Features

- Upload a `.pdf` or `.docx` file
- One PNG per page
- Adjustable DPI (72–400, default **200**)
- Preview gallery + ZIP download of all pages
- Fully local, pure-Python stack

## PDF rendering quality

The PDF path is tuned for sharp output:

- Default **200 DPI** (screen / light print); slider goes to **400**
- Explicit **RGB** colorspace
- **Opaque** render (no alpha soft edges on paper background)
- **Annotations** and form widgets included
- **Lossless PNG** (no JPEG compression artifacts)
- Uses PyMuPDF `dpi=` when available, otherwise an equivalent scale matrix

For print or archival use, set DPI to **300**.

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

Each page is rendered with **PyMuPDF** at the chosen DPI. Layout, fonts, images, vectors, and annotations are preserved.

### DOCX

1. **python-docx** parses the document and extracts text.
2. Explicit page breaks in the XML are respected when present.
3. **Pillow** draws simple text pages (fixed margins, basic wrapping).

**DOCX limitations:** no real layout engine; images/tables/headers/footers are ignored or simplified. For accurate visuals, convert the Word file to PDF first, then upload the PDF.

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
