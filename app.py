from __future__ import annotations

import queue
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from tkinterdnd2 import DND_FILES, TkinterDnD

from database import test_database_connection
from main import (
    SUPPORTED_EXTENSIONS,
    process_dwg_file,
    process_item_file,
    validate_input_file,
)


APP_TITLE = "BOQ Importer"

# Organic Professional palette
BG_LIGHT = "#0D1117"
BG_DARK = "#0D1117"

SURFACE_LIGHT = "#161B22"
SURFACE_DARK = "#161B22"

SURFACE_ALT_LIGHT = "#0A0E14"
SURFACE_ALT_DARK = "#0A0E14"

ACCENT = "#58A6FF"
ACCENT_HOVER = "#79B8FF"
ACCENT_SOFT = "#0D2238"

SECONDARY = "#D29922"
SECONDARY_HOVER = "#E3B341"

SUCCESS = "#2EA043"
DANGER = "#DA3633"

TEXT_LIGHT = "#E6EDF3"
TEXT_DARK = "#E6EDF3"
TEXT_MUTED = ("#FFFFFF", "#FFFFFF")

BORDER_LIGHT = "#21262D"
BORDER_DARK = "#21262D"


class TkinterDnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    """CustomTkinter root with native file drag-and-drop support."""

    def __init__(self) -> None:
        ctk.CTk.__init__(self)
        self.TkdndVersion = TkinterDnD._require(self)


