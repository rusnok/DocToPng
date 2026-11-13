"""
DocToPng – simple Gradio UI.

Upload a DOCX or PDF; each page is turned into a PNG image.

- PDF  → faithful rendering via PyMuPDF
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
    dpi: int = 150,
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
        kind = "PDF (faithful)" if suffix == ".pdf" else "DOCX (approximate)"
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
            | **PDF** | Faithful | PyMuPDF renders each page exactly |
            | **DOCX** | Approximate | python-docx extracts text; Pillow draws simple pages |
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
                    maximum=300,
                    value=150,
                    step=1,
                    label="DPI (resolution)",
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
            **Notes**
            - PDF path produces accurate page images (recommended when possible).
            - DOCX path is text-only and approximate: no real layout, images, or complex tables.
              Prefer converting the Word file to PDF first if you need faithful visuals.
            - Higher DPI = sharper images, larger files, slower conversion.
            """
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
