"""
DocToPng – simple Gradio UI for converting DOCX / ODT documents to per-page PNGs.

Supports two conversion methods for DOCX so you can compare results:
  - LibreOffice (recommended, faithful layout)
  - python-docx (pure Python, approximate text-only rendering)
"""

from __future__ import annotations

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
        "⚠️ LibreOffice / OpenOffice **not found**. "
        "The 'LibreOffice' method will fail. You can still use the "
        "**python-docx** method for DOCX files (approximate layout)."
    )


def process(
    file_obj,
    method: str,
    dpi: int = 150,
) -> Tuple[List[str], Optional[str], str]:
    if file_obj is None:
        return [], None, "Please upload a .docx or .odt file."

    if isinstance(file_obj, str):
        src = Path(file_obj)
    else:
        src = Path(file_obj.name)

    suffix = src.suffix.lower()
    if suffix not in {".docx", ".odt", ".doc"}:
        return [], None, f"Unsupported file type: {suffix}. Use .docx or .odt."

    # Normalize method name
    method_key = "python-docx" if "python-docx" in method.lower() else "libreoffice"

    if method_key == "python-docx" and suffix == ".odt":
        return [], None, "python-docx method only works with DOCX. Use LibreOffice for ODT."

    try:
        work_dir = Path(tempfile.mkdtemp(prefix="doctopng_ui_"))
        png_paths, zip_path = convert_document(
            src, dpi=dpi, work_dir=work_dir, method=method_key
        )

        gallery = [str(p) for p in png_paths]
        status = (
            f"✅ Converted **{len(png_paths)}** page(s) at {dpi} DPI "
            f"using **{method_key}**.\n"
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
            Upload a **DOCX** (Word) or **ODT** (OpenDocument) file.  
            Each page is rendered as a separate PNG image.

            Choose a conversion method to compare quality:
            - **LibreOffice** — faithful visual layout (recommended, works for DOCX + ODT)
            - **python-docx** — pure-Python parsing + simple text rendering (DOCX only, approximate)
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
                method = gr.Radio(
                    choices=[
                        "LibreOffice (faithful layout)",
                        "python-docx (experimental / approximate)",
                    ],
                    value="LibreOffice (faithful layout)",
                    label="Conversion method",
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
            inputs=[file_input, method, dpi_slider],
            outputs=[gallery, zip_output, status_box],
        )

        gr.Markdown(
            """
            ---
            ### Method comparison

            | Aspect              | LibreOffice              | python-docx                          |
            |---------------------|--------------------------|--------------------------------------|
            | Layout fidelity     | High (real engine)       | Low (text + basic wrapping only)     |
            | Images / tables     | Preserved                | Mostly ignored                       |
            | Headers / footers   | Yes                      | No                                   |
            | External dependency | LibreOffice required     | None (pure Python)                   |
            | ODT support         | Yes                      | No                                   |
            | Best for            | Accurate page screenshots| Quick text preview / no LO installed |

            The python-docx path is useful for testing or when you cannot install LibreOffice.
            For production-quality page images, prefer the LibreOffice path.
            """
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
