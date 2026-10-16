"""Visual desktop workspace for SkinForge AI.

Uses Tkinter from the Python standard library so the GUI does not add a heavy UI dependency.
"""

from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from typing import Any

from skinforge.ai import create_edit_recipe, create_plan
from skinforge.archive import extract_zip_safe, inspect_zip, validate_zip
from skinforge.assets import index_assets
from skinforge.bininspect import inspect_bin
from skinforge.texture import tint_texture
from skinforge.updater import UpdateError, check_for_update, install_latest_update
from skinforge.wad import extract_wad
from skinforge.workflow import apply_edit_recipe, parse_edit_recipe

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
        self.root.after(1800, self._check_updates_on_startup)

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
            "AI can plan changes and apply confirmed edits to supported raster textures. Model editing, game-specific DDS/TEX decoding, package compilation and in-game verification are not implemented yet.\n"
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
        ai_actions = tk.Frame(ai_tab, bg=BG)
        ai_actions.pack(fill="x")
        self._button(ai_actions, "Ask SkinForge AI", self._ask_ai, primary=True).pack(side="left")
        self._button(ai_actions, "Generate & apply supported edits", self._ai_apply_edits).pack(side="left", padx=(8, 0))
        self._button(ai_actions, "AI Settings", self._ai_settings).pack(side="left", padx=(8, 0))
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
        asset_actions = tk.Frame(assets_tab, bg=BG)
        asset_actions.pack(fill="x", anchor="w")
        self._button(asset_actions, "Choose extracted folder and index", self._choose_and_index).pack(side="left")
        self._button(asset_actions, "Tint a raster texture", self._tint_texture).pack(side="left", padx=(8, 0))
        self._button(asset_actions, "Extract .wad.client", self._extract_wad).pack(side="left", padx=(8, 0))
        self._button(asset_actions, "Inspect .bin", self._inspect_bin).pack(side="left", padx=(8, 0))
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
        ).pack(side="left", fill="x", expand=True)
        self._button(footer, "Check for updates", self._check_updates).pack(side="right")

    def _ai_provider_configured(self) -> bool:
        if os.getenv("SKINFORGE_AI_BASE_URL", "").strip() and os.getenv("SKINFORGE_AI_MODEL", "").strip():
            return True
        config_path = Path.home() / ".skinforge" / ".env"
        if not config_path.is_file():
            return False
        values: dict[str, str] = {}
        for line in config_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                values[key.strip()] = value.strip().strip('"').strip("'")
        return bool(values.get("SKINFORGE_AI_BASE_URL") and values.get("SKINFORGE_AI_MODEL"))

    def _ai_apply_edits(self) -> None:
        if not self._ai_provider_configured():
            if messagebox.askyesno("Connect SkinForge AI", "No AI provider is configured yet. Open AI Settings now?"):
                self._ai_settings()
            return
        request = self.skin_request.get().strip()
        if not request:
            messagebox.showwarning("Describe your skin", "Write the desired visual changes first.")
            return
        asset_root = filedialog.askdirectory(title="Choose extracted raster asset folder")
        if not asset_root:
            return
        output_root = filedialog.askdirectory(title="Choose an EMPTY separate output folder")
        if not output_root:
            return
        root = Path(asset_root).expanduser().resolve()
        output = Path(output_root).expanduser().resolve()
        if root == output or root in output.parents:
            messagebox.showerror("Unsafe output folder", "Choose a separate output folder, not inside the source.")
            return

        def generate() -> dict[str, Any]:
            inventory = index_assets(root)
            raw = create_edit_recipe(request, inventory)
            recipe = parse_edit_recipe(raw)
            known_textures = {
                item["path"] for item in inventory["files"]
                if item.get("category") == "texture"
                and Path(item["path"]).suffix.lower() in {".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp"}
            }
            for edit in recipe["edits"]:
                if edit["source"] not in known_textures:
                    raise ValueError(f"AI referenced an asset not present in the indexed raster inventory: {edit['source']}")
            return {"recipe": recipe, "asset_root": str(root), "output_root": str(output)}

        self._run_background("Generating safe AI edit recipe", generate, self._confirm_ai_edits)

    def _confirm_ai_edits(self, payload: dict[str, Any]) -> None:
        recipe = payload["recipe"]
        summary = str(recipe.get("summary", "AI proposed supported texture edits."))
        edits = recipe["edits"]
        preview = json.dumps(recipe, indent=2, ensure_ascii=False)
        self.ai_output.delete("1.0", "end")
        self.ai_output.insert("1.0", preview[:30000])
        if not edits:
            messagebox.showinfo("No supported edits proposed", summary)
            return
        if not messagebox.askyesno(
            "Review AI edit recipe",
            f"{summary}\n\nThe AI proposes {len(edits)} raster texture edit(s). "
            "Original assets will not be overwritten. Apply them to the selected output folder?",
        ):
            self._append("AI edit recipe generated but not applied.")
            return

        def apply() -> dict[str, Any]:
            return apply_edit_recipe(recipe, payload["asset_root"], payload["output_root"])

        self._run_background(
            "Applying confirmed AI texture edits",
            apply,
            lambda report: self._append(
                "AI texture workflow complete:\\n" + json.dumps(report, indent=2, ensure_ascii=False)[:30000]
            ),
        )

    def _extract_wad(self) -> None:
        source = filedialog.askopenfilename(
            title="Choose a League WAD archive",
            filetypes=[("League WAD archives", "*.wad.client *.wad"), ("All files", "*.*")],
        )
        if not source:
            return
        output = filedialog.askdirectory(title="Choose an EMPTY output folder")
        if not output:
            return
        source_path = Path(source).expanduser().resolve()
        output_path = Path(output).expanduser().resolve()
        if (
            output_path == source_path.parent or source_path.parent in output_path.parents
        ) and not messagebox.askyesno(
            "Check output folder",
            "The output folder is inside the source archive's directory tree. Continue only if it is a separate, empty folder.",
        ):
            return

        def extract() -> dict[str, Any]:
            result = extract_wad(source_path, output_path)
            if result.returncode:
                detail = (result.stderr or result.stdout or "wadtools extraction failed").strip()
                raise RuntimeError(f"wadtools exited with code {result.returncode}: {detail[-3000:]}")
            return {
                "source": str(source_path),
                "output": str(output_path),
                "stdout": result.stdout[-5000:],
                "stderr": result.stderr[-2000:],
            }

        def done(report: dict[str, Any]) -> None:
            self.output_path.set(str(output_path))
            self._append("WAD extraction completed:\n" + json.dumps(report, indent=2, ensure_ascii=False))
            self._index(output_path)

        self._run_background("Extracting WAD with LeagueToolkit wadtools", extract, done)

    def _inspect_bin(self) -> None:
        source = filedialog.askopenfilename(
            title="Choose a BIN asset",
            filetypes=[("League BIN assets", "*.bin"), ("All files", "*.*")],
        )
        if not source:
            return

        def done(report: dict[str, Any]) -> None:
            self._append("BIN inspection (metadata only, not full Riot BIN decoding):\n" +
                         json.dumps(report, indent=2, ensure_ascii=False))
            self.ai_output.delete("1.0", "end")
            self.ai_output.insert("1.0", json.dumps(report, indent=2, ensure_ascii=False)[:50000])

        self._run_background("Inspecting BIN metadata", lambda: inspect_bin(source), done)

    def _tint_texture(self) -> None:
        source = filedialog.askopenfilename(
            title="Choose a raster texture",
            filetypes=[("Supported raster textures", "*.png *.jpg *.jpeg *.tga *.bmp *.webp")],
        )
        if not source:
            return
        selected = colorchooser.askcolor(title="Choose tint color")
        if not selected or not selected[1]:
            return
        strength = simpledialog.askfloat(
            "Tint strength", "Blend strength from 0.0 to 1.0", initialvalue=0.35,
            minvalue=0.0, maxvalue=1.0, parent=self.root,
        )
        if strength is None:
            return
        destination = filedialog.asksaveasfilename(
            title="Save edited texture as a new file",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("TGA image", "*.tga"), ("WEBP image", "*.webp"), ("BMP image", "*.bmp")],
        )
        if not destination:
            return
        self._run_background(
            "Tinting texture",
            lambda: tint_texture(source, destination, selected[1], strength=strength),
            lambda report: self._append("Texture edit complete (original preserved):\\n" + json.dumps(report, indent=2)),
        )

    def _check_updates_on_startup(self) -> None:
        """Check quietly at launch; only interrupt the user when an update exists."""
        def worker() -> None:
            try:
                self.jobs.put(("startup_update", check_for_update()))
            except (UpdateError, RuntimeError, ValueError):
                # Startup must remain usable when GitHub is unreachable or private-repo auth
                # has not been configured. The user can run a manual check from the footer.
                return

        threading.Thread(target=worker, daemon=True).start()

    def _check_updates(self) -> None:
        self._run_background("Checking for updates", check_for_update, self._handle_update_result)

    def _handle_update_result(self, info: dict[str, Any]) -> None:
        latest = info.get("latest_version", "unknown")
        current = info.get("current_version", "unknown")
        if not info.get("update_available"):
            messagebox.showinfo("SkinForge AI is up to date", f"Installed version: {current}")
            return
        if not info.get("wheel"):
            messagebox.showwarning(
                "Update found",
                f"Version {latest} is available, but this release has no installable wheel yet.\n\n"
                f"Open the release page?\n{info.get('release_url', '')}",
            )
            return
        if messagebox.askyesno(
            "SkinForge AI update available",
            f"Installed: {current}\nLatest: {latest}\n\n"
            "Download and install the official release now? The app will need to be restarted.",
        ):
            self._run_background(
                "Installing update",
                lambda: install_latest_update(info),
                self._update_installed,
            )

    def _update_installed(self, version: str) -> None:
        self._append(f"SkinForge AI {version} installed. Restart the app to use the new version.")
        self.status.set(f"Updated to {version}; restart required")
        messagebox.showinfo(
            "Update installed",
            f"SkinForge AI {version} was installed. Close and reopen the app to finish updating.",
        )

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
                elif kind == "startup_update":
                    if payload.get("update_available"):
                        self._handle_update_result(payload)
                else:
                    label, result, callback = payload
                    self.status.set(label + " complete")
                    callback(result)
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

    def _ai_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("SkinForge AI Settings")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        panel = tk.Frame(dialog, bg=PANEL, padx=22, pady=20)
        panel.pack(fill="both", expand=True, padx=16, pady=16)

        self._label(panel, "CONNECT YOUR AI PROVIDER", size=12, color=ACCENT).pack(anchor="w")
        self._label(
            panel,
            "Use an OpenAI-compatible API endpoint. Your key is saved locally on this computer.",
            color=MUTED,
        ).pack(anchor="w", pady=(6, 16))

        fields = (
            ("API base URL", "SKINFORGE_AI_BASE_URL", False),
            ("Model name", "SKINFORGE_AI_MODEL", False),
            ("API key", "SKINFORGE_AI_API_KEY", True),
        )
        variables: dict[str, tk.StringVar] = {}
        saved_settings: dict[str, str] = {}
        config_path = Path.home() / ".skinforge" / ".env"
        if config_path.is_file():
            for line in config_path.read_text(encoding="utf-8").splitlines():
                name, separator, raw_value = line.partition("=")
                if separator and name.strip().startswith("SKINFORGE_AI_"):
                    saved_settings[name.strip()] = raw_value.strip().strip('"').strip("'")
        for label, key, secret in fields:
            self._label(panel, label, color=TEXT).pack(anchor="w", pady=(5, 4))
            variable = tk.StringVar(value=os.getenv(key, saved_settings.get(key, "")))
            variables[key] = variable
            entry = tk.Entry(
                panel,
                textvariable=variable,
                bg=PANEL_LIGHT,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                width=64,
                show="*" if secret else "",
                font=("Segoe UI", 10),
            )
            entry.pack(fill="x", ipady=8)

        def save() -> None:
            config_dir = Path.home() / ".skinforge"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / ".env"
            lines: list[str] = []
            for _, key, _ in fields:
                value = variables[key].get().strip()
                if not value:
                    continue
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key}="{escaped}"')
                os.environ[key] = value
            config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self.status.set("AI settings saved locally")
            self._append("AI provider settings saved to the local user configuration.")
            dialog.destroy()

        self._button(panel, "Save AI Settings", save, primary=True).pack(anchor="w", pady=(18, 0))

    def _ask_ai(self) -> None:
        if not self._ai_provider_configured():
            if messagebox.askyesno("Connect SkinForge AI", "No AI provider is configured yet. Open AI Settings now?"):
                self._ai_settings()
            return
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
