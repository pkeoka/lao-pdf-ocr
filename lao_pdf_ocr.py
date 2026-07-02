#!/usr/bin/env python3
"""
lao_pdf_ocr.py — Extract text from a scanned (image-based) PDF containing Lao script.

Usage:
    python3 lao_pdf_ocr.py INPUT.pdf [-o OUTPUT.txt] [--dpi 300] [--lang lao] [--searchable-pdf OUT.pdf]

Requirements (already installed in this environment):
    - tesseract-ocr (binary) + a Lao traineddata file on TESSDATA_PREFIX
    - poppler-utils (for pdf2image)
    - Python packages: pytesseract, pdf2image, pypdf

To run this on your own machine instead:
    1. Install Tesseract OCR (https://github.com/tesseract-ocr/tesseract)
    2. Download lao.traineddata from
       https://github.com/tesseract-ocr/tessdata_best/blob/main/lao.traineddata
       and place it in your tessdata folder (e.g. /usr/share/tesseract-ocr/5/tessdata/)
    3. Install poppler (poppler-utils on Linux, `brew install poppler` on macOS,
       or the poppler binaries on Windows)
    4. pip install pytesseract pdf2image pypdf
"""

import argparse
import os
import re
import sys
import unicodedata
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader

# --- Lao orthography normalization -----------------------------------------
# Fixes for known, well-defined OCR/legacy-text artifacts in Lao Unicode,
# per the official Lao MoES 2024 orthography standard (combining-mark
# precomposition and stray-space rules). These are narrow, unambiguous
# corrections — not a general spell-checker — so they're safe to apply by
# default to every extraction.
#
# NOTE: standard Unicode NFC normalization does NOT perform these fixes on
# its own (verified: Lao vowel/tone marks carry combining class 0, and the
# Lao "HO NO"/"HO MO" ligatures are compatibility, not canonical, mappings),
# so they have to be applied explicitly.

# NIGGAHITA + AA -> precomposed AM. A stray space sometimes appears between
# the two marks in extracted/legacy text (per the orthography standard), so
# it's tolerated and dropped here too.
_AM_DECOMPOSED_RE = re.compile("\u0ecd[ \t]*\u0eb2")
_HO_NO_RE = re.compile("\u0eab\u0e99")  # HO SUNG + NO  ->  precomposed HO NO (ໜ)
_HO_MO_RE = re.compile("\u0eab\u0ea1")  # HO SUNG + MO  ->  precomposed HO MO (ໝ)

# Any Lao combining mark (vowel sign / tone mark) that attaches to the
# preceding base consonant. A space can never legitimately sit between a
# base and its combining mark, so a space immediately before one of these
# is always an OCR/copy artifact, never an intentional word break.
_LAO_COMBINING_MARKS = "".join(
    chr(cp) for cp in range(0x0E80, 0x0EFF) if unicodedata.category(chr(cp)) == "Mn"
)
_SPACE_BEFORE_MARK_RE = re.compile(rf"[ \t]+(?=[{re.escape(_LAO_COMBINING_MARKS)}])")


def normalize_lao_text(text: str) -> str:
    """Apply the official Lao orthography normalization rules to OCR output:
    Unicode NFC, precomposed AM (ຳ) and HO NO / HO MO (ໜ / ໝ) ligatures, and
    removal of stray spaces before combining marks."""
    text = unicodedata.normalize("NFC", text)
    text = _AM_DECOMPOSED_RE.sub("\u0eb3", text)
    text = _HO_NO_RE.sub("\u0edc", text)
    text = _HO_MO_RE.sub("\u0edd", text)
    text = _SPACE_BEFORE_MARK_RE.sub("", text)
    return text


def find_tessdata_dir() -> str | None:
    """Locate a directory containing lao.traineddata, checking common locations
    plus a local ./tessdata folder shipped alongside this script."""
    candidates = [
        os.environ.get("TESSDATA_PREFIX"),
        str(Path(__file__).resolve().parent / "tessdata"),
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tessdata",
    ]
    for c in candidates:
        if c and Path(c, "lao.traineddata").is_file():
            return c
    return None


