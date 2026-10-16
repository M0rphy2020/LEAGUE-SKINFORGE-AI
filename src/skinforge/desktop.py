"""Visual desktop workspace for SkinForge AI.

Uses Tkinter from the Python standard library so the GUI does not add a heavy UI dependency.
"""

from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from skinforge.ai import create_plan
from skinforge.archive import extract_zip_safe, inspect_zip, validate_zip
from skinforge.assets import index_assets

BG = "#10131b"
PANEL = "#191f2b"
PANEL_LIGHT = "#222b3b"
TEXT = "#edf2ff"
MUTED = "#a7b2c8"
ACCENT = "#8b7cff"
SUCCESS = "#63d9a5"
WARNING = "#ffc875"


class SkinForgeDesktop:
    """Small GUI wrapper around the existing inspection, extraction and AI tools."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SkinForge AI | Custom Skin Workshop")
        self.root.geometry("1100x760")
        self.root.minsize(900, 640)
        self.root.configure(bg=BG)
        self.jobs: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.package_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.skin_request = tk.StringVar()
        self.status = tk.StringVar(value="Ready · Select a .fantome package to begin")
        self._configure_styles()
        self._build_layout()
        self.root.after(120, self._poll_jobs)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0)
        )
        style.configure(
            "TNotebook.Tab",
            background=PANEL_LIGHT,
            foreground=MUTED,
            padding=(18, 10),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", ACCENT)],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=TEXT,
            rowheight=30,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=PANEL_LIGHT,
            foreground=TEXT,
            relief="flat",
        )

    def _label(self, parent: tk.Widget, text: str, *, size: int = 10, color: str = TEXT) -> tk.Label:
        return tk.Label(
            parent, text=text, bg=parent.cget("bg"), fg=color,
            font=("Segoe UI", size), anchor="w",
        )

    def _button(
        self, parent: tk.Widget, text: str, command: Callable[[], None], *, primary: bool = False
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ACCENT if primary else PANEL_LIGHT,
            fg="#ffffff" if primary else TEXT,
            activebackground="#7565ed" if primary else "#303b50",
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            padx=14,
            pady=10,
            cursor="hand2",
            font=("Segoe UI Semibold", 10),
        )

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg=BG, padx=28, pady=22)
        header.pack(fill="x")
        tk.Label(
            header, text="SKINFORGE", bg=BG, fg=ACCENT,
            font=("Segoe UI Semibold", 12),
        ).pack(anchor="w")
        tk.Label(
            header, text="AI Custom Skin Workshop", bg=BG, fg=TEXT,
            font=("Segoe UI Semibold", 25),
        ).pack(anchor="w", pady=(3, 2))
        self._label(
            header,
            "Inspect packages, map assets and ask the skin-focused AI for the next step.",
            size=11,
            color=MUTED,
        ).pack(anchor="w")

        body = tk.Frame(self.root, bg=BG, padx=28)
        body.pack(fill="both", expand=True)

        source = tk.Frame(body, bg=PANEL, padx=16, pady=14)
        source.pack(fill="x", pady=(0, 16))
        self._label(source, "1  ·  YOUR SKIN PACKAGE", size=10, color=ACCENT).pack(anchor="w")
        row = tk.Frame(source, bg=PANEL)
        row.pack(fill="x", pady=(8, 10))
        tk.Entry(
            row, textvariable=self.package_path, bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        ).pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 8))
        self._button(row, "Browse .fantome", self._choose_package).pack(side="left")
        out_row = tk.Frame(source, bg=PANEL)
        out_row.pack(fill="x")
        self._label(out_row, "Output folder", color=MUTED).pack(side="left", padx=(0, 14))
        tk.Entry(
            out_row, textvariable=self.output_path, bg=PANEL_LIGHT, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 10),
        ).pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self._button(out_row, "Choose folder", self._choose_output).pack(side="left")

        notebook = ttk.Notebook(body)
        notebook.pack(fill="both", expand=True)
        overview = tk.Frame(notebook, bg=BG, padx=4, pady=14)
        ai_tab = tk.Frame(notebook, bg=BG, padx=4, pady=14)
        assets_tab = tk.Frame(notebook, bg=BG, padx=4, pady=14)
        notebook.add(overview, text="Workshop")
        notebook.add(ai_tab, text="AI Skin Assistant")
        notebook.add(assets_tab, text="Asset Explorer")

        cards = tk.Frame(overview, bg=BG)
        cards.pack(fill="x")
        self._make_card(cards, "PACKAGE INSPECTOR", "Review files, sizes and archive metadata.", "Inspect package", self._inspect)
        self._make_card(cards, "SAFE EXTRACT", "Validate the archive before extracting files.", "Extract package", self._extract)
        self._make_card(cards, "ASSET INDEX", "Sort textures, models, BIN, audio and more.", "Index output folder", self._index)
        self._label(overview, "ACTIVITY & RESULTS", color=MUTED).pack(anchor="w", pady=(18, 8))
        self.log = tk.Text(
            overview, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat",
            wrap="word", font=("Consolas", 10), padx=14, pady=12,
        )
        self.log.pack(fill="both", expand=True)
        self._append(
            "Welcome to SkinForge AI.\n"
            "The GUI is the main workspace; you do not need to type terminal commands.\n"
            "Current AI mode creates an asset-aware work plan. Direct model/texture editing "
            "and in-game verification are not implemented yet.\n"
        )

        self._label(ai_tab, "DESCRIBE THE SKIN YOU WANT", size=11, color=ACCENT).pack(anchor="w")
        self._label(
            ai_tab,
            "Be specific about the champion, visual theme, colors, effects and what should stay unchanged.",
            color=MUTED,
        ).pack(anchor="w", pady=(5, 10))
        tk.Entry(
            ai_tab, textvariable=self.skin_request, bg=PANEL, fg=TEXT,
            insertbackground=TEXT, relief="flat", font=("Segoe UI", 11),
        ).pack(fill="x", ipady=12, pady=(0, 10))
        self._button(ai_tab, "Ask SkinForge AI", self._ask_ai, primary=True).pack(anchor="w")
        self.ai_output = tk.Text(
            ai_tab, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat",
            wrap="word", font=("Segoe UI", 10), padx=14, pady=12,
        )
        self.ai_output.pack(fill="both", expand=True, pady=(14, 0))
        self.ai_output.insert(
            "1.0",
            "Your AI work plan will appear here. Configure the provider in the local .env file "
            "using .env.example. Never paste API keys into the request box.",
        )

        self._label(assets_tab, "ASSET INVENTORY", size=11, color=ACCENT).pack(anchor="w")
        self._label(
            assets_tab, "Choose an extracted folder with the button below to classify its files.",
            color=MUTED,
        ).pack(anchor="w", pady=(4, 12))
        self._button(assets_tab, "Choose extracted folder and index", self._choose_and_index).pack(anchor="w")
        self.asset_table = ttk.Treeview(
            assets_tab, columns=("kind", "size", "path"), show="headings",
        )
        self.asset_table.heading("kind", text="Type")
        self.asset_table.heading("size", text="Size")
        self.asset_table.heading("path", text="Relative path")
        self.asset_table.column("kind", width=120, stretch=False)
        self.asset_table.column("size", width=100, stretch=False)
        self.asset_table.column("path", width=600)
        self.asset_table.pack(fill="both", expand=True, pady=(12, 0))

        footer = tk.Frame(self.root, bg=PANEL, padx=28, pady=10)
        footer.pack(fill="x", side="bottom")
        tk.Label(
            footer, textvariable=self.status, bg=PANEL, fg=SUCCESS,
            font=("Segoe UI", 9), anchor="w",
        ).pack(fill="x")

    def _make_card(
        self, parent: tk.Widget, title: str, description: str, button: str, command: Callable[[], None]
    ) -> None:
        card = tk.Frame(parent, bg=PANEL, padx=14, pady=14)
        card.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._label(card, title, color=ACCENT).pack(anchor="w")
        self._label(card, description, color=MUTED).pack(anchor="w", pady=(8, 16))
        self._button(card, button, command, primary=True).pack(anchor="w")

    def _append(self, text: str) -> None:
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def _choose_package(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a skin package",
            filetypes=[("Fantome packages", "*.fantome"), ("ZIP archives", "*.zip"), ("All files", "*.*")],
        )
        if path:
            self.package_path.set(path)
            if not self.output_path.get():
                self.output_path.set(str(Path(path).with_suffix("")) + "_extracted")
            self.status.set("Package selected")

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_path.set(path)

    def _require_package(self) -> Path | None:
        path = Path(self.package_path.get()).expanduser()
        if not path.is_file():
            messagebox.showwarning("Choose a package", "Select an existing .fantome or ZIP file first.")
            return None
        return path

    def _run_background(self, label: str, job: Callable[[], Any], callback: Callable[[Any], None]) -> None:
        self.status.set(label + "…")
        self._append(label + "…")

        def worker() -> None:
            try:
                result = job()
                self.jobs.put(("success", (label, result, callback)))
            except (OSError, ValueError, RuntimeError) as exc:
                self.jobs.put(("error", (label, str(exc))))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_jobs(self) -> None:
        try:
            while True:
                kind, payload = self.jobs.get_nowait()
                if kind == "error":
                    label, error = payload
                    self.status.set(label + " failed")
                    self._append("ERROR: " + error)
                    messagebox.showerror(label, error)
                else:
                    label, result, callback = payload
                    callback(result)
                    self.status.set(label + " complete")
        except queue.Empty:
            pass
        self.root.after(120, self._poll_jobs)

    def _inspect(self) -> None:
        path = self._require_package()
        if path is None:
            return

        def done(report: dict[str, Any]) -> None:
            self._append(json.dumps(report, indent=2, ensure_ascii=False)[:30000])

        self._run_background("Inspecting package", lambda: inspect_zip(path), done)

    def _extract(self) -> None:
        path = self._require_package()
        if path is None:
            return
        output = Path(self.output_path.get()).expanduser()
        self._run_background(
            "Validating and extracting",
            lambda: extract_zip_safe(path, output),
            lambda result: self._append(json.dumps(result, indent=2, ensure_ascii=False)),
        )

    def _index(self, folder: Path | None = None) -> None:
        chosen = folder or Path(self.output_path.get()).expanduser()
        if not chosen.is_dir():
            messagebox.showwarning("Choose a folder", "Choose an existing extracted asset folder first.")
            return

        def done(report: dict[str, Any]) -> None:
            for item in self.asset_table.get_children():
                self.asset_table.delete(item)
            for item in report["files"]:
                self.asset_table.insert(
                    "", "end",
                    values=(item["category"], f'{item["size"]:,} B', item["path"]),
                )
            self._append(
                "Asset index: "
                + json.dumps(report["category_counts"], ensure_ascii=False)
                + f" · {report['file_count']} files"
            )

        self._run_background("Indexing assets", lambda: index_assets(chosen), done)

    def _choose_and_index(self) -> None:
        path = filedialog.askdirectory(title="Select an extracted asset folder")
        if path:
            self._index(Path(path))

    def _ask_ai(self) -> None:
        path = self._require_package()
        request = self.skin_request.get().strip()
        if path is None:
            return
        if not request:
            messagebox.showinfo("Describe your skin", "Tell the AI what kind of custom skin you want.")
            return

        def ask() -> str:
            report = validate_zip(path)
            output = Path(self.output_path.get()).expanduser()
            if output.is_dir():
                report["extracted_asset_inventory"] = index_assets(output)
            return create_plan(
                "Custom-skin request: " + request
                + "\nFocus on League of Legends custom-skin assets, mapping the requested visual changes "
                "to candidate files, distinguishing confirmed facts from guesses, and listing validation "
                "steps. Do not claim you have edited or built assets.",
                report,
            )

        def done(answer: str) -> None:
            self.ai_output.delete("1.0", "end")
            self.ai_output.insert("1.0", answer)
            self._append("AI work plan received.")

        self._run_background("Consulting SkinForge AI", ask, done)


def main() -> None:
    root = tk.Tk()
    SkinForgeDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
