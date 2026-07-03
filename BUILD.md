# Building the Windows app

This folder is a small, self-contained project that GitHub will build into a
double-click Windows app (`LaoPdfOcr.exe`) for you — **you don't need Python,
Tesseract, or anything else installed on your own machine.** GitHub's own
Windows servers do the actual building and testing; you just upload this
folder and click a button.

## One-time setup (about 5 minutes)

1. Go to https://github.com and create a free account if you don't have one.
2. Click the **+** in the top-right corner → **New repository**. Name it
   anything (e.g. `lao-pdf-ocr`). Keep it **Private** if you'd prefer — this
   works the same either way. Click **Create repository**.
3. On the new repository's page, click **uploading an existing file** (or
   **Add file → Upload files** if you don't see that link).
4. Drag this entire folder's contents into the upload box — all of
   `lao_pdf_ocr.py`, `lao_pdf_ocr_gui.py`, `test_lao_scanned.pdf`, the
   `tessdata` folder, and the `.github` folder (GitHub's uploader preserves
   folder structure when you drag a folder in; if it flattens it, use
   **git** locally instead — see "Alternative" below).
5. Scroll down, click **Commit changes**.

## Running the build

1. Click the **Actions** tab near the top of your repository page.
2. You should see a workflow called **Build Windows exe** in the left
   sidebar. Click it.
3. Click the **Run workflow** button (top right of the list), then the green
   **Run workflow** button in the dropdown.
4. Wait — this takes about 3–5 minutes. GitHub is spinning up an actual
   Windows machine, installing Tesseract and Poppler, building the app, and
   running a sanity check that OCRs the included test PDF and checks the Lao
   text comes back correctly.
5. When the run finishes with a green checkmark, click into it, scroll down
   to **Artifacts**, and download **LaoPdfOcr-windows**. That's a zip
   containing `LaoPdfOcr.exe`.
6. Unzip it and double-click `LaoPdfOcr.exe` to run — no install needed.
   (Windows SmartScreen may warn about an unrecognized publisher the first
   time, since this isn't code-signed — click "More info" → "Run anyway".)

If the run fails (red X instead of green check), click into it to see which
step failed and the error output — that's specific, actionable information
I can help debug from, rather than a black box.

## What actually happens during the build

- Installs Tesseract OCR and Poppler via Chocolatey (Windows' package
  manager) on a temporary GitHub-hosted Windows machine.
- Removes whichever `tessdata` Tesseract installed by default, so there's no
  ambiguity — the app only ever uses the Lao model bundled in this repo's
  `tessdata/` folder (the same `tessdata_best`-quality model already tested
  in chat).
- Packages `lao_pdf_ocr_gui.py`, Tesseract, Poppler, and the Lao model
  together into one `.exe` with PyInstaller.
- **Actually runs the OCR pipeline** against `test_lao_scanned.pdf` and
  checks the extracted text contains the expected Lao characters, before
  ever uploading the exe — so a passing build means the OCR really works on
  a real Windows machine, not just that the exe file was produced.

## Alternative: using git instead of drag-and-drop

If you're comfortable with git and have it installed:

```
git init
git add .
git commit -m "Lao PDF OCR app"
git remote add origin https://github.com/<your-username>/lao-pdf-ocr.git
git push -u origin main
```

Then follow "Running the build" above.

## Updating the app later

Any time `lao_pdf_ocr.py` or `lao_pdf_ocr_gui.py` changes, just re-upload the
changed file(s) through the same **Add file → Upload files** flow (this
automatically triggers a rebuild, since the workflow watches those paths) —
or re-run the workflow manually from the Actions tab.

## Releases & versioning

Every commit to GitHub is already version control — the full history of
every change is preserved and can always be inspected or rolled back to,
whether or not you do anything else. What tagged **Releases** add on top
of that is a clear, stable signpost for anyone downloading the app: "this
specific point in history is the one that's tested and works," rather than
them having to guess which commit in the history is good.

This matters more once a repo is public: the commit history includes every
intermediate step taken to get the Windows build working (including a few
that didn't work yet), which is genuinely useful as a debugging record but
isn't what a random visitor wants to download.

**To cut a release, once a build has gone green:**

1. Go to the **Releases** section (right-hand sidebar on the repo's main
   page, or `/releases` in the URL).
2. Click **Create a new release** / **Draft a new release**.
3. Under "Choose a tag," type a version number — `v1.0.0` for the first
   release. This project follows [Semantic Versioning](https://semver.org/):
   increment the last number for a bug fix (`v1.0.1`), the middle number
   for a new feature that doesn't break existing usage (`v1.1.0`), and the
   first number for a breaking change (`v2.0.0`).
4. Give it a title and paste in the relevant section from `CHANGELOG.md`
   as the description.
5. Download `LaoPdfOcr.exe` from the successful Actions run's Artifacts
   (as in "Running the build" above), and drag it into the release's
   **Attach binaries** box. This is what makes the exe downloadable
   directly from the Releases page, instead of visitors needing to know
   to go dig through the Actions tab.
6. Click **Publish release**.

After that, `CHANGELOG.md`'s `[Unreleased]` section is where new changes
get logged until the next release is cut.