def extract_text(
    pdf_path: str,
    lang: str = "lao",
    dpi: int = 300,
    normalize: bool = True,
    poppler_path: str | None = None,
) -> list[str]:
    """OCR every page of a scanned PDF and return a list of per-page text.

    By default, output is passed through normalize_lao_text() to fix known
    Lao Unicode artifacts (see above). Pass normalize=False to get Tesseract's
    raw output untouched, e.g. for debugging OCR quality itself.

    Pages are rasterized and OCR'd one at a time (rather than converting the
    whole PDF to images up front) to keep memory use flat regardless of
    document length — converting all pages at once can exhaust memory on
    large (50+ page) PDFs at 300+ DPI.

    poppler_path: folder containing pdftoppm(.exe) etc., for environments
    (e.g. a bundled Windows .exe) where poppler isn't on PATH.
    """
    tessdata_dir = find_tessdata_dir()
    if tessdata_dir is None:
        sys.exit(
            "Could not find lao.traineddata. Download it from "
            "https://github.com/tesseract-ocr/tessdata_best/blob/main/lao.traineddata "
            "and place it in a 'tessdata' folder next to this script, or set "
            "TESSDATA_PREFIX to a directory that contains it."
        )

    config = f'--tessdata-dir "{tessdata_dir}"'

    reader = PdfReader(pdf_path)
    n_pages = len(reader.pages)

    pages_text = []
    for i in range(1, n_pages + 1):
        print(f"OCR page {i}/{n_pages}...", file=sys.stderr)
        page_images = convert_from_path(
            pdf_path, dpi=dpi, first_page=i, last_page=i, poppler_path=poppler_path
        )
        image = page_images[0]
        text = pytesseract.image_to_string(image, lang=lang, config=config).strip()
        if normalize and ("lao" in lang):
            text = normalize_lao_text(text)
        pages_text.append(text)
        del page_images, image
    return pages_text


def make_searchable_pdf(
    pdf_path: str,
    out_path: str,
    lang: str = "lao",
    dpi: int = 300,
    poppler_path: str | None = None,
) -> None:
    """Create a searchable PDF: original page images with an invisible Lao text
    layer on top, so the file can be opened and text-searched/copy-pasted.

    Note: the embedded text layer is Tesseract's raw output — normalize_lao_text()
    is not applied here, since that would require rebuilding the PDF's internal
    text-positioning data rather than just post-processing a string. Use the
    plain-text (.txt) output if you need the normalized version."""
    tessdata_dir = find_tessdata_dir()
    if tessdata_dir is None:
        sys.exit("Could not find lao.traineddata (see extract_text error above).")

    config = f'--tessdata-dir "{tessdata_dir}"'
    images = convert_from_path(pdf_path, dpi=dpi, poppler_path=poppler_path)

    from pypdf import PdfWriter

    writer = PdfWriter()
    for i, image in enumerate(images, start=1):
        print(f"Building searchable page {i}/{len(images)}...", file=sys.stderr)
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(
            image, lang=lang, config=config, extension="pdf"
        )
        tmp_path = f"/tmp/_page_{i}.pdf"
        with open(tmp_path, "wb") as f:
            f.write(pdf_bytes)
        from pypdf import PdfReader

        writer.add_page(PdfReader(tmp_path).pages[0])
        os.remove(tmp_path)

    with open(out_path, "wb") as f:
        writer.write(f)


def main():
    parser = argparse.ArgumentParser(description="Extract Lao text from a scanned PDF.")
    parser.add_argument("input_pdf", help="Path to the scanned PDF")
    parser.add_argument("-o", "--output", help="Output .txt path (default: <input>.txt)")
    parser.add_argument("--dpi", type=int, default=300, help="Rasterization DPI (default 300)")
    parser.add_argument(
        "--lang",
        default="lao",
        help="Tesseract language code(s), e.g. 'lao' or 'lao+eng' for mixed documents (default: lao)",
    )
    parser.add_argument(
        "--searchable-pdf",
        help="Optional: also write a searchable PDF (image + invisible text layer) to this path",
    )
    parser.add_argument(
        "--no-normalize",
        action="store_true",
        help=(
            "Skip Lao orthography normalization and keep Tesseract's raw output "
            "(useful for debugging OCR quality itself)"
        ),
    )
    args = parser.parse_args()

    input_path = Path(args.input_pdf)
    if not input_path.is_file():
        sys.exit(f"File not found: {input_path}")

    output_path = Path(args.output) if args.output else input_path.with_suffix(".txt")

    pages_text = extract_text(
        str(input_path), lang=args.lang, dpi=args.dpi, normalize=not args.no_normalize
    )

    with open(output_path, "w", encoding="utf-8") as f:
        for i, text in enumerate(pages_text, start=1):
            f.write(f"--- Page {i} ---\n{text}\n\n")

    print(f"\nExtracted text written to: {output_path}")

    if args.searchable_pdf:
        make_searchable_pdf(str(input_path), args.searchable_pdf, lang=args.lang, dpi=args.dpi)
        print(f"Searchable PDF written to: {args.searchable_pdf}")


if __name__ == "__main__":
    main()
