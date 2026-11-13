"""
DocToPng – simple Gradio UI for converting DOCX / ODT documents to per-page PNGs.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import gradio as gr

from converter import convert_document, find_soffice


def check_libreoffice() -> str:
    path = find_soffice()
    if path:
        return f"✅ LibreOffice found: `{path}`"
    return (
        "❌ LibreOffice / OpenOffice **not found**. "
        "Install it and make sure `soffice` or `libreoffice` is on your PATH."
    )


def process(
    file_obj,
    dpi: int = 150,
) -> Tuple[List[str], Optional[str], str]:
    """
    Gradio handler.

    Returns
    -------
    gallery_images : list of file paths for the Gallery
    zip_file       : path to the ZIP (or None)
    status         : human-readable status message
    """
    if file_obj is None:
        return [], None, "Please upload a .docx or .odt file."

    # Gradio may give a path string or a file-like object depending on version
    if isinstance(file_obj, str):
        src = Path(file_obj)
    else:
        src = Path(file_obj.name)

    if src.suffix.lower() not in {".docx", ".odt", ".doc"}:
        return [], None, f"Unsupported file type: {src.suffix}. Use .docx or .odt."

    try:
        work_dir = Path(tempfile.mkdtemp(prefix="doctopng_ui_"))
        png_paths, zip_path = convert_document(src, dpi=dpi, work_dir=work_dir)

        gallery = [str(p) for p in png_paths]
        status = (
            f"✅ Converted **{len(png_paths)}** page(s) at {dpi} DPI.\n"
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
            Upload a **DOCX** (Word) or **ODT** (OpenDocument / LibreOffice) file.  
            Each page will be rendered as a separate PNG image.

            Conversion uses LibreOffice (headless) → PDF → PyMuPDF.
            """
        )

        with gr.Row():
            status_lo = gr.Markdown(check_libreoffice())

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="Upload document",
                    file_types=[".docx", ".odt", ".doc"],
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
            **Tips**
            - Higher DPI = sharper images but larger files and slower conversion.
            - Both DOCX and ODT go through the same LibreOffice path, so you can
              easily compare which source format gives better visual fidelity for your documents.
            - Make sure LibreOffice is installed before converting.
            """
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
