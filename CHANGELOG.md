# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/), and this project
uses [Semantic Versioning](https://semver.org/) once tagged releases begin
(see "Versioning" in the README/BUILD docs).

## [Unreleased]

Nothing yet.

## [1.0.0] — 2026-07-03

Initial public release.

### Added
- Core OCR pipeline (`lao_pdf_ocr.py`): scanned PDF → per-page rasterization
  → Tesseract OCR (Lao model) → Lao orthography normalization → plain text
  and/or searchable PDF output.
- Lao-specific Unicode normalization (`normalize_lao_text()`): fixes
  decomposed AM vowel, decomposed ໜ/ໝ ligatures, and stray spaces before
  combining marks — issues confirmed not already handled by standard
  Unicode NFC normalization.
- Desktop GUI (`lao_pdf_ocr_gui.py`): file picker, normalize/searchable-PDF
  checkboxes, progress bar, no command line required.
- Windows `.exe` build pipeline (`.github/workflows/build-windows-exe.yml`):
  bundles Tesseract, Poppler, and the Lao model into a single
  double-click executable, with an automated OCR sanity check against
  `test_lao_scanned.pdf` gating every build.
- Bundled `tessdata_best`-quality Lao model plus the support files needed
  for searchable-PDF output (`configs/`, `tessconfigs/`, `pdf.ttf`).
- CLI flags: `--dpi`, `--lang` (for mixed-language documents, e.g.
  `lao+eng`), `--searchable-pdf`, `--no-normalize`.

### Fixed (during Windows build bring-up)
- `find_tessdata_dir()` could return a relative path, which worked by
  accident on Linux but broke when handed to the Tesseract subprocess on
  Windows. Now always resolves to an absolute path.
- Tesseract's `--tessdata-dir` CLI flag, when quoted, arrived at
  `tesseract.exe` on Windows with the literal quote characters still
  embedded in the path (a `pytesseract`/`shlex` Windows-quoting
  difference), corrupting the path. Replaced with setting `TESSDATA_PREFIX`
  as an environment variable instead, which isn't subject to that parsing.
  See `TECHNICAL.md` for the full root-cause writeup.
- CI's PATH didn't pick up Chocolatey-installed Tesseract in the very next
  build step (each CI step is a fresh process). Fixed by explicitly
  refreshing the environment via Chocolatey's PowerShell profile, with a
  hardcoded-default-path fallback.
- Replaced a fragile dependency on Chocolatey's internal `poppler` package
  layout with a direct, pinned download of a known-good Poppler-for-Windows
  release.
- Windows console encoding (`cp1252`) couldn't print Lao characters during
  CI's sanity check — fixed by forcing UTF-8 mode for that step. (Did not
  affect the shipped app itself, which never prints Lao text to a console.)