class BOQImporterApp(TkinterDnDCTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.title(APP_TITLE)
        self.geometry("950x600")
        self.minsize(840, 750)
        self.configure(fg_color=(BG_LIGHT, BG_DARK))

        self.selected_file: Path | None = None
        self.is_processing = False
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_content()
        self._build_footer()
        self.after(100, self._poll_events)
        self.after(250, self._start_database_test)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(
            self,
            corner_radius=24,
            fg_color=("#161B22", "#161B22"),
            border_width=1,
            border_color=("#21262D", "#21262D"),
        )
        header.grid(row=0, column=0, padx=24, pady=(20, 0), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        brand_row = ctk.CTkFrame(header, fg_color="transparent")
        brand_row.grid(row=0, column=0, padx=28, pady=(22, 4), sticky="w")

        ctk.CTkLabel(
            brand_row,
            text="BOQ",
            font=ctk.CTkFont(size=29, weight="bold"),
            text_color="#E6EDF3",
        ).pack(side="left")

        ctk.CTkLabel(
            brand_row,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#8B949E",
        ).pack(side="left", padx=(8, 0), pady=(8, 0))

        subtitle = ctk.CTkLabel(
            header,
            text="Bill of Quantities",
            font=ctk.CTkFont(size=14),
            text_color="#8B949E",
        )
        subtitle.grid(row=1, column=0, padx=28, pady=(0, 22), sticky="w")

        self.db_badge = ctk.CTkLabel(
            header,
            text="●  Connecting to database…",
            fg_color=("#21262D", "#21262D"),
            corner_radius=16,
            text_color="#E6EDF3",
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=15,
            pady=8,
        )
        self.db_badge.grid(row=0, rowspan=2, column=1, padx=28, pady=24)

    def _build_content(self) -> None:
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=24, pady=22, sticky="nsew")
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(0, weight=1)

        self._build_upload_card(content)
        self._build_log_card(content)

    def _build_upload_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            corner_radius=24,
            fg_color=(SURFACE_LIGHT, SURFACE_DARK),
            border_width=1,
            border_color=(BORDER_LIGHT, BORDER_DARK),
        )
        card.grid(row=0, column=0, padx=(0, 12), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            card,
            text="Select a file",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=26, pady=(24, 4), sticky="w")

        ctk.CTkLabel(
            card,
            text="Supported formats: .xlsx, .xls, .pdf and .dwg",
            text_color=TEXT_MUTED,
        ).grid(row=1, column=0, padx=26, pady=(0, 16), sticky="w")

        self.drop_zone = ctk.CTkFrame(
            card,
            corner_radius=22,
            border_width=2,
            border_color=("#30363D", "#30363D"),
            fg_color=("#0D2238", "#0D2238"),
        )
        self.drop_zone.grid(row=2, column=0, padx=26, pady=8, sticky="nsew")
        self.drop_zone.grid_columnconfigure(0, weight=1)
        self.drop_zone.grid_rowconfigure(0, weight=1)

        drop_content = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        drop_content.grid(row=0, column=0)

        ctk.CTkLabel(
            drop_content,
            text="⇩",
            font=ctk.CTkFont(size=52, weight="bold"),
            text_color=ACCENT,
        ).pack(pady=(8, 0))

        self.drop_title = ctk.CTkLabel(
            drop_content,
            text="Drag and drop your file here",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.drop_title.pack(pady=(5, 3))

        self.drop_subtitle = ctk.CTkLabel(
            drop_content,
            text="or choose it from your computer",
            text_color=TEXT_MUTED,
        )
        self.drop_subtitle.pack(pady=(0, 14))

        self.browse_button = ctk.CTkButton(
            drop_content,
            text="Browse files",
            command=self._browse_file,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            height=44,
            width=160,
            corner_radius=22,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.browse_button.pack(pady=(0, 12))

        for widget in (self.drop_zone, drop_content, self.drop_title, self.drop_subtitle):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

        self.file_info = ctk.CTkFrame(
            card,
            corner_radius=18,
            fg_color=(SURFACE_ALT_LIGHT, SURFACE_ALT_DARK),
            border_width=1,
            border_color=(BORDER_LIGHT, BORDER_DARK),
        )
        self.file_info.grid(row=3, column=0, padx=26, pady=(14, 8), sticky="ew")
        self.file_info.grid_columnconfigure(1, weight=1)

        self.file_icon = ctk.CTkLabel(self.file_info, text="📄", font=ctk.CTkFont(size=28))
        self.file_icon.grid(row=0, rowspan=2, column=0, padx=(16, 10), pady=14)

        self.file_name_label = ctk.CTkLabel(
            self.file_info,
            text="No file selected",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self.file_name_label.grid(row=0, column=1, padx=(0, 12), pady=(12, 0), sticky="ew")

        self.file_details_label = ctk.CTkLabel(
            self.file_info,
            text="Choose one file to begin",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.file_details_label.grid(row=1, column=1, padx=(0, 12), pady=(0, 12), sticky="ew")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=4, column=0, padx=26, pady=(10, 24), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)

        self.import_button = ctk.CTkButton(
            actions,
            text="Import to database",
            command=self._start_import,
            state="disabled",
            height=50,
            corner_radius=24,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=SUCCESS,
            hover_color="#3FB950",
            text_color="#0D1117",
        )
        self.import_button.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.clear_button = ctk.CTkButton(
            actions,
            text="Clear",
            command=self._clear_selection,
            width=105,
            height=50,
            corner_radius=24,
            fg_color="transparent",
            border_width=1,
            text_color=(TEXT_LIGHT, TEXT_DARK),
            border_color=(BORDER_LIGHT, BORDER_DARK),
            hover_color=(SURFACE_ALT_LIGHT, SURFACE_ALT_DARK),
        )
        self.clear_button.grid(row=0, column=1)

    def _build_log_card(self, parent: ctk.CTkFrame) -> None:
        card = ctk.CTkFrame(
            parent,
            corner_radius=24,
            fg_color=(SURFACE_LIGHT, SURFACE_DARK),
            border_width=1,
            border_color=(BORDER_LIGHT, BORDER_DARK),
        )
        card.grid(row=0, column=1, padx=(12, 0), sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            card,
            text="Status",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(24, 4), sticky="w")

        self.status_label = ctk.CTkLabel(
            card,
            text="Ready",
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="ew")

        self.progress = ctk.CTkProgressBar(
            card,
            mode="indeterminate",
            height=9,
            corner_radius=10,
            progress_color=ACCENT,
            fg_color=("#0A0E14", "#0A0E14"),
        )
        self.progress.grid(row=2, column=0, padx=24, pady=(0, 14), sticky="ew")
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(
            card,
            corner_radius=18,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            fg_color=("#0A0E14", "#0A0E14"),
            border_width=1,
            border_color=(BORDER_LIGHT, BORDER_DARK),
            text_color=(TEXT_LIGHT, TEXT_DARK),
        )
        self.log_box.grid(row=3, column=0, padx=24, pady=(0, 16), sticky="nsew")
        self.log_box.insert("end", "Waiting for a file.\n")
        self.log_box.configure(state="disabled")


    def _build_footer(self) -> None:
        footer = ctk.CTkLabel(
            self,
            text="",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=12),
        )
        footer.grid(row=2, column=0, padx=24, pady=(0, 18))

    def _browse_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select a BOQ file",
            filetypes=[
                ("Supported files", "*.xlsx *.xls *.pdf *.dwg"),
                ("Excel files", "*.xlsx *.xls"),
                ("PDF files", "*.pdf"),
                ("AutoCAD drawings", "*.dwg"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._select_file(Path(path))

    def _on_drop(self, event: object) -> None:
        try:
            raw_data = getattr(event, "data", "")
            paths = self.tk.splitlist(raw_data)
            if paths:
                self._select_file(Path(paths[0]))
        except Exception as error:
            messagebox.showerror("Invalid drop", str(error))

    def _select_file(self, file_path: Path) -> None:
        try:
            file_path = file_path.expanduser().resolve()
            validate_input_file(file_path)
        except Exception as error:
            self._set_status("Unsupported file", DANGER)
            messagebox.showerror("Cannot select file", str(error))
            return

        self.selected_file = file_path
        extension = file_path.suffix.lower()
        size_mb = file_path.stat().st_size / (1024 * 1024)
        icon = {".xlsx": "", ".xls": "", ".pdf": "", ".dwg": ""}.get(extension, "")

        self.file_icon.configure(text=icon)
        self.file_name_label.configure(text=file_path.name)
        self.file_details_label.configure(text=f"{extension.upper()[1:]} • {size_mb:.2f} MB • {file_path.parent}")
        self.drop_title.configure(text="File ready for import")
        self.drop_subtitle.configure(text="Drop another file here to replace it")
        self.import_button.configure(state="normal")
        self._set_status("Ready to import", ACCENT)
        self._append_log(f"Selected file: {file_path.name}\n")

    def _clear_selection(self) -> None:
        if self.is_processing:
            return
        self.selected_file = None
        self.file_icon.configure(text="📄")
        self.file_name_label.configure(text="No file selected")
        self.file_details_label.configure(text="Choose one file to begin")
        self.drop_title.configure(text="Drag and drop your file here")
        self.drop_subtitle.configure(text="or choose it from your computer")
        self.import_button.configure(state="disabled")
        self._set_status("Ready", TEXT_MUTED)

    def _start_import(self) -> None:
        if self.is_processing or self.selected_file is None:
            return

        file_path = self.selected_file
        self._set_busy(True, "Import in progress…")
        self._append_log(f"Processing {file_path.name}…\n")

        threading.Thread(
            target=self._run_import,
            args=(file_path,),
            daemon=True,
        ).start()

    def _run_import(self, file_path: Path) -> None:
        try:
            # The processing functions may print AI prompts and technical details.
            # They are intentionally not redirected to the interface.
            if file_path.suffix.lower() == ".dwg":
                process_dwg_file(file_path)
            else:
                process_item_file(file_path)

            self.events.put(("success", file_path.name))
        except Exception as error:
            self.events.put(("error", error))

    def _start_database_test(self) -> None:
        if self.is_processing:
            return

        self.db_badge.configure(
            text="●  Connecting to database…",
            fg_color="#21262D",
        )
        threading.Thread(
            target=self._run_database_test,
            daemon=True,
        ).start()

    def _run_database_test(self) -> None:
        try:
            test_database_connection()
            self.events.put(("database_success", None))
        except Exception as error:
            self.events.put(("database_error", error))

    def _poll_events(self) -> None:
        try:
            while True:
                event_type, payload = self.events.get_nowait()
                if event_type == "log":
                    self._append_log(str(payload))
                elif event_type == "success":
                    self._set_busy(False, "Import completed successfully", SUCCESS)
                    self._append_log(f"✓ {payload} was imported successfully.\n")
                elif event_type == "error":
                    self._set_busy(False, "Import failed", DANGER)
                    self._append_log(f"✗ Import failed: {payload}\n")
                elif event_type == "database_success":
                    self.db_badge.configure(
                        text="●  Database connected",
                        fg_color="#238636",
                    )
                    self._set_busy(False, "Ready", TEXT_MUTED)
                    self._append_log("✓ Connected to the database.\n")
                elif event_type == "database_error":
                    self.db_badge.configure(
                        text="●  Database unavailable",
                        fg_color="#DA3633",
                    )
                    self._set_busy(False, "Database connection failed", DANGER)
                    self._append_log(f"✗ Database connection failed: {payload}\n")
        except queue.Empty:
            pass
        finally:
            self.after(100, self._poll_events)

    def _set_busy(self, busy: bool, status: str, color: str = ACCENT) -> None:
        self.is_processing = busy
        self._set_status(status, color)
        state = "disabled" if busy else ("normal" if self.selected_file else "disabled")
        self.import_button.configure(state=state)
        self.browse_button.configure(state="disabled" if busy else "normal")
        self.clear_button.configure(state="disabled" if busy else "normal")
        if busy:
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.set(1 if color == SUCCESS else 0)

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _append_log(self, text: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")


def main() -> None:
    app = BOQImporterApp()
    app.mainloop()


if __name__ == "__main__":
    main()