"""
Core conversion logic.

Supported inputs:
  - PDF  → faithful per-page PNG via PyMuPDF
  - DOCX → approximate per-page PNG via python-docx + Pillow
            (no real layout engine; text-only approximation)
"""

from __future__ import annotations

import os
import shutil
import tempfile
import textwrap
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF
from docx import Document
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# PDF → PNG (faithful)
# ---------------------------------------------------------------------------

def pdf_to_pngs(pdf_path: Path, out_dir: Path, dpi: int = 150) -> List[Path]:
    """Render every page of a PDF to a PNG file. Returns list of PNG paths."""
    doc = fitz.open(pdf_path)
    png_paths: List[Path] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out_file = out_dir / f"page_{page_index + 1:04d}.png"
        pix.save(str(out_file))
        png_paths.append(out_file)

    doc.close()
    return png_paths


# ---------------------------------------------------------------------------
# DOCX → PNG via python-docx (approximate)
# ---------------------------------------------------------------------------

def _get_font(size: int = 14) -> ImageFont.ImageFont:
    """Try to load a reasonable system font; fall back to default."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _extract_pages_from_docx(doc: Document) -> List[str]:
    """
    Split document content into approximate pages.

    Uses explicit page breaks when present; otherwise puts everything on one
    logical page and lets the renderer paginate by height.
    """
    pages: List[List[str]] = [[]]

    for para in doc.paragraphs:
        has_page_break = False
        for run in para.runs:
            for br in run._element.findall(qn("w:br")):
                if br.get(qn("w:type")) == "page":
                    has_page_break = True
                    break
            if has_page_break:
                break

        text = para.text.strip()
        if text:
            pages[-1].append(text)

        if has_page_break:
            pages.append([])

    if pages and not pages[-1]:
        pages.pop()

    if not pages:
        pages = [["(empty document)"]]

    return ["\n\n".join(block) for block in pages]


def _render_text_to_pngs(
    page_texts: List[str],
    out_dir: Path,
    dpi: int = 150,
    page_width_in: float = 8.5,
    page_height_in: float = 11.0,
    margin_in: float = 0.75,
) -> List[Path]:
    """
    Render each text block as one or more PNG pages using a simple fixed layout.
    This is intentionally approximate — it does not reproduce Word's layout engine.
    """
    width_px = int(page_width_in * dpi)
    height_px = int(page_height_in * dpi)
    margin_px = int(margin_in * dpi)
    usable_width = width_px - 2 * margin_px
    usable_height = height_px - 2 * margin_px

    scale = dpi / 72.0
    font_size = max(10, int(11 * scale))
    font = _get_font(font_size)
    line_height = int(font_size * 1.35)

    avg_char_width = font_size * 0.55
    max_chars = max(20, int(usable_width / avg_char_width))

    png_paths: List[Path] = []
    page_counter = 0

    for block in page_texts:
        wrapped_lines: List[str] = []
        for paragraph in block.split("\n"):
            if not paragraph.strip():
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(textwrap.wrap(paragraph, width=max_chars) or [""])

        lines_per_page = max(1, usable_height // line_height)
        for i in range(0, len(wrapped_lines), lines_per_page):
            chunk = wrapped_lines[i : i + lines_per_page]
            page_counter += 1

            img = Image.new("RGB", (width_px, height_px), color="white")
            draw = ImageDraw.Draw(img)

            y = margin_px
            for line in chunk:
                draw.text((margin_px, y), line, fill="black", font=font)
                y += line_height

            footer = f"— page {page_counter} (python-docx approx.) —"
            draw.text(
                (margin_px, height_px - margin_px // 2),
                footer,
                fill="#888888",
                font=_get_font(max(8, font_size // 2)),
            )

            out_file = out_dir / f"page_{page_counter:04d}.png"
            img.save(out_file, "PNG")
            png_paths.append(out_file)

    return png_paths


def convert_docx_python_docx(
    input_path: Path,
    out_dir: Path,
    dpi: int = 150,
) -> List[Path]:
    """
    Parse DOCX with python-docx and render approximate pages.

    Limitations:
    - No real layout engine → line wrapping, fonts, spacing, tables, headers/footers,
      columns, floating images, etc. are only roughly approximated or ignored.
    - Images and complex tables are not rendered.
    - Page breaks are detected only when explicitly present in the XML.
    """
    doc = Document(str(input_path))
    page_texts = _extract_pages_from_docx(doc)
    return _render_text_to_pngs(page_texts, out_dir, dpi=dpi)


# ---------------------------------------------------------------------------
# Shared helpers + main entry point
# ---------------------------------------------------------------------------

def create_zip(png_paths: List[Path], zip_path: Path) -> Path:
    """Pack PNG files into a ZIP archive."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in png_paths:
            zf.write(p, arcname=p.name)
    return zip_path


def convert_document(
    input_file: str | Path,
    dpi: int = 150,
    work_dir: Optional[Path] = None,
) -> Tuple[List[Path], Path]:
    """
    Full pipeline: DOCX or PDF → list of PNG paths + ZIP path.

    - PDF  → PyMuPDF (faithful page rendering)
    - DOCX → python-docx + Pillow (approximate text layout)

    Returns
    -------
    png_paths : list of Path
    zip_path  : Path to a ZIP containing all PNGs
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in {".docx", ".doc", ".pdf"}:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Only .docx, .doc and .pdf are supported."
        )

    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="doctopng_"))
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    local_input = work_dir / input_path.name
    if local_input.resolve() != input_path.resolve():
        shutil.copy2(input_path, local_input)

    if suffix == ".pdf":
        png_paths = pdf_to_pngs(local_input, work_dir, dpi=dpi)
    else:
        png_paths = convert_docx_python_docx(local_input, work_dir, dpi=dpi)

    zip_path = work_dir / f"{input_path.stem}_pages.zip"
    create_zip(png_paths, zip_path)
    return png_paths, zip_path
