"""
DocToPng – simple Gradio UI.

Upload a DOCX or PDF; each page is turned into a PNG image.

- PDF  → high-quality rendering via PyMuPDF
- DOCX → approximate text rendering via python-docx + Pillow
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import gradio as gr

from converter import convert_document


def process(
    file_obj,
    dpi: int = 200,
) -> Tuple[List[str], Optional[str], str]:
    if file_obj is None:
        return [], None, "Please upload a .docx or .pdf file."

    if isinstance(file_obj, str):
        src = Path(file_obj)
    else:
        src = Path(file_obj.name)

    suffix = src.suffix.lower()
    if suffix not in {".docx", ".doc", ".pdf"}:
        return [], None, f"Unsupported file type: {suffix}. Use .docx or .pdf."

    try:
        work_dir = Path(tempfile.mkdtemp(prefix="doctopng_ui_"))
        png_paths, zip_path = convert_document(src, dpi=dpi, work_dir=work_dir)

        gallery = [str(p) for p in png_paths]
        kind = "PDF (high quality)" if suffix == ".pdf" else "DOCX (approximate)"
        status = (
            f"✅ Converted **{len(png_paths)}** page(s) at {dpi} DPI "
            f"from **{kind}**.\n"
            f"ZIP archive ready for download."
        )
        return gallery, str(zip_path), status

    except Exception as exc:
        return [], None, f"❌ Error: {exc}"


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="DocToPng", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # DocToPng
            Upload a **PDF** or **DOCX** file. Each page is rendered as a separate PNG image.

            | Input | Quality | How it works |
            |-------|---------|--------------|
            | **PDF** | High (lossless PNG) | PyMuPDF, RGB, annotations, chosen DPI |
            | **DOCX** | Approximate | python-docx text + Pillow layout |
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="Upload document",
                    file_types=[".pdf", ".docx", ".doc"],
                    type="filepath",
                )
                dpi_slider = gr.Slider(
                    minimum=72,
                    maximum=400,
                    value=200,
                    step=1,
                    label="DPI (resolution)",
                    info="200 = sharp screen / light print · 300 = print quality · 400 = max detail",
                )
                convert_btn = gr.Button("Convert to PNGs", variant="primary")

            with gr.Column(scale=2):
                status_box = gr.Markdown("")
                gallery = gr.Gallery(
                    label="Page previews",
                    columns=2,
                    height="auto",
                    object_fit="contain",
                )
                zip_output = gr.File(label="Download all pages (ZIP)")

        convert_btn.click(
            fn=process,
            inputs=[file_input, dpi_slider],
            outputs=[gallery, zip_output, status_box],
        )

        gr.Markdown(
            """
            ---
            **PDF quality tips**
            - Default **200 DPI** is a good balance of sharpness and file size.
            - Use **300 DPI** for print or archival screenshots.
            - PNG is lossless; raising DPI is the main way to get more detail.
            - Annotations and form fields are included in the render.

            **DOCX note**
            - DOCX rendering is text-only and approximate. For faithful visuals,
              export the Word file to PDF first, then upload the PDF.
            """
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
