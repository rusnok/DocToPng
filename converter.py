"""
Core conversion logic.

Two paths for DOCX:
  1. LibreOffice headless → PDF → PyMuPDF  (faithful layout, also works for ODT)
  2. python-docx direct parsing + Pillow     (no external tools, approximate layout)

ODT always uses the LibreOffice path.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF
from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml.ns import qn
from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# LibreOffice helpers
# ---------------------------------------------------------------------------

def find_soffice() -> Optional[str]:
    """Locate the LibreOffice / OpenOffice executable."""
    candidates = [
        "soffice",
        "libreoffice",
        "soffice.exe",
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice",
        "/usr/bin/libreoffice",
        "/usr/lib/libreoffice/program/soffice",
    ]
    for cmd in candidates:
        path = shutil.which(cmd) if not os.path.isabs(cmd) else (cmd if os.path.isfile(cmd) else None)
        if path:
            return path
    return None


def convert_to_pdf(input_path: Path, out_dir: Path, soffice: str) -> Path:
    """Convert DOCX or ODT to PDF using LibreOffice headless mode."""
    cmd = [
        soffice,
        "--headless",
        "--norestore",
        "--nofirststartwizard",
        "--convert-to",
        "pdf",
        "--outdir",
        str(out_dir),
        str(input_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    pdf_path = out_dir / f"{input_path.stem}.pdf"
    if not pdf_path.exists():
        pdfs = list(out_dir.glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError("LibreOffice did not produce a PDF file.")
        pdf_path = max(pdfs, key=lambda p: p.stat().st_mtime)
    return pdf_path


def pdf_to_pngs(pdf_path: Path, out_dir: Path, dpi: int = 150) -> List[Path]:
    """Render every page of a PDF to a PNG file."""
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
# python-docx direct parsing (experimental / approximate)
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
        # Detect hard page breaks inside runs
        has_page_break = False
        for run in para.runs:
            # python-docx exposes breaks via the underlying XML
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

    # Also check for page-break-before paragraph properties (common style)
    # Already handled roughly by the break detection above.

    # Drop trailing empty page
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
    scale = dpi / 72.0
    width_px = int(page_width_in * dpi)
    height_px = int(page_height_in * dpi)
    margin_px = int(margin_in * dpi)
    usable_width = width_px - 2 * margin_px
    usable_height = height_px - 2 * margin_px

    font_size = max(10, int(11 * scale))
    font = _get_font(font_size)
    line_height = int(font_size * 1.35)

    # Approximate characters per line (monospace-ish estimate)
    avg_char_width = font_size * 0.55
    max_chars = max(20, int(usable_width / avg_char_width))

    png_paths: List[Path] = []
    page_counter = 0

    for block in page_texts:
        # Word-wrap the whole block
        wrapped_lines: List[str] = []
        for paragraph in block.split("\n"):
            if not paragraph.strip():
                wrapped_lines.append("")
                continue
            wrapped_lines.extend(textwrap.wrap(paragraph, width=max_chars) or [""])

        # Paginate by height
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

            # Small footer with page number
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
    Experimental path: parse DOCX with python-docx and render approximate pages.

    Limitations (important):
    - No real layout engine → line wrapping, fonts, spacing, tables, headers/footers,
      columns, floating images, etc. are only roughly approximated or ignored.
    - Images and complex tables are not rendered.
    - Page breaks are detected only when explicitly present in the XML.
    - Useful for quick text-only previews or when LibreOffice is unavailable.
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
    method: str = "libreoffice",
) -> Tuple[List[Path], Path]:
    """
    Full pipeline.

    Parameters
    ----------
    method : "libreoffice" | "python-docx"
        - libreoffice : faithful visual rendering (DOCX + ODT). Requires soffice.
        - python-docx : pure-Python approximate text rendering (DOCX only).

    Returns
    -------
    png_paths, zip_path
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in {".docx", ".odt", ".doc"}:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Only .docx, .odt and .doc are supported."
        )

    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="doctopng_"))
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    local_input = work_dir / input_path.name
    if local_input.resolve() != input_path.resolve():
        shutil.copy2(input_path, local_input)

    method = method.lower().strip()

    if method == "python-docx":
        if suffix not in {".docx", ".doc"}:
            raise ValueError("python-docx method only supports .docx / .doc files.")
        png_paths = convert_docx_python_docx(local_input, work_dir, dpi=dpi)
    else:
        # Default: LibreOffice path
        soffice = find_soffice()
        if soffice is None:
            raise RuntimeError(
                "LibreOffice / OpenOffice not found. "
                "Install it or switch to the 'python-docx' method for DOCX files."
            )
        pdf_path = convert_to_pdf(local_input, work_dir, soffice)
        png_paths = pdf_to_pngs(pdf_path, work_dir, dpi=dpi)

    zip_path = work_dir / f"{input_path.stem}_pages.zip"
    create_zip(png_paths, zip_path)
    return png_paths, zip_path
