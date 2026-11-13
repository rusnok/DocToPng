"""
Core conversion logic: DOCX / ODT → PDF (via LibreOffice) → per-page PNG (via PyMuPDF).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

import fitz  # PyMuPDF


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
    """
    Convert DOCX or ODT to PDF using LibreOffice headless mode.
    Returns the path to the generated PDF.
    """
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
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    # LibreOffice names the PDF after the input stem
    pdf_path = out_dir / f"{input_path.stem}.pdf"
    if not pdf_path.exists():
        # Sometimes the name is slightly different; pick the newest PDF
        pdfs = list(out_dir.glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError("LibreOffice did not produce a PDF file.")
        pdf_path = max(pdfs, key=lambda p: p.stat().st_mtime)
    return pdf_path


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
    Full pipeline: document → PDF → list of PNG paths + ZIP path.

    Returns
    -------
    png_paths : list of Path
    zip_path  : Path to a ZIP containing all PNGs
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    suffix = input_path.suffix.lower()
    if suffix not in {".docx", ".odt", ".doc"}:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Only .docx, .odt and .doc are supported."
        )

    soffice = find_soffice()
    if soffice is None:
        raise RuntimeError(
            "LibreOffice / OpenOffice not found. "
            "Please install it and ensure 'soffice' or 'libreoffice' is on your PATH."
        )

    cleanup = False
    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="doctopng_"))
        cleanup = False  # caller may want to keep files; Gradio will clean later

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    # Copy input into work dir so LibreOffice has a clean name
    local_input = work_dir / input_path.name
    if local_input.resolve() != input_path.resolve():
        shutil.copy2(input_path, local_input)

    pdf_path = convert_to_pdf(local_input, work_dir, soffice)
    png_paths = pdf_to_pngs(pdf_path, work_dir, dpi=dpi)

    zip_path = work_dir / f"{input_path.stem}_pages.zip"
    create_zip(png_paths, zip_path)

    return png_paths, zip_path
