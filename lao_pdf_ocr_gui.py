#!/usr/bin/env python3
"""
Lao PDF OCR — desktop GUI

A simple point-and-click wrapper around the Lao OCR pipeline:
pick a scanned PDF, click Extract, get a .txt file (and optionally a
searchable PDF) next to the input file.

This is the file that gets compiled into a Windows .exe by
.github/workflows/build-windows-exe.yml — see BUILD.md for how to
trigger that build.
"""
import os
import sys
import threading
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# When frozen by PyInstaller, bundled data (tessdata/) is unpacked to
# sys._MEIPASS at runtime; when run as a plain script, it's next to this file.
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lao_pdf_ocr import extract_text, make_searchable_pdf  # noqa: E402

# When frozen into a Windows .exe, bundled copies of tesseract.exe and
# poppler's pdftoppm.exe are unpacked under BASE_DIR (see the build workflow
# for the --add-data layout). Point pytesseract/pdf2image at them explicitly
# so the app works with nothing installed on the target machine.
POPPLER_PATH: str | None = None
if getattr(sys, "frozen", False):
    import pytesseract

    tesseract_exe = BASE_DIR / "tesseract" / "tesseract.exe"
    if tesseract_exe.is_file():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_exe)

    tessdata_dir = BASE_DIR / "tessdata"
    if tessdata_dir.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(tessdata_dir)

    poppler_bin = BASE_DIR / "poppler_bin"
    if poppler_bin.is_dir():
        POPPLER_PATH = str(poppler_bin)


class LaoOcrApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lao PDF OCR")
        self.geometry("560x360")
        self.resizable(False, False)

        self.pdf_path: str | None = None
        self.searchable_var = tk.BooleanVar(value=False)
        self.normalize_var = tk.BooleanVar(value=True)

        pad = {"padx": 12, "pady": 8}

        tk.Label(self, text="Lao PDF OCR", font=("Segoe UI", 16, "bold")).pack(
            anchor="w", **pad
        )
        tk.Label(
            self,
            text="Extract text from a scanned PDF written in Lao script.",
            fg="#555",
        ).pack(anchor="w", padx=12)

        pick_frame = tk.Frame(self)
        pick_frame.pack(fill="x", **pad)
        self.file_label = tk.Label(
            pick_frame, text="No file selected", anchor="w", fg="#333"
        )
        self.file_label.pack(side="left", fill="x", expand=True)
        tk.Button(pick_frame, text="Choose PDF...", command=self.choose_file).pack(
            side="right"
        )

        opts_frame = tk.Frame(self)
        opts_frame.pack(fill="x", **pad)
        tk.Checkbutton(
            opts_frame,
            text="Normalize Lao orthography (recommended)",
            variable=self.normalize_var,
        ).pack(anchor="w")
        tk.Checkbutton(
            opts_frame,
            text="Also create a searchable PDF (slower)",
            variable=self.searchable_var,
        ).pack(anchor="w")

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=12, pady=(4, 0))

        self.status_label = tk.Label(self, text="", fg="#555", anchor="w")
        self.status_label.pack(fill="x", padx=12, pady=(4, 0))

        self.run_button = tk.Button(
            self,
            text="Extract Text",
            command=self.start_extraction,
            bg="#2563eb",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            height=2,
        )
        self.run_button.pack(fill="x", padx=12, pady=16)

        tk.Label(
            self,
            text=(
                "Output is saved next to the input PDF as <name>.txt\n"
                "(and <name>_searchable.pdf if that option is checked)."
            ),
            fg="#777",
            justify="left",
        ).pack(anchor="w", padx=12)

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Choose a scanned PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.pdf_path = path
            self.file_label.config(text=Path(path).name)

    def start_extraction(self):
        if not self.pdf_path:
            messagebox.showwarning("No file", "Choose a PDF first.")
            return
        self.run_button.config(state="disabled")
        self.status_label.config(text="Starting...")
        threading.Thread(target=self._run_extraction, daemon=True).start()

    def _set_status(self, text: str):
        self.status_label.config(text=text)

    def _run_extraction(self):
        try:
            pdf_path = Path(self.pdf_path)
            out_txt = pdf_path.with_suffix(".txt")

            from pypdf import PdfReader

            n_pages = len(PdfReader(str(pdf_path)).pages)
            self.after(0, self.progress.config, {"maximum": n_pages})

            # extract_text() prints "OCR page i/n..." to stderr per page;
            # tee that into the status label and progress bar.
            import io
            import contextlib

            class _Tee(io.StringIO):
                def write(_self, s):
                    if s.strip():
                        self.after(0, self._set_status, s.strip())
                        if "/" in s:
                            try:
                                i = int(s.split("page")[1].split("/")[0].strip())
                                self.after(0, self.progress.config, {"value": i})
                            except Exception:
                                pass
                    return len(s)

            with contextlib.redirect_stderr(_Tee()):
                pages_text = extract_text(
                    str(pdf_path),
                    normalize=self.normalize_var.get(),
                    poppler_path=POPPLER_PATH,
                )

            with open(out_txt, "w", encoding="utf-8") as f:
                for i, text in enumerate(pages_text, start=1):
                    f.write(f"--- Page {i} ---\n{text}\n\n")

            result_msg = f"Done. Text saved to:\n{out_txt}"

            if self.searchable_var.get():
                self.after(0, self._set_status, "Building searchable PDF...")
                out_pdf = pdf_path.with_name(pdf_path.stem + "_searchable.pdf")
                make_searchable_pdf(str(pdf_path), str(out_pdf), poppler_path=POPPLER_PATH)
                result_msg += f"\nSearchable PDF saved to:\n{out_pdf}"

            self.after(0, self._finish, True, result_msg)
        except Exception as e:
            tb = traceback.format_exc()
            self.after(0, self._finish, False, f"{e}\n\n{tb}")

    def _finish(self, ok: bool, message: str):
        self.run_button.config(state="normal")
        self.progress.config(value=0)
        self._set_status("Done" if ok else "Failed")
        if ok:
            messagebox.showinfo("Lao PDF OCR", message)
        else:
            messagebox.showerror("Lao PDF OCR — error", message)


if __name__ == "__main__":
    app = LaoOcrApp()
    app.mainloop()
