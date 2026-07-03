# Technical specification

## Architecture overview

```
lao_pdf_ocr.py       Core library: PDF → images → OCR → normalized text.
                      No GUI dependency; usable as a CLI tool or imported
                      as a module.

lao_pdf_ocr_gui.py    Tkinter GUI wrapping the same core functions.
                      Detects when running as a frozen PyInstaller .exe
                      and points Tesseract/Poppler at bundled copies
                      instead of relying on a system install.

tessdata/             Bundled Lao OCR model (tessdata_best quality) plus
                      the support files (configs/, tessconfigs/, pdf.ttf)
                      Tesseract needs to produce searchable-PDF output.

.github/workflows/    GitHub Actions workflow that builds LaoPdfOcr.exe
build-windows-exe.yml on a real Windows runner, bundling Tesseract,
                      Poppler, and tessdata/ into one file with
                      PyInstaller — and runs an actual OCR sanity check
                      against test_lao_scanned.pdf before publishing the
                      build as an artifact.

test_lao_scanned.pdf  A tiny synthetic scanned-style PDF ("ສະບາຍດີ
                      ປະເທດລາວ / ການບິນລາວ") used by the CI sanity check.
                      Deliberately small so the build stays fast.
```

## Processing pipeline

1. **Rasterize** — each PDF page is converted to an image via
   `pdf2image` (which shells out to Poppler's `pdftoppm`), **one page at a
   time** rather than converting the whole document up front. This keeps
   memory flat regardless of document length; converting a 50+ page PDF
   to images all at once at 300 DPI can exhaust memory on constrained
   machines.
2. **OCR** — each page image is passed to `pytesseract.image_to_string()`
   using the bundled `lao` model. `TESSDATA_PREFIX` is set as an
   environment variable rather than passed as a `--tessdata-dir` CLI flag
   (see "Windows quoting bug" below for why).
3. **Normalize** — raw OCR output passes through `normalize_lao_text()`
   (on by default; disable with `--no-normalize` / the GUI checkbox).
4. **Write output** — plain text per page, and optionally a searchable
   PDF (original image + invisible OCR text layer via
   `pytesseract.image_to_pdf_or_hocr`).

## Lao orthography normalization

Generic OCR output is technically valid Unicode but often not in the
*canonical* form a human would type, because Tesseract (like most OCR
engines) recognizes each glyph independently rather than reasoning about
Lao's combining-mark rules. `normalize_lao_text()` fixes three specific,
well-defined issues, all confirmed by direct testing (not assumed) to be
things plain Unicode NFC normalization does **not** already handle:

| Issue | Example | Fix |
|---|---|---|
| Decomposed AM vowel | NIGGAHITA (U+0ECD) + AA (U+0EB2), sometimes with a stray space between them | Compose to precomposed AM ຳ (U+0EB3) |
| Decomposed HO NO / HO MO ligatures | HO SUNG (U+0EAB) + NO (U+0E99) / MO (U+0EA1) | Compose to precomposed ໜ (U+0EDC) / ໝ (U+0EDD) |
| Stray space before a combining mark | A space can never legitimately separate a base consonant from its vowel/tone mark | Remove the space |

Why NFC alone doesn't fix these (verified directly, not assumed): Lao
vowel/tone marks carry Unicode combining class 0 (not a "combining
mark" for NFC's reordering purposes), and the ໜ/ໝ ligatures are
*compatibility* mappings, not *canonical* ones — so NFC/NFKC leave them
untouched. See the source comments in `lao_pdf_ocr.py` for the exact
regex patterns.

This is intentionally a narrow, rule-based cleanup — not a spell-checker
and not an LLM-based rewrite. It only fixes encoding-level defects with
one unambiguous correct answer; it will not (and should not attempt to)
correct genuine OCR misreadings of a character.

## Known Windows-specific bugs and how they were fixed

Building the bundled `.exe` surfaced several bugs that don't show up when
running the raw Python script on Linux/macOS with system-installed
Tesseract/Poppler already on `PATH`. Documented here so they don't get
silently reintroduced:

1. **`find_tessdata_dir()` returning a relative path.** The function
   originally returned whichever candidate path string matched, without
   resolving it to absolute. Harmless on Linux (where the fallback
   candidate — a path built from `Path(__file__).resolve()` — is already
   absolute and happens to catch the case), but on Windows CI, a relative
   `TESSDATA_PREFIX` environment variable could match successfully
   against the *current process's* working directory and get returned
   unresolved — then fail once handed to the Tesseract subprocess, which
   doesn't necessarily share that same working-directory assumption.
   **Fix:** `find_tessdata_dir()` now always returns `str(Path(c).resolve())`.

2. **`shlex.split()` not stripping quotes on Windows.** `pytesseract`
   parses its `config` string with
   `shlex.split(config, posix=not_windows)`. With `posix=False` (the
   Windows code path), `shlex` does **not** strip quote characters from
   tokens the way it does in POSIX mode — so
   `--tessdata-dir "C:\path\to\tessdata"` arrived at `tesseract.exe` with
   the literal quote marks still embedded in the path string, which then
   obviously didn't match any real directory. Confirmed by matching the
   resulting Tesseract error message character-for-character against a
   local reproduction of the bug.
   **Fix:** stopped passing `--tessdata-dir` as a CLI flag entirely;
   `TESSDATA_PREFIX` is set directly as an environment variable instead
   (Tesseract's original, native mechanism for locating its data files),
   which never goes through `shlex` parsing.

3. **Chocolatey-installed tools not appearing on `PATH` in the next CI
   step.** Each GitHub Actions step runs as a fresh process; a `PATH`
   update made by an installer in one step isn't automatically visible to
   the next step's process. **Fix:** explicitly re-import Chocolatey's
   PowerShell profile and call `refreshenv` before locating newly
   installed binaries, with a hardcoded-default-path fallback as a second
   line of defense.

4. **Uncertain internal layout of the Chocolatey `poppler` package.**
   Rather than guess at (and repeatedly re-guess) where Chocolatey's
   `poppler` package places its binaries, the build downloads a specific,
   pinned release of
   [`oschwartz10612/poppler-windows`](https://github.com/oschwartz10612/poppler-windows)
   directly and searches the small, self-contained extracted folder for
   `pdftoppm.exe` — no dependency on a third-party package's internal
   directory conventions.

5. **Console encoding (`cp1252`) can't print Lao text.** Windows consoles
   default to a legacy codepage that doesn't include Lao Unicode
   characters, so `print()`-ing OCR results directly to the CI log threw
   `UnicodeEncodeError`. This only affected the CI smoke-test's console
   output, not the app itself (which writes files with explicit
   `encoding="utf-8"` and displays text in Tkinter widgets, both of which
   are unaffected by console codepage). **Fix:** set `PYTHONUTF8=1` before
   the smoke-test's `python` invocation.

## Running the Python script directly

Install Tesseract and Poppler for your platform, then the Python packages:

```bash
pip install pytesseract pdf2image pypdf pillow
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr poppler-utils
```

**macOS:**
```bash
brew install tesseract poppler
```

**Windows:** install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
and [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases),
adding both to your `PATH`.

No separate download needed for the Lao model — it's bundled in this
repo's `tessdata/` folder, and `find_tessdata_dir()` finds it
automatically next to the script.

## The Windows build (`.github/workflows/build-windows-exe.yml`)

Runs on GitHub's `windows-latest` runner:

1. Checks out the repo, sets up Python 3.11.
2. Installs Tesseract via Chocolatey.
3. Downloads the pinned Poppler-for-Windows release directly (see bug #4
   above).
4. Locates and stages both into local `tesseract_bundle/` and
   `poppler_bin/` folders (bug #3 above).
5. Removes whichever `tessdata` Chocolatey's Tesseract package installed
   by default, so there's no ambiguity — only this repo's own
   `tessdata/` (tested, orthography-verified) is ever used.
6. Installs `pyinstaller`, `pytesseract`, `pdf2image`, `pypdf`, `pillow`.
7. Runs PyInstaller (`--onefile --windowed`) bundling
   `lao_pdf_ocr_gui.py` with `tessdata/`, `tesseract_bundle/`, and
   `poppler_bin/` as `--add-data`.
8. **Runs an actual OCR extraction** against `test_lao_scanned.pdf` using
   the same bundled Tesseract/Poppler/tessdata the `.exe` will use, and
   asserts the correct Lao text comes back — a green build means the OCR
   pipeline was verified working on real Windows, not just that a file
   got produced.
9. Uploads `LaoPdfOcr.exe` as a build artifact.

To trigger a build: push a change to any of the watched paths (see the
workflow's `on.push.paths`), or go to **Actions → Build Windows exe → Run
workflow** to trigger manually.

## Design decisions worth knowing before changing things

- **One page at a time, not the whole PDF at once** — see pipeline step 1.
  Don't revert `extract_text()` to a single `convert_from_path(pdf_path)`
  call without `first_page`/`last_page` — this was a real OOM bug on a
  58-page document at 300 DPI on a 4GB machine.
- **`tessdata_best`, not `tessdata_fast`** — deliberately chosen for
  accuracy over speed, appropriate for archival/document OCR rather than
  real-time use. If a faster model is ever substituted, re-verify output
  quality against known documents before shipping.
- **Never pass paths through `--tessdata-dir` as a quoted CLI string** —
  see bug #2 above. Use the `TESSDATA_PREFIX` environment variable for
  any future Tesseract configuration that involves a filesystem path.
