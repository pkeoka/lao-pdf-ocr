# Lao PDF OCR

Extract text from scanned (image-only) PDFs written in Lao script — as a
double-click Windows app, or as a Python command-line tool. No cloud
services, no API keys: everything runs locally using
[Tesseract OCR](https://github.com/tesseract-ocr/tesseract) with a Lao
language model, plus a Lao-specific text cleanup pass that fixes known
Unicode issues generic OCR tools get wrong.

## Why this exists

Off-the-shelf OCR tools generally don't ship a Lao model, and even when
Tesseract's Lao model is available, its raw output carries a few
well-known Unicode artifacts (decomposed vowel marks, missing ligatures,
stray spaces around combining characters) that make the text look subtly
wrong even when the character recognition itself is correct. This project
bundles the Lao model, applies orthography-standard cleanup automatically,
and packages the whole thing so it's usable without installing anything.

## Two ways to use it

### 1. Windows app (no install required)

Download the latest `LaoPdfOcr.exe` from
[Releases](../../releases) (or build it yourself — see
[BUILD.md](BUILD.md)). Double-click it, choose a PDF, click **Extract
Text**. Output is saved as a `.txt` file next to the PDF you selected.

Optional: check "Also create a searchable PDF" to additionally produce a
copy of the PDF with an invisible, selectable/searchable Lao text layer
laid over the original scan.

### 2. Python script (any OS)

```bash
pip install pytesseract pdf2image pypdf pillow
python lao_pdf_ocr.py scanned_document.pdf
```

This requires Tesseract OCR and Poppler installed separately (see
[TECHNICAL.md](TECHNICAL.md#running-the-python-script-directly) for
platform-specific install commands) — the Windows `.exe` bundles both so
end users don't need this step, but running the raw script gives you
CLI flags and is easier to script into a larger pipeline.

```
usage: lao_pdf_ocr.py [-h] [-o OUTPUT] [--dpi DPI] [--lang LANG]
                       [--searchable-pdf SEARCHABLE_PDF] [--no-normalize]
                       input_pdf

positional arguments:
  input_pdf             Path to the scanned PDF

options:
  -o, --output          Output .txt path (default: <input>.txt)
  --dpi DPI              Rasterization DPI (default 300)
  --lang LANG            Tesseract language code(s), e.g. 'lao' or
                         'lao+eng' for mixed documents (default: lao)
  --searchable-pdf PATH  Also write a searchable PDF
  --no-normalize         Skip Lao orthography cleanup, keep raw OCR output
```

## What you get

- **Plain text extraction**, page by page, with Lao-specific Unicode
  cleanup applied by default (see [TECHNICAL.md](TECHNICAL.md) for exactly
  what this fixes and why it's necessary).
- **Optional searchable PDF** output — the original scan with an
  invisible, copy/searchable text layer.
- **Bilingual documents**: `--lang lao+eng` runs both models together for
  documents mixing Lao and English (e.g. bilingual contracts).

## Accuracy expectations

OCR accuracy depends heavily on scan quality — clean 300dpi+ scans with
good contrast and minimal skew perform best. This uses Tesseract's
`tessdata_best` Lao model (higher accuracy, slower than the default/fast
models), suited to archival and document-quality OCR rather than
real-time use. Handwriting, stamps, and seals overlapping printed text
remain hard for any OCR engine, including this one — always spot-check
output against the source for anything going into a formal or legal
document.

## Contributing

This is a small, single-purpose tool and contributions are welcome —
bug reports, accuracy improvements, support for other Lao-script-adjacent
languages, or platform support (macOS/Linux app builds) are all fair game.
Please open an issue before a large PR so the direction can be agreed on
first. See [TECHNICAL.md](TECHNICAL.md) for how the pieces fit together
before diving in.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including
commercially, with attribution. See the LICENSE file for the exact terms.

## Credits

Built on [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) and
its [`tessdata_best`](https://github.com/tesseract-ocr/tessdata_best) Lao
model, [pdf2image](https://github.com/Belval/pdf2image),
[PyPDF](https://github.com/py-pdf/pypdf), and a Windows build of
[Poppler](https://github.com/oschwartz10612/poppler-windows).
