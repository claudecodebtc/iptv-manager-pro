import tkinter as tk
import threading
import sys
from datetime import datetime
from tkinter import ttk

import requests

from config import FONTS, THEME, THEME_PRESETS, VLC_PATH
from i18n import DEFAULT_LANG, tr
from m3u_utils import M3UHandler
from vlc_manager import VLCManager


class IPTVManagerApp:
    def __init__(self, root):
        self.root = root
        self.current_lang = DEFAULT_LANG
        self.root.title(self.t("app_title"))
        self.root.geometry("1040x760")
        self.root.minsize(920, 680)
        self.root.configure(bg=THEME["bg"])
        self.current_theme_name = next(
            (name for name, theme in THEME_PRESETS.items() if theme == THEME),
            "Ocean",
        )
        self.channel_search_var = tk.StringVar()
        self.status_var = tk.StringVar(value=tr(self.current_lang, "status_ready"))
        self._sort_state = {}
        self.compact_mode = False
        self.kiosk_mode = False
        self.log_lines = []
        self.preview_status_var = tk.StringVar(value=tr(self.current_lang, "select_url_first"))
        self.preview_type_var = tk.StringVar(value="-")
        self.preview_user_var = tk.StringVar(value="-")
        self._preview_url = ""
        self.edit_preview_status_var = tk.StringVar(value=tr(self.current_lang, "select_url_first"))
        self.edit_preview_name_var = tk.StringVar(value="-")
        self._edit_preview_url = ""
        self.visible_channel_items = []
        self.channel_url_map = {}
        self.debug_probe = False
        self.vlc_py = None
        self.embedded_vlc_instance = None
        self.embedded_player = None
        self.embedded_player_ready = False
        self.embedded_playing_url = ""
        self.embedded_paused = False
        self.video_controls_popup = None
        self.video_controls_owner = None
        self.video_controls_pinned = False
        self._controls_keepalive_job = None
        self.fullscreen_video_window = None
        self.fullscreen_video_frame = None
        self.fullscreen_controls_bar = None
        self.fullscreen_vlc_instance = None
        self.fullscreen_player = None
        self.fullscreen_playing_url = ""
        self.fullscreen_resume_url = ""
        self.fullscreen_paused = False

        self.vlc = VLCManager(VLC_PATH)
        self.m3u = M3UHandler(self)
        self._init_embedded_vlc()

        self.setup_styles()
        self.setup_ui()
        self.bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def t(self, key, **kwargs):
        return tr(self.current_lang, key, **kwargs)

    def _init_embedded_vlc(self):
        try:
            import vlc as vlc_module

            self.vlc_py = vlc_module
        except Exception as e:
            self.vlc_py = None
            self._dbg(f"python-vlc unavailable: {e}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("alt")
        if self.kiosk_mode:
            ui_size = 13
            title_size = 18
            tab_size = 14
            row_height = 34
            btn_padding = (16, 12)
        elif self.compact_mode:
            ui_size = 9
            title_size = 12
            tab_size = 10
            row_height = 22
            btn_padding = (10, 6)
        else:
            ui_size = 10
            title_size = 13
            tab_size = 11
            row_height = 26
            btn_padding = (12, 8)

        style.configure("TFrame", background=THEME["bg"])
        style.configure("Card.TFrame", background=THEME["tab_bg"], relief="flat", borderwidth=0)

        style.configure(
            "Title.TLabel",
            font=(FONTS["title"], title_size),
            foreground=THEME["fg"],
            background=THEME["bg"],
        )
        style.configure(
            "TLabel",
            font=(FONTS["ui"], ui_size),
            foreground=THEME["fg"],
            background=THEME["bg"],
        )
        style.configure(
            "Muted.TLabel",
            font=(FONTS["ui"], ui_size),
            foreground=THEME["muted_fg"],
            background=THEME["bg"],
        )

        style.configure(
            "TButton",
            font=(FONTS["title"], ui_size),
            padding=btn_padding,
            background=THEME["btn_bg"],
            foreground=THEME["fg"],
            borderwidth=0,
        )
        style.map(
            "TButton",
            background=[("active", THEME["btn_active"])],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )

        style.configure("Primary.TButton", background=THEME["btn_active"], foreground=THEME["fg"])
        style.map("Primary.TButton", background=[("active", THEME["title_bg"])])

        style.configure(
            "TEntry",
            fieldbackground=THEME["tree_bg"],
            foreground=THEME["fg"],
            insertcolor=THEME["fg"],
            borderwidth=1,
        )

        style.configure(
            "TCombobox",
            font=(FONTS["ui"], ui_size),
            fieldbackground=THEME["tree_bg"],
            background=THEME["tree_bg"],
            foreground=THEME["fg"],
            arrowcolor=THEME["fg"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", THEME["tree_bg"])],
            selectbackground=[("readonly", THEME["btn_active"])],
            selectforeground=[("readonly", THEME["fg"])],
        )

        style.configure("TNotebook", background=THEME["bg"], tabmargins=[6, 8, 6, 0], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            font=(FONTS["title"], tab_size),
            padding=[10, 6] if self.compact_mode else [14, 8],
            background=THEME["btn_bg"],
            foreground=THEME["fg"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["btn_active"])],
            expand=[("selected", [1, 1, 1, 0])],
        )

        style.configure(
            "Treeview",
            font=(FONTS["ui"], ui_size),
            background=THEME["tree_bg"],
            foreground=THEME["fg"],
            fieldbackground=THEME["tree_bg"],
            rowheight=row_height,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            font=(FONTS["title"], ui_size),
            background=THEME["btn_bg"],
            foreground=THEME["fg"],
            relief="flat",
        )
        style.map("Treeview", background=[("selected", THEME["btn_active"])])

    def setup_ui(self):
        self.root.title(self.t("app_title"))
        top_pad = 8 if self.compact_mode else (12 if self.kiosk_mode else 14)
        frame_pad_x = 10 if self.compact_mode else (20 if self.kiosk_mode else 18)
        notebook_pad = 8 if self.compact_mode else (20 if self.kiosk_mode else 16)
        title_size = 16 if self.compact_mode else (28 if self.kiosk_mode else 22)
        subtitle_size = 8 if self.compact_mode else (12 if self.kiosk_mode else 10)
        title_frame = tk.Frame(self.root, bg=THEME["title_bg"], padx=frame_pad_x, pady=top_pad)
        title_frame.pack(fill="x")
        accent_line = tk.Frame(title_frame, bg="#8ed5c6", height=2)
        accent_line.pack(fill="x", pady=(0, 8 if self.compact_mode else 10))
        header_row = tk.Frame(title_frame, bg=THEME["title_bg"])
        header_row.pack(fill="x")

        tk.Label(
            header_row,
            text=self.t("app_title"),
            font=(FONTS["title"], title_size),
            fg=THEME["fg"],
            bg=THEME["title_bg"],
        ).pack(side=tk.LEFT)

        theme_wrap = tk.Frame(header_row, bg=THEME["title_bg"])
        theme_wrap.pack(side=tk.RIGHT)
        tk.Label(
            theme_wrap,
            text=self.t("theme"),
            font=(FONTS["ui"], 10),
            fg="#d2ece5",
            bg=THEME["title_bg"],
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.theme_var = tk.StringVar(value=self.current_theme_name)
        self.theme_picker = ttk.Combobox(
            theme_wrap,
            textvariable=self.theme_var,
            state="readonly",
            width=12,
            values=list(THEME_PRESETS.keys()),
        )
        self.theme_picker.pack(side=tk.LEFT)
        self.theme_picker.bind("<<ComboboxSelected>>", self.apply_theme)
        tk.Label(
            theme_wrap,
            text=self.t("language"),
            font=(FONTS["ui"], 10),
            fg="#d2ece5",
            bg=THEME["title_bg"],
        ).pack(side=tk.LEFT, padx=(8, 8))
        self.lang_var = tk.StringVar(value=self.current_lang.upper())
        self.lang_picker = ttk.Combobox(
            theme_wrap,
            textvariable=self.lang_var,
            state="readonly",
            width=5,
            values=["EN", "RO", "DE", "ES"],
        )
        self.lang_picker.pack(side=tk.LEFT)
        self.lang_picker.bind("<<ComboboxSelected>>", self.apply_language)

        compact_label = self.t("compact_on") if self.compact_mode else self.t("compact_off")
        compact_btn = ttk.Button(theme_wrap, text=compact_label, command=self.toggle_compact_mode)
        compact_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.add_tooltip(compact_btn, "Activeaza/dezactiveaza layout compact pentru ecrane mici.")
        kiosk_label = self.t("fullscreen_on") if self.kiosk_mode else self.t("fullscreen_off")
        kiosk_btn = ttk.Button(theme_wrap, text=kiosk_label, command=self.toggle_kiosk_mode)
        kiosk_btn.pack(side=tk.LEFT, padx=(8, 0))
        self.add_tooltip(kiosk_btn, "Mod full-screen cu butoane mari pentru TV.")

        tk.Label(
            title_frame,
            text=self.t("app_subtitle"),
            font=(FONTS["ui"], subtitle_size),
            fg="#d2ece5",
            bg=THEME["title_bg"],
        ).pack(anchor="w", pady=(3 if self.compact_mode else 4, 0))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=notebook_pad, pady=notebook_pad)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.setup_download_tab()
        self.setup_edit_tab()
        self.setup_url_tab()
        self.setup_conflicts_tab()
        self.setup_log_panel()
        self.setup_status_bar()

    def setup_log_panel(self):
        panel_pad = 8 if self.compact_mode else 12
        panel = ttk.Frame(self.root, style="Card.TFrame", padding=panel_pad)
        panel.pack(fill="x", padx=10 if self.compact_mode else 16, pady=(0, 8))

        head = ttk.Frame(panel)
        head.pack(fill="x", pady=(0, 6))
        ttk.Label(head, text=self.t("log_activity"), style="Title.TLabel").pack(side=tk.LEFT)
        clear_btn = ttk.Button(head, text=self.t("clear_log"), command=self.clear_log)
        clear_btn.pack(side=tk.RIGHT)
        self.add_tooltip(clear_btn, "Goleste mesajele din panoul de log.")

        log_height = 4 if self.compact_mode else 6
        self.log_text = tk.Text(
            panel,
            height=log_height,
            wrap="word",
            bg=THEME["tree_bg"],
            fg=THEME["fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(FONTS["mono"], 9 if self.compact_mode else 10),
        )
        self.log_text.pack(fill="x")
        self.log_text.config(state="disabled")
        for line in self.log_lines:
            self._append_log_line(line)

    def setup_status_bar(self):
        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            font=(FONTS["ui"], 9),
            bg=THEME["tab_bg"],
            fg=THEME["muted_fg"],
            padx=10,
            pady=6,
        )
        status.pack(fill="x", side="bottom")

    def setup_download_tab(self):
        tab_pad = 12 if self.compact_mode else 18
        frame = ttk.Frame(self.notebook, padding=tab_pad)
        frame.columnconfigure(0, weight=1)
        self.notebook.add(frame, text=self.t("tab_download"))

        card = ttk.Frame(frame, style="Card.TFrame", padding=12 if self.compact_mode else 18)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Label(card, text=self.t("download_title"), style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        entries = [
            (
                "url_full",
                self.t("url_full"),
                "https://example.com/get.php?username=demo_user&password=demo_password&type=m3u_plus&output=ts",
            ),
            ("url_server", self.t("url_server"), "https://example.com"),
            ("username", self.t("username"), ""),
            ("password", self.t("password"), "", True),
        ]
        self.download_entries = {}
        for i, (field_key, label, default, *args) in enumerate(entries, start=1):
            ttk.Label(card, text=label).grid(row=i, column=0, sticky="w", pady=8, padx=(0, 8))
            entry = ttk.Entry(card, show="*" if args else "")
            entry.grid(row=i, column=1, sticky="ew", pady=8)
            entry.insert(0, default)
            self.download_entries[field_key] = entry

        download_btn = ttk.Button(
            card,
            text=self.t("download_list"),
            style="Primary.TButton",
            command=lambda: self.m3u.download_iptv(self.download_entries),
        )
        download_btn.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 4))
        self.add_tooltip(download_btn, "Descarca lista M3U folosind URL-ul complet.")

    def setup_edit_tab(self):
        tab_pad = 12 if self.compact_mode else 18
        frame = ttk.Frame(self.notebook, padding=tab_pad)
        frame.columnconfigure(0, weight=1)
        self.notebook.add(frame, text=self.t("tab_edit"))

        top_card = ttk.Frame(frame, style="Card.TFrame", padding=12 if self.compact_mode else 16)
        top_card.grid(row=0, column=0, sticky="ew")
        top_card.columnconfigure(1, weight=1)

        ttk.Label(top_card, text=self.t("edit_title"), style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        self.file_label = ttk.Label(top_card, text=self.t("no_file_loaded"))
        self.file_label.grid(row=1, column=0, columnspan=2, sticky="w")

        load_m3u_btn = ttk.Button(top_card, text=self.t("load_m3u"), command=self.m3u.load_file)
        load_m3u_btn.grid(row=1, column=2, sticky="e")
        self.add_tooltip(load_m3u_btn, "Deschide un fisier M3U local pentru editare.")

        pin_frame = ttk.Frame(top_card)
        pin_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Label(pin_frame, text=self.t("pin")).pack(side=tk.LEFT, padx=(0, 6))
        self.pin_entry = ttk.Entry(pin_frame, width=10)
        self.pin_entry.insert(0, "1234")
        self.pin_entry.pack(side=tk.LEFT)

        sel_card = ttk.Frame(frame, style="Card.TFrame", padding=12 if self.compact_mode else 16)
        sel_card.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        sel_card.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        sel_frame = ttk.Frame(sel_card)
        sel_frame.pack(fill="both", expand=True)

        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(sel_frame, textvariable=self.group_var, state="readonly", width=34)
        self.group_dropdown.bind("<<ComboboxSelected>>", lambda event: self.m3u.update_channels(self.group_var.get()))
        self.group_dropdown.pack(anchor="w", padx=4, pady=(0, 10))

        search_row = ttk.Frame(sel_frame)
        search_row.pack(fill="x", padx=4, pady=(0, 10))
        ttk.Label(search_row, text=self.t("search_channel")).pack(side=tk.LEFT, padx=(0, 8))
        self.channel_search_entry = ttk.Entry(search_row, textvariable=self.channel_search_var)
        self.channel_search_entry.pack(side=tk.LEFT, fill="x", expand=True)
        self.channel_search_entry.bind("<KeyRelease>", self.on_search_channels)

        body_frame = ttk.Frame(sel_frame)
        body_frame.pack(fill="both", expand=True)

        list_frame = ttk.Frame(body_frame)
        list_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(4, 8))
        self.channel_listbox = tk.Listbox(
            list_frame,
            height=14,
            font=(FONTS["ui"], 10),
            bg=THEME["tree_bg"],
            fg=THEME["fg"],
            selectbackground=THEME["btn_active"],
            exportselection=False,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.channel_listbox.pack(side=tk.LEFT, fill="both", expand=True)
        self.channel_listbox.bind("<<ListboxSelect>>", self.on_edit_channel_select)
        channel_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.channel_listbox.yview)
        channel_scroll.pack(side=tk.RIGHT, fill="y")
        self.channel_listbox.config(yscrollcommand=channel_scroll.set)

        edit_preview_card = ttk.Frame(body_frame, style="Card.TFrame", padding=10 if self.compact_mode else 12)
        edit_preview_card.pack(side=tk.LEFT, fill="both", expand=True, padx=(8, 8))
        edit_preview_card.columnconfigure(0, weight=1)
        edit_preview_card.columnconfigure(1, weight=1)
        edit_preview_card.columnconfigure(2, weight=1)

        btn_frame = ttk.Frame(body_frame)
        btn_frame.pack(side=tk.RIGHT, fill="y")
        delete_btn = ttk.Button(btn_frame, text=self.t("delete"), command=self.m3u.remove_selected)
        delete_btn.pack(fill="x", pady=4)
        pin_btn = ttk.Button(btn_frame, text=self.t("add_pin"), command=self.m3u.pin_selected)
        pin_btn.pack(fill="x", pady=4)
        pin_group_btn = ttk.Button(btn_frame, text=self.t("pin_group"), command=self.m3u.pin_group)
        pin_group_btn.pack(fill="x", pady=4)
        undo_btn = ttk.Button(btn_frame, text=self.t("undo"), command=self.m3u.undo_last_action)
        undo_btn.pack(fill="x", pady=4)
        save_btn = ttk.Button(btn_frame, text=self.t("save"), style="Primary.TButton", command=self.m3u.save_file)
        save_btn.pack(
            fill="x", pady=(14, 0)
        )
        self.add_tooltip(delete_btn, "Sterge canalele selectate sau tot grupul daca nu ai selectie.")
        self.add_tooltip(pin_btn, "Aplica PIN doar pe canalele selectate.")
        self.add_tooltip(pin_group_btn, "Aplica PIN pe toate canalele ramase din grup.")
        self.add_tooltip(undo_btn, "Revine la ultima actiune de stergere/pinare.")
        self.add_tooltip(save_btn, "Salveaza modificarile intr-un nou fisier M3U.")

        ttk.Label(edit_preview_card, text=self.t("mini_player_edit"), style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        ttk.Label(edit_preview_card, text=self.t("channel")).grid(row=1, column=0, sticky="w")
        ttk.Label(edit_preview_card, textvariable=self.edit_preview_name_var).grid(row=1, column=1, sticky="w")

        self.edit_preview_url_text = tk.Text(
            edit_preview_card,
            height=2 if self.compact_mode else 3,
            wrap="word",
            bg=THEME["tree_bg"],
            fg=THEME["fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(FONTS["mono"], 8 if self.compact_mode else 9),
        )
        self.edit_preview_url_text.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        self.edit_preview_url_text.config(state="disabled")

        probe_edit_btn = ttk.Button(edit_preview_card, text=self.t("probe_channel"), command=self.run_edit_preview_probe)
        probe_edit_btn.grid(row=3, column=0, sticky="w")
        self.add_tooltip(probe_edit_btn, "Testeaza URL-ul canalului selectat.")
        ttk.Label(edit_preview_card, style="Muted.TLabel", textvariable=self.edit_preview_status_var).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        self.edit_video_frame = tk.Frame(
            edit_preview_card,
            bg="#000000",
            height=220 if self.compact_mode else 300,
            highlightthickness=1,
            highlightbackground=THEME["btn_bg"],
        )
        self.edit_video_frame.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        edit_preview_card.rowconfigure(5, weight=1)
        self.edit_video_frame.grid_propagate(False)

        self._build_video_controls_popup()
        self._hide_controls_job = None

        self._bind_video_surface_events(self.edit_video_frame)

        self.root.after(100, self._ensure_embedded_player_ready)

        ttk.Label(sel_card, style="Muted.TLabel", text=self.t("edit_hint")).pack(
            anchor="w", pady=(10, 0)
        )

    def setup_url_tab(self):
        tab_pad = 12 if self.compact_mode else 18
        frame = ttk.Frame(self.notebook, padding=tab_pad)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        self.notebook.add(frame, text=self.t("tab_url"))

        top_card = ttk.Frame(frame, style="Card.TFrame", padding=10 if self.compact_mode else 14)
        top_card.grid(row=0, column=0, sticky="ew")
        top_card.columnconfigure(1, weight=1)

        self.url_label = ttk.Label(top_card, text=self.t("no_text_file_loaded"))
        self.url_label.grid(row=0, column=0, sticky="w")
        load_txt_btn = ttk.Button(top_card, text=self.t("load_text"), command=self.m3u.load_text_file)
        load_txt_btn.grid(row=0, column=1, sticky="e")
        self.add_tooltip(load_txt_btn, "Incarca un TXT cu URL-uri M3U/stream.")

        table_card = ttk.Frame(frame, style="Card.TFrame", padding=10 if self.compact_mode else 14)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(0, weight=1)

        self.url_tree = ttk.Treeview(table_card, columns=("Tip", "URL", "Username"), show="headings")
        self.url_tree.heading("Tip", text=self.t("type"), command=lambda: self.sort_treeview("Tip"))
        self.url_tree.heading("URL", text="URL", command=lambda: self.sort_treeview("URL"))
        self.url_tree.heading("Username", text=self.t("username"), command=lambda: self.sort_treeview("Username"))
        self.url_tree.column("Tip", width=120, anchor="center")
        self.url_tree.column("URL", width=560, anchor="w")
        self.url_tree.column("Username", width=220, anchor="w")
        self.url_tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.url_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.url_tree.config(yscrollcommand=tree_scroll.set)
        self.url_tree.bind("<Double-1>", self.vlc.play_in_vlc)
        self.url_tree.bind("<<TreeviewSelect>>", self.on_url_select)

        btn_frame = ttk.Frame(table_card)
        btn_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for idx in range(4):
            btn_frame.columnconfigure(idx, weight=1)

        save_urls_btn = ttk.Button(btn_frame, text=self.t("save_m3u_lists"), command=self.m3u.save_urls_as_m3u)
        save_urls_btn.grid(
            row=0, column=0, sticky="ew", padx=4
        )
        play_direct_btn = ttk.Button(
            btn_frame, text=self.t("run_direct_stream"), command=lambda: self.vlc.play_stream_direct(self.url_tree)
        )
        play_direct_btn.grid(
            row=0, column=1, sticky="ew", padx=4
        )
        choose_channel_btn = ttk.Button(btn_frame, text=self.t("choose_channel"), command=lambda: self.vlc.choose_channel(self.url_tree))
        choose_channel_btn.grid(
            row=0, column=2, sticky="ew", padx=4
        )
        load_group_btn = ttk.Button(btn_frame, text=self.t("load_group"), command=lambda: self.vlc.load_group(self.url_tree))
        load_group_btn.grid(
            row=0, column=3, sticky="ew", padx=4
        )
        self.add_tooltip(save_urls_btn, "Salveaza URL-urile M3U in fisiere locale.")
        self.add_tooltip(play_direct_btn, "Porneste imediat URL-ul selectat in VLC.")
        self.add_tooltip(choose_channel_btn, "Alege un canal din lista pentru redare.")
        self.add_tooltip(load_group_btn, "Incarca in VLC toate stream-urile din grup.")

        preview_card = ttk.Frame(frame, style="Card.TFrame", padding=10 if self.compact_mode else 14)
        preview_card.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        preview_card.columnconfigure(1, weight=1)

        ttk.Label(preview_card, text=self.t("mini_preview_url"), style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        ttk.Label(preview_card, text=self.t("type")).grid(row=1, column=0, sticky="w")
        ttk.Label(preview_card, textvariable=self.preview_type_var).grid(row=1, column=1, sticky="w")
        ttk.Label(preview_card, text=self.t("user")).grid(row=2, column=0, sticky="w")
        ttk.Label(preview_card, textvariable=self.preview_user_var).grid(row=2, column=1, sticky="w")

        self.preview_url_text = tk.Text(
            preview_card,
            height=2 if self.compact_mode else 3,
            wrap="word",
            bg=THEME["tree_bg"],
            fg=THEME["fg"],
            insertbackground=THEME["fg"],
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=(FONTS["mono"], 8 if self.compact_mode else 9),
        )
        self.preview_url_text.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        self.preview_url_text.config(state="disabled")

        probe_btn = ttk.Button(preview_card, text=self.t("probe_url"), command=self.run_preview_probe)
        probe_btn.grid(row=4, column=0, sticky="w")
        self.add_tooltip(probe_btn, "Testeaza rapid URL-ul selectat (status, content-type).")
        ttk.Label(preview_card, style="Muted.TLabel", textvariable=self.preview_status_var).grid(
            row=4, column=1, columnspan=2, sticky="w", padx=(8, 0)
        )

    def setup_conflicts_tab(self):
        tab_pad = 12 if self.compact_mode else 18
        frame = ttk.Frame(self.notebook, padding=tab_pad)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.notebook.add(frame, text=self.t("tab_conflicts"))

        card = ttk.Frame(frame, style="Card.TFrame", padding=12 if self.compact_mode else 16)
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        head = ttk.Frame(card)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        head.columnconfigure(0, weight=1)
        ttk.Label(head, text=self.t("conflicts_title"), style="Title.TLabel").grid(row=0, column=0, sticky="w")
        jump_btn = ttk.Button(head, text=self.t("jump_group"), command=self.jump_to_conflict_group)
        jump_btn.grid(row=0, column=1, sticky="e")
        self.add_tooltip(jump_btn, "Te muta in tab-ul Editare pe primul grup din conflict.")

        self.conflict_tree = ttk.Treeview(card, columns=("Canal", "Nr Grupuri", "Grupuri"), show="headings")
        self.conflict_tree.heading("Canal", text=self.t("channel"))
        self.conflict_tree.heading("Nr Grupuri", text=self.t("group_count"))
        self.conflict_tree.heading("Grupuri", text=self.t("groups"))
        self.conflict_tree.column("Canal", width=260, anchor="w")
        self.conflict_tree.column("Nr Grupuri", width=110, anchor="center")
        self.conflict_tree.column("Grupuri", width=620, anchor="w")
        self.conflict_tree.grid(row=1, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(card, orient="vertical", command=self.conflict_tree.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.conflict_tree.config(yscrollcommand=scroll.set)

        self.conflict_summary_var = tk.StringVar(value=self.t("no_analysis"))
        ttk.Label(card, style="Muted.TLabel", textvariable=self.conflict_summary_var).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )

    def bind_shortcuts(self):
        self.root.bind_all("<Control-o>", lambda event: self.m3u.load_file())
        self.root.bind_all("<Control-s>", lambda event: self.m3u.save_file())
        self.root.bind_all("<Control-z>", lambda event: self.m3u.undo_last_action())
        self.root.bind_all("<Delete>", lambda event: self.m3u.remove_selected())
        self.root.bind_all("<Control-f>", self.focus_search)
        self.root.bind_all("<Alt-Return>", self.toggle_video_fullscreen)
        self.root.bind_all("<F11>", lambda event: self.toggle_kiosk_mode())
        self.root.bind_all("<Escape>", self.handle_escape)

    def focus_search(self, event=None):
        if hasattr(self, "channel_search_entry"):
            self.notebook.select(1)
            self.channel_search_entry.focus_set()
            self.channel_search_entry.select_range(0, tk.END)

    def on_search_channels(self, event=None):
        group = self.group_var.get().strip()
        if group:
            self.refresh_channel_list(group)

    def refresh_channel_list(self, group):
        if not group or group not in self.m3u.groups or group in self.m3u.remove_groups:
            self.channel_listbox.delete(0, "end")
            self.visible_channel_items = []
            self.channel_url_map = {}
            self._dbg(f"refresh_channel_list invalid group='{group}'")
            return

        query = self.channel_search_var.get().strip().lower()
        removed = set(self.m3u.remove_channels.get(group, []))
        pinned = set(self.m3u.pin_channels.get(group, []))

        self.channel_listbox.delete(0, "end")
        self.visible_channel_items = []
        self.channel_url_map = {}
        for name, url, _ in self.m3u.groups[group]:
            if name in removed:
                continue
            if query and query not in name.lower():
                continue
            self.channel_listbox.insert("end", name)
            self.visible_channel_items.append((name, url))
            if name not in self.channel_url_map:
                self.channel_url_map[name] = url
            if name in pinned:
                self.channel_listbox.itemconfig("end", {"fg": "#00ff99"})

        self.group_var.set(group)
        self._dbg(
            f"refresh_channel_list group='{group}' visible={len(self.visible_channel_items)} "
            f"query='{query}' curselection={self.channel_listbox.curselection()}"
        )
        self.edit_preview_name_var.set("-")
        self._edit_preview_url = ""
        self.edit_preview_status_var.set(self.t("select_url_first"))
        self.edit_preview_url_text.config(state="normal")
        self.edit_preview_url_text.delete("1.0", "end")
        self.edit_preview_url_text.config(state="disabled")

    def on_edit_channel_select(self, event=None):
        selected_data = self._get_selected_edit_channel_data()
        if not selected_data:
            self._dbg("on_edit_channel_select no selected data")
            return
        name, url = selected_data
        self.edit_preview_name_var.set(name)
        self._edit_preview_url = url
        self.edit_preview_status_var.set(self.t("url_selected_probe"))
        self._set_edit_preview_url_text(url)
        self._dbg(f"on_edit_channel_select name='{name}' url='{url[:80]}'")

    def _get_selected_edit_channel_data(self):
        selected = self.channel_listbox.curselection()
        idx = selected[0] if selected else None

        if idx is None:
            try:
                active_idx = int(self.channel_listbox.index("active"))
                if active_idx >= 0:
                    idx = active_idx
            except Exception:
                idx = None
        if idx is None:
            self._dbg("_get_selected_edit_channel_data: no idx")
            return None

        if 0 <= idx < len(self.visible_channel_items):
            self._dbg(f"_get_selected_edit_channel_data: from visible idx={idx}")
            return self.visible_channel_items[idx]

        group = self.group_var.get().strip()
        if not group or group not in self.m3u.groups:
            return None
        try:
            name = self.channel_listbox.get(idx)
        except Exception:
            self._dbg(f"_get_selected_edit_channel_data: invalid idx={idx}")
            return None
        for ch_name, ch_url, _ in self.m3u.groups[group]:
            if ch_name == name:
                self._dbg(f"_get_selected_edit_channel_data: map by name='{name}'")
                return ch_name, ch_url
        self._dbg(f"_get_selected_edit_channel_data: no map for name='{name}'")
        return None

    def run_edit_preview_probe(self):
        resolved = self._sync_edit_preview_url_from_ui() or self._resolve_edit_preview_url()
        self._dbg(
            "run_edit_preview_probe "
            f"resolved='{(resolved or '')[:100]}' "
            f"curselection={self.channel_listbox.curselection()} "
            f"active={self.channel_listbox.index('active')} "
            f"anchor={self.channel_listbox.index('anchor')} "
            f"preview_name='{self.edit_preview_name_var.get()}'"
        )
        if not resolved:
            diag = self._edit_probe_diag()
            self.edit_preview_status_var.set(self.t("select_url_first"))
            self.set_status("Mini preview editare: fara selectie")
            self.log(f"Probe editare ignorat: fara canal selectat | {diag}", level="WARN")
            self._dbg(f"run_edit_preview_probe FAIL | {diag}")
            return
        self._edit_preview_url = resolved

        if not self._edit_preview_url.lower().startswith(("http://", "https://")):
            self._set_edit_preview_status("URL invalid pentru probe (doar http/https)", "WARN")
            return

        self.edit_preview_status_var.set("Probe in progress...")
        threading.Thread(target=self._edit_probe_worker, args=(self._edit_preview_url,), daemon=True).start()

    def _resolve_edit_preview_url(self):
        if self._edit_preview_url:
            self._dbg("_resolve_edit_preview_url: using stored url")
            return self._edit_preview_url.strip()

        selected_data = self._get_selected_edit_channel_data()
        if selected_data:
            name, url = selected_data
            self.edit_preview_name_var.set(name)
            self._set_edit_preview_url_text(url)
            self._dbg("_resolve_edit_preview_url: using selected_data")
            return url.strip()

        group = self.group_var.get().strip()
        channel_name = self.edit_preview_name_var.get().strip()
        if group and channel_name and channel_name != "-" and group in self.m3u.groups:
            removed = set(self.m3u.remove_channels.get(group, []))
            for ch_name, ch_url, _ in self.m3u.groups[group]:
                if ch_name == channel_name and ch_name not in removed:
                    self._set_edit_preview_url_text(ch_url)
                    self._dbg("_resolve_edit_preview_url: using preview label + group")
                    return ch_url.strip()

        preview_url = self.edit_preview_url_text.get("1.0", "end").strip()
        if preview_url:
            self._dbg("_resolve_edit_preview_url: using preview text")
            return preview_url
        self._dbg("_resolve_edit_preview_url: empty")
        return ""

    def _sync_edit_preview_url_from_ui(self):
        # 1) try explicit selected indices
        for idx in self.channel_listbox.curselection():
            try:
                name = self.channel_listbox.get(idx)
            except Exception:
                continue
            url = self.channel_url_map.get(name)
            if url:
                self.edit_preview_name_var.set(name)
                self._set_edit_preview_url_text(url)
                self._edit_preview_url = url
                self._dbg(f"_sync_edit_preview_url_from_ui: curselection idx={idx}")
                return url

        # 2) try anchor/active element even if selection is lost by focus
        for marker in ("anchor", "active"):
            try:
                idx = int(self.channel_listbox.index(marker))
                if idx >= 0:
                    name = self.channel_listbox.get(idx)
                    url = self.channel_url_map.get(name)
                    if url:
                        self.edit_preview_name_var.set(name)
                        self._set_edit_preview_url_text(url)
                        self._edit_preview_url = url
                        self._dbg(f"_sync_edit_preview_url_from_ui: marker={marker} idx={idx}")
                        return url
            except Exception:
                continue

        # 3) try name currently shown in mini-preview label
        name = self.edit_preview_name_var.get().strip()
        if name and name != "-":
            url = self.channel_url_map.get(name)
            if url:
                self._set_edit_preview_url_text(url)
                self._edit_preview_url = url
                self._dbg("_sync_edit_preview_url_from_ui: preview label")
                return url

        # 4) last fallback: URL text already visible in preview box
        preview_url = self.edit_preview_url_text.get("1.0", "end").strip()
        if preview_url:
            self._edit_preview_url = preview_url
            self._dbg("_sync_edit_preview_url_from_ui: preview text")
            return preview_url
        self._dbg("_sync_edit_preview_url_from_ui: empty")
        return ""

    def _set_edit_preview_url_text(self, url):
        self.edit_preview_url_text.config(state="normal")
        self.edit_preview_url_text.delete("1.0", "end")
        self.edit_preview_url_text.insert("1.0", url)
        self.edit_preview_url_text.config(state="disabled")

    def _edit_probe_diag(self):
        try:
            active = self.channel_listbox.index("active")
        except Exception:
            active = "err"
        try:
            anchor = self.channel_listbox.index("anchor")
        except Exception:
            anchor = "err"
        text_len = len(self.edit_preview_url_text.get("1.0", "end").strip()) if hasattr(self, "edit_preview_url_text") else 0
        return (
            f"sel={self.channel_listbox.curselection()} active={active} anchor={anchor} "
            f"preview_name='{self.edit_preview_name_var.get()}' stored_url_len={len(self._edit_preview_url or '')} "
            f"text_len={text_len} group='{self.group_var.get()}' items={self.channel_listbox.size()}"
        )

    def _probe_stream(self, raw_url):
        # IPTV links sometimes append custom headers after "|" which break direct HTTP probing.
        probe_url = (raw_url or "").strip().split("|", 1)[0].strip()
        if not probe_url:
            raise ValueError("URL gol")
        if not probe_url.lower().startswith(("http://", "https://")):
            raise ValueError("URL invalid pentru probe (doar http/https)")

        headers = {"User-Agent": "Mozilla/5.0", "Range": "bytes=0-512"}
        with requests.Session() as session:
            session.trust_env = False
            response = session.get(
                probe_url,
                headers=headers,
                timeout=6,
                verify=False,
                allow_redirects=True,
                stream=True,
            )
            try:
                code = response.status_code
                ctype = response.headers.get("Content-Type", "necunoscut")
                if code >= 400:
                    raise requests.HTTPError(response=response)
            finally:
                response.close()
        return code, ctype

    def _edit_probe_worker(self, url):
        try:
            code, ctype = self._probe_stream(url)
            self.root.after(0, lambda: self._set_edit_preview_status(f"OK ({code}) - {ctype}", "INFO"))
        except requests.HTTPError as e:
            code = getattr(getattr(e, "response", None), "status_code", "unknown")
            self.root.after(0, lambda code=code: self._set_edit_preview_status(f"HTTP error: {code}", "WARN"))
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda msg=msg: self._set_edit_preview_status(f"Eroare probe: {msg}", "ERROR"))

    def _set_edit_preview_status(self, text, level="INFO"):
        self.edit_preview_status_var.set(text)
        self.set_status(f"Mini preview editare: {text}")
        channel = self.edit_preview_name_var.get()
        self.log(f"Mini preview editare [{channel}] {text}", level=level)

    def _ensure_embedded_player_ready(self):
        if self.embedded_player_ready:
            return True
        if self.vlc_py is None:
            return False
        if not hasattr(self, "edit_video_frame"):
            return False
        try:
            self.embedded_vlc_instance = self.vlc_py.Instance(
                "--no-video-title-show",
                "--quiet",
                "--verbose=-1",
                "--network-caching=2000",
                "--live-caching=2000",
            )
            self.embedded_player = self.embedded_vlc_instance.media_player_new()
            self._bind_embedded_video_surface()
            self.embedded_player_ready = True
            self._dbg("embedded VLC ready")
            return True
        except Exception as e:
            self.embedded_player_ready = False
            self._set_edit_preview_status(f"Mini player indisponibil: {e}", "ERROR")
            return False

    def _bind_video_surface_events(self, widget):
        widget.bind("<Enter>", self._on_video_hover_enter)
        widget.bind("<Leave>", self._on_video_hover_leave)
        widget.bind("<Double-1>", self.toggle_video_fullscreen)

    def _get_active_video_widget(self):
        if self.fullscreen_video_frame is not None:
            try:
                if self.fullscreen_video_frame.winfo_exists():
                    return self.fullscreen_video_frame
            except Exception:
                pass
        if hasattr(self, "edit_video_frame") and self.edit_video_frame is not None:
            try:
                if self.edit_video_frame.winfo_exists():
                    return self.edit_video_frame
            except Exception:
                pass
        return None

    def _bind_player_surface(self, player, target):
        if player is None or target is None:
            return
        target.update_idletasks()
        win_id = target.winfo_id()
        if sys.platform.startswith("win"):
            player.set_hwnd(win_id)
        elif sys.platform.startswith("linux"):
            player.set_xwindow(win_id)
        elif sys.platform == "darwin":
            player.set_nsobject(win_id)

    def _bind_embedded_video_surface(self):
        if not hasattr(self, "edit_video_frame") or self.edit_video_frame is None:
            return
        self._bind_player_surface(self.embedded_player, self.edit_video_frame)

    def _bind_fullscreen_video_surface(self):
        if self.fullscreen_video_frame is None:
            return
        self._bind_player_surface(self.fullscreen_player, self.fullscreen_video_frame)

    def _build_vlc_media(self, instance, url):
        media = instance.media_new(url)
        media.add_option(":network-caching=2000")
        media.add_option(":live-caching=2000")
        media.add_option(":quiet")
        return media

    def _get_active_player(self):
        if self.fullscreen_video_window is not None and self.fullscreen_player is not None:
            return self.fullscreen_player
        return self.embedded_player

    def toggle_video_fullscreen(self, event=None):
        if self.fullscreen_video_window is not None:
            self._exit_video_fullscreen()
        else:
            self._enter_video_fullscreen()

    def _enter_video_fullscreen(self):
        if self.fullscreen_video_window is not None:
            return
        if self.vlc_py is None:
            self._set_edit_preview_status("Instaleaza python-vlc pentru video embedded", "WARN")
            return
        resolved = self._sync_edit_preview_url_from_ui() or self._resolve_edit_preview_url() or self.embedded_playing_url
        if not resolved:
            self._set_edit_preview_status(self.t("select_url_first"), "WARN")
            return

        win = tk.Toplevel(self.root)
        win.configure(bg="#000000")
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        win.bind("<Escape>", self._exit_video_fullscreen)
        win.bind("<Double-1>", self.toggle_video_fullscreen)
        win.protocol("WM_DELETE_WINDOW", self._exit_video_fullscreen)

        shell = tk.Frame(win, bg="#000000")
        shell.pack(fill="both", expand=True)

        frame = tk.Frame(shell, bg="#000000", highlightthickness=0, bd=0)
        frame.pack(fill="both", expand=True)
        self._bind_video_surface_events(frame)

        controls = tk.Frame(shell, bg="#111111", padx=10, pady=10)
        controls.pack(fill="x", side="bottom")
        ttk.Button(controls, text=self.t("back"), command=self.play_prev_channel).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text=self.t("play_video"), command=self.play_edit_embedded_video).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text=self.t("pause_resume"), command=self.toggle_pause_edit_video).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text=self.t("next"), command=self.play_next_channel).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text=self.t("stop"), command=self.stop_edit_video).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text=self.t("fullscreen_off"), command=self.toggle_video_fullscreen).pack(side=tk.RIGHT, padx=4)

        self.fullscreen_video_window = win
        self.fullscreen_video_frame = frame
        self.fullscreen_controls_bar = controls
        self.fullscreen_resume_url = self.embedded_playing_url or resolved
        self.video_controls_pinned = False
        self._hide_video_controls(force=True)

        try:
            win.focus_force()
        except Exception:
            pass

        if self.embedded_player is not None:
            try:
                self.embedded_player.stop()
            except Exception:
                pass
        self.embedded_playing_url = ""
        self.embedded_paused = False

        self.root.after(80, lambda url=resolved: self._play_fullscreen_video(url))
        self._set_edit_preview_status("Video fullscreen activ. Esc sau dublu-click pentru iesire.", "INFO")

    def _exit_video_fullscreen(self, event=None, resume_embedded=True):
        resume_url = self.fullscreen_playing_url or self.fullscreen_resume_url
        player = self.fullscreen_player
        instance = self.fullscreen_vlc_instance
        win = self.fullscreen_video_window
        self.fullscreen_video_window = None
        self.fullscreen_video_frame = None
        self.fullscreen_controls_bar = None
        self.fullscreen_player = None
        self.fullscreen_vlc_instance = None
        self.fullscreen_playing_url = ""
        self.fullscreen_paused = False
        self.fullscreen_resume_url = ""
        if player is not None:
            try:
                player.stop()
            except Exception:
                pass
            try:
                player.release()
            except Exception:
                pass
        if instance is not None:
            try:
                instance.release()
            except Exception:
                pass
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
        if resume_embedded and resume_url:
            self.root.after(100, lambda url=resume_url: self._restore_embedded_video_after_fullscreen(url))
        self._set_edit_preview_status("Video fullscreen inchis.", "INFO")

    def _restore_embedded_video_after_fullscreen(self, url):
        self.video_controls_pinned = True
        self.play_edit_embedded_video(url=url)
        self.root.after(320, self._ensure_embedded_controls_visible)

    def _ensure_embedded_controls_visible(self):
        if self.fullscreen_video_window is not None:
            return
        if not self.embedded_playing_url:
            return
        self.video_controls_pinned = True
        self._show_video_controls_popup()

    def _play_fullscreen_video(self, url):
        if self.fullscreen_video_window is None or self.fullscreen_video_frame is None:
            return
        try:
            if self.fullscreen_vlc_instance is None:
                self.fullscreen_vlc_instance = self.vlc_py.Instance(
                    "--no-video-title-show",
                    "--quiet",
                    "--verbose=-1",
                    "--network-caching=2000",
                    "--live-caching=2000",
                )
            if self.fullscreen_player is None:
                self.fullscreen_player = self.fullscreen_vlc_instance.media_player_new()
            self._bind_fullscreen_video_surface()
            media = self._build_vlc_media(self.fullscreen_vlc_instance, url)
            self.fullscreen_player.set_media(media)
            self.fullscreen_player.play()
            self.fullscreen_playing_url = url
            self.fullscreen_paused = False
            self.root.after(220, self._after_fullscreen_play_fix)
        except Exception as e:
            self._set_edit_preview_status(f"Eroare fullscreen video: {e}", "ERROR")
            return
        self.log(f"Fullscreen video play: {url[:100]}")

    def _after_fullscreen_play_fix(self):
        try:
            self._bind_fullscreen_video_surface()
            if self.fullscreen_player is not None:
                self.fullscreen_player.video_set_scale(0)
                self.fullscreen_player.video_set_aspect_ratio(None)
        except Exception:
            pass

    def play_edit_embedded_video(self, url=None):
        if self.vlc_py is None:
            self._set_edit_preview_status("Instaleaza python-vlc pentru video embedded", "WARN")
            return
        resolved = url or self._sync_edit_preview_url_from_ui() or self._resolve_edit_preview_url()
        if not resolved:
            self._set_edit_preview_status(self.t("select_url_first"), "WARN")
            return
        if not resolved.lower().startswith(("http://", "https://")):
            self._set_edit_preview_status("URL invalid pentru redare", "WARN")
            return
        if self.fullscreen_video_window is not None:
            self._play_fullscreen_video(resolved)
            return
        if not self._ensure_embedded_player_ready():
            return
        try:
            self._bind_embedded_video_surface()
            media = self._build_vlc_media(self.embedded_vlc_instance, resolved)
            self.embedded_player.set_media(media)
            self.embedded_player.play()
            self.root.after(220, self._after_play_video_fix)
            self.embedded_playing_url = resolved
            self.embedded_paused = False
            self.video_controls_pinned = True
            self._show_video_controls_popup()
            self._set_edit_preview_status(self.t("video_started"), "INFO")
            self.log(f"Embedded video play: {resolved[:100]}")
        except Exception as e:
            self._set_edit_preview_status(f"Eroare play embedded: {e}", "ERROR")

    def _after_play_video_fix(self):
        try:
            self._bind_embedded_video_surface()
            if self.embedded_player is not None:
                self.embedded_player.video_set_scale(0)
                self.embedded_player.video_set_aspect_ratio(None)
        except Exception:
            pass

    def on_tab_changed(self, event=None):
        current = self.notebook.tab(self.notebook.select(), "text")
        if current != self.t("tab_edit"):
            self.video_controls_pinned = False
            self._hide_video_controls(force=True)
        else:
            if self.video_controls_popup is None or not self.video_controls_popup.winfo_exists():
                self._build_video_controls_popup()
            if self.embedded_playing_url:
                self.video_controls_pinned = True
                self._show_video_controls_popup()

    def stop_edit_video(self):
        try:
            if self.fullscreen_video_window is not None:
                self._exit_video_fullscreen(resume_embedded=False)
            if self.embedded_player is not None:
                self.embedded_player.stop()
            self.embedded_playing_url = ""
            self.embedded_paused = False
            self.video_controls_pinned = False
            self._hide_video_controls(force=True)
            return True
        except Exception:
            return False

    def _on_video_hover_enter(self, event=None):
        if self.fullscreen_video_window is not None:
            return
        if self.video_controls_pinned and self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
            return
        if self._hide_controls_job is not None:
            self.root.after_cancel(self._hide_controls_job)
            self._hide_controls_job = None
        self._dbg("video hover enter -> show controls")
        self._show_video_controls_popup()

    def _on_video_hover_leave(self, event=None):
        if self.fullscreen_video_window is not None:
            return
        if self.video_controls_pinned or self.embedded_playing_url:
            self._dbg("video hover leave ignored while playing")
            return
        if self._hide_controls_job is not None:
            self.root.after_cancel(self._hide_controls_job)
        self._hide_controls_job = self.root.after(180, self._hide_video_controls)

    def _hide_video_controls(self, force=False):
        if self.fullscreen_video_window is not None:
            if self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
                self.video_controls_popup.withdraw()
            self._hide_controls_job = None
            return
        if self.video_controls_pinned and not force:
            self._hide_controls_job = None
            return
        if self.embedded_playing_url and not force:
            self._dbg("hide controls canceled while playing")
            self._hide_controls_job = None
            return
        if self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
            self.video_controls_popup.withdraw()
        if self._controls_keepalive_job is not None:
            self.root.after_cancel(self._controls_keepalive_job)
            self._controls_keepalive_job = None
        self._hide_controls_job = None

    def _build_video_controls_popup(self):
        if self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
            self.video_controls_popup.destroy()
        owner = self.fullscreen_video_window if self.fullscreen_video_window is not None else self.root
        popup = tk.Toplevel(owner)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        try:
            popup.transient(owner)
        except Exception:
            pass
        popup.configure(bg="#111111")

        wrap = tk.Frame(popup, bg="#111111", padx=6, pady=6)
        wrap.pack(fill="both", expand=True)
        ttk.Button(wrap, text=self.t("back"), command=self.play_prev_channel).pack(side=tk.LEFT, padx=3)
        ttk.Button(wrap, text=self.t("play_video"), command=self.play_edit_embedded_video).pack(side=tk.LEFT, padx=3)
        ttk.Button(wrap, text=self.t("video_fullscreen"), command=self.toggle_video_fullscreen).pack(side=tk.LEFT, padx=3)
        ttk.Button(wrap, text=self.t("pause_resume"), command=self.toggle_pause_edit_video).pack(side=tk.LEFT, padx=3)
        ttk.Button(wrap, text=self.t("next"), command=self.play_next_channel).pack(side=tk.LEFT, padx=3)
        ttk.Button(wrap, text=self.t("stop"), command=self.stop_edit_video).pack(side=tk.LEFT, padx=3)

        popup.bind("<Enter>", self._on_video_hover_enter)
        popup.bind("<Leave>", self._on_video_hover_leave)
        wrap.bind("<Enter>", self._on_video_hover_enter)
        wrap.bind("<Leave>", self._on_video_hover_leave)
        self.video_controls_popup = popup
        self.video_controls_owner = owner

    def _show_video_controls_popup(self):
        if self.fullscreen_video_window is not None:
            if self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
                self.video_controls_popup.withdraw()
            return
        desired_owner = self.fullscreen_video_window if self.fullscreen_video_window is not None else self.root
        if (
            self.video_controls_popup is None
            or not self.video_controls_popup.winfo_exists()
            or self.video_controls_owner is not desired_owner
        ):
            self._build_video_controls_popup()
        target = self._get_active_video_widget()
        if target is None:
            return
        self.video_controls_popup.update_idletasks()
        fw = target.winfo_width()
        fh = target.winfo_height()
        fx = target.winfo_rootx()
        fy = target.winfo_rooty()
        pw = self.video_controls_popup.winfo_reqwidth()
        ph = self.video_controls_popup.winfo_reqheight()
        x = fx + max(6, (fw - pw) // 2)
        y = fy + max(6, fh - ph - 8)
        self.video_controls_popup.geometry(f"+{x}+{y}")
        self.video_controls_popup.deiconify()
        try:
            self.video_controls_popup.lift(desired_owner)
        except Exception:
            self.video_controls_popup.lift()
        self._dbg(f"show controls popup x={x} y={y}")
        if self.video_controls_pinned:
            if self._controls_keepalive_job is not None:
                self.root.after_cancel(self._controls_keepalive_job)
                self._controls_keepalive_job = None
            return
        self._schedule_controls_keepalive()

    def _schedule_controls_keepalive(self):
        if self._controls_keepalive_job is not None:
            self.root.after_cancel(self._controls_keepalive_job)
        self._controls_keepalive_job = self.root.after(220, self._keep_controls_on_top)

    def _keep_controls_on_top(self):
        if self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
            try:
                if self.video_controls_popup.state() != "withdrawn":
                    if self.video_controls_owner is not None:
                        self.video_controls_popup.lift(self.video_controls_owner)
                    else:
                        self.video_controls_popup.lift()
                    self._controls_keepalive_job = self.root.after(220, self._keep_controls_on_top)
                    return
            except Exception:
                pass
        self._controls_keepalive_job = None

    def _destroy_video_controls_popup(self):
        if self._controls_keepalive_job is not None:
            self.root.after_cancel(self._controls_keepalive_job)
            self._controls_keepalive_job = None
        if self.video_controls_popup is not None and self.video_controls_popup.winfo_exists():
            self.video_controls_popup.destroy()
        self.video_controls_popup = None
        self.video_controls_owner = None
        self.video_controls_pinned = False

    def toggle_pause_edit_video(self):
        player = self._get_active_player()
        if player is None:
            self._set_edit_preview_status("Mini player inactiv", "WARN")
            return
        try:
            player.pause()
            if self.fullscreen_video_window is not None:
                self.fullscreen_paused = not self.fullscreen_paused
                paused = self.fullscreen_paused
            else:
                self.embedded_paused = not self.embedded_paused
                paused = self.embedded_paused
            state = "Pauza" if paused else "Resume"
            self._set_edit_preview_status(state, "INFO")
        except Exception as e:
            self._set_edit_preview_status(f"Eroare pause/resume: {e}", "ERROR")

    def _select_channel_index(self, idx):
        size = self.channel_listbox.size()
        if size <= 0:
            return False
        idx = idx % size
        self.channel_listbox.selection_clear(0, "end")
        self.channel_listbox.selection_set(idx)
        self.channel_listbox.activate(idx)
        self.channel_listbox.see(idx)
        self.on_edit_channel_select()
        return True

    def play_next_channel(self):
        size = self.channel_listbox.size()
        if size <= 0:
            self._set_edit_preview_status("Nu exista canale in lista", "WARN")
            return
        cur = self.channel_listbox.curselection()
        idx = cur[0] if cur else 0
        if self._select_channel_index(idx + 1):
            self.play_edit_embedded_video()

    def play_prev_channel(self):
        size = self.channel_listbox.size()
        if size <= 0:
            self._set_edit_preview_status("Nu exista canale in lista", "WARN")
            return
        cur = self.channel_listbox.curselection()
        idx = cur[0] if cur else 0
        if self._select_channel_index(idx - 1):
            self.play_edit_embedded_video()

    def on_close(self):
        self.stop_edit_video()
        self._destroy_video_controls_popup()
        self.root.destroy()

    def _populate_url_tree(self):
        self.url_tree.delete(*self.url_tree.get_children())
        m3u_urls = self.m3u.m3u_urls or []
        stream_urls = self.m3u.stream_urls or []
        if not m3u_urls and not stream_urls:
            return

        from url_manager import extract_username

        for url in m3u_urls:
            self.url_tree.insert("", "end", values=("M3U", url, extract_username(url)))
        for url in stream_urls:
            self.url_tree.insert("", "end", values=("Stream", url, extract_username(url)))
        self.set_status(self.t("url_loaded_status", m3u=len(m3u_urls), stream=len(stream_urls)))

    def sort_treeview(self, column_name):
        descending = self._sort_state.get(column_name, False)
        rows = []
        for item in self.url_tree.get_children(""):
            value = str(self.url_tree.set(item, column_name)).lower()
            rows.append((value, item))
        rows.sort(reverse=descending)
        for idx, (_, item_id) in enumerate(rows):
            self.url_tree.move(item_id, "", idx)
        self._sort_state[column_name] = not descending
        direction = self.t("desc") if descending else self.t("asc")
        self.set_status(self.t("sort_status", column=column_name, direction=direction))

    def set_status(self, text):
        self.status_var.set(text)

    def _dbg(self, text):
        if self.debug_probe:
            print(f"[DEBUG] {text}")

    def _append_log_line(self, line):
        if not hasattr(self, "log_text"):
            return
        self.log_text.config(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def log(self, text, level="INFO"):
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] [{level}] {text}"
        self.log_lines.append(line)
        if len(self.log_lines) > 400:
            self.log_lines = self.log_lines[-400:]
        self._append_log_line(line)

    def clear_log(self):
        self.log_lines = []
        if hasattr(self, "log_text"):
            self.log_text.config(state="normal")
            self.log_text.delete("1.0", "end")
            self.log_text.config(state="disabled")
        self.set_status(self.t("log_cleared"))

    def on_url_select(self, event=None):
        selected = self.url_tree.selection()
        if not selected:
            return
        item = self.url_tree.item(selected[0], "values")
        if len(item) < 3:
            return
        tip, url, username = item[0], item[1], item[2]
        self.preview_type_var.set(tip or "-")
        self.preview_user_var.set(username or "-")
        self._preview_url = url
        self.preview_status_var.set("URL selectat. Apasa Probeaza URL.")
        self.preview_url_text.config(state="normal")
        self.preview_url_text.delete("1.0", "end")
        self.preview_url_text.insert("1.0", url)
        self.preview_url_text.config(state="disabled")

    def run_preview_probe(self):
        if not self._preview_url:
            self.preview_status_var.set(self.t("select_url_first"))
            return
        self.preview_status_var.set("Probe in progress...")
        threading.Thread(target=self._preview_probe_worker, args=(self._preview_url,), daemon=True).start()

    def _preview_probe_worker(self, url):
        try:
            code, ctype = self._probe_stream(url)
            msg = f"OK ({code}) - {ctype}"
            self.root.after(0, lambda: self._set_preview_status(msg, "INFO"))
        except requests.HTTPError as e:
            code = getattr(getattr(e, "response", None), "status_code", "unknown")
            self.root.after(0, lambda code=code: self._set_preview_status(f"HTTP error: {code}", "WARN"))
        except Exception as e:
            msg = str(e)
            self.root.after(0, lambda msg=msg: self._set_preview_status(f"Eroare probe: {msg}", "ERROR"))

    def _set_preview_status(self, text, level="INFO"):
        self.preview_status_var.set(text)
        self.set_status(f"Mini preview: {text}")
        self.log(f"Mini preview {self._preview_url}: {text}", level=level)

    def refresh_conflicts_panel(self):
        if not hasattr(self, "conflict_tree"):
            return
        self.conflict_tree.delete(*self.conflict_tree.get_children())
        groups = getattr(self.m3u, "groups", {}) or {}
        if not groups:
            self.conflict_summary_var.set("Nu exista date M3U incarcate.")
            return

        removed_groups = set(getattr(self.m3u, "remove_groups", set()))
        removed_channels = getattr(self.m3u, "remove_channels", {})

        index = {}
        for group_name, channels in groups.items():
            if group_name in removed_groups:
                continue
            removed = set(removed_channels.get(group_name, []))
            for name, _, _ in channels:
                if name in removed:
                    continue
                key = name.strip().lower()
                if not key:
                    continue
                data = index.setdefault(key, {"name": name, "groups": []})
                if group_name not in data["groups"]:
                    data["groups"].append(group_name)

        conflicts = [v for v in index.values() if len(v["groups"]) > 1]
        conflicts.sort(key=lambda x: x["name"].lower())
        for conflict in conflicts:
            groups_text = " | ".join(conflict["groups"])
            self.conflict_tree.insert("", "end", values=(conflict["name"], len(conflict["groups"]), groups_text))

        count = len(conflicts)
        if count == 0:
            self.conflict_summary_var.set(self.t("no_conflicts"))
            self.set_status(self.t("status_conflicts_zero"))
        else:
            self.conflict_summary_var.set(self.t("conflicts_found", count=count))
            self.set_status(self.t("status_conflicts", count=count))

    def jump_to_conflict_group(self):
        selected = self.conflict_tree.selection()
        if not selected:
            self.set_status(self.t("select_conflict"))
            return
        values = self.conflict_tree.item(selected[0], "values")
        if len(values) < 3:
            return
        first_group = str(values[2]).split(" | ")[0].strip()
        if not first_group:
            return
        self.notebook.select(1)
        self.group_var.set(first_group)
        self.m3u.update_channels(first_group)
        self.set_status(self.t("jump_group_status", group=first_group))
        self.log(self.t("jump_group_status", group=first_group))

    def add_tooltip(self, widget, text):
        tooltip_state = {"window": None}

        def show_tooltip(event=None):
            if tooltip_state["window"] is not None:
                return
            window = tk.Toplevel(widget)
            window.wm_overrideredirect(True)
            window.attributes("-topmost", True)
            x = widget.winfo_rootx() + 14
            y = widget.winfo_rooty() + widget.winfo_height() + 8
            window.wm_geometry(f"+{x}+{y}")
            label = tk.Label(
                window,
                text=text,
                bg="#10151c",
                fg="#d9e4e1",
                font=(FONTS["ui"], 9),
                relief="solid",
                bd=1,
                padx=8,
                pady=4,
            )
            label.pack()
            tooltip_state["window"] = window

        def hide_tooltip(event=None):
            if tooltip_state["window"] is not None:
                tooltip_state["window"].destroy()
                tooltip_state["window"] = None

        widget.bind("<Enter>", show_tooltip, add="+")
        widget.bind("<Leave>", hide_tooltip, add="+")
        widget.bind("<ButtonPress>", hide_tooltip, add="+")

    def restore_view_from_model(self):
        if self.m3u.groups:
            self.group_dropdown["values"] = [g for g in self.m3u.groups.keys() if g not in self.m3u.remove_groups]
            group = self.group_var.get() or next(iter(self.m3u.groups.keys()))
            if group in self.m3u.remove_groups:
                values = self.group_dropdown["values"]
                group = values[0] if values else ""
            self.group_var.set(group)
            if group:
                self.refresh_channel_list(group)

        self._populate_url_tree()
        self.refresh_conflicts_panel()

    def apply_theme(self, event=None):
        theme_name = self.theme_var.get().strip()
        if theme_name not in THEME_PRESETS:
            return
        self.current_theme_name = theme_name

        THEME.clear()
        THEME.update(THEME_PRESETS[theme_name])
        self.root.configure(bg=THEME["bg"])

        # Rebuild keeps behavior untouched and re-applies colors everywhere.
        self._destroy_video_controls_popup()
        self.stop_edit_video()
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_styles()
        self.setup_ui()
        self.restore_view_from_model()
        self.set_status(self.t("active_theme", theme=theme_name))
        self.log(f"Tema schimbata: {theme_name}")

    def apply_language(self, event=None):
        lang = self.lang_var.get().strip().lower()
        if lang not in ("en", "ro", "de", "es"):
            return
        self.current_lang = lang
        self.root.title(self.t("app_title"))
        self._destroy_video_controls_popup()
        self.stop_edit_video()
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_styles()
        self.setup_ui()
        self.restore_view_from_model()
        self.set_status(self.t("active_language", language=lang.upper()))

    def toggle_compact_mode(self):
        if self.kiosk_mode:
            self.toggle_kiosk_mode()
        self.compact_mode = not self.compact_mode
        self.root.geometry("900x620" if self.compact_mode else "1040x760")
        if self.compact_mode:
            self.root.minsize(760, 560)
        else:
            self.root.minsize(920, 680)
        self._destroy_video_controls_popup()
        self.stop_edit_video()
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_styles()
        self.setup_ui()
        self.restore_view_from_model()
        mode = self.t("mode_on") if self.compact_mode else self.t("mode_off")
        self.set_status(self.t("compact_mode", mode=mode))
        self.log(self.t("compact_mode", mode=mode))

    def toggle_kiosk_mode(self):
        self.kiosk_mode = not self.kiosk_mode
        if self.kiosk_mode:
            self.compact_mode = False
            self.root.attributes("-fullscreen", True)
            self.root.minsize(900, 620)
        else:
            self.root.attributes("-fullscreen", False)
            self.root.geometry("1040x760")
            self.root.minsize(920, 680)
        self._destroy_video_controls_popup()
        self.stop_edit_video()
        for child in self.root.winfo_children():
            child.destroy()
        self.setup_styles()
        self.setup_ui()
        self.restore_view_from_model()
        mode = self.t("mode_on") if self.kiosk_mode else self.t("mode_off")
        self.set_status(self.t("fullscreen_mode", mode=mode))
        self.log(self.t("fullscreen_mode", mode=mode))

    def exit_kiosk_mode(self, event=None):
        if self.kiosk_mode:
            self.toggle_kiosk_mode()

    def handle_escape(self, event=None):
        if self.fullscreen_video_window is not None:
            self._exit_video_fullscreen()
            return "break"
        self.exit_kiosk_mode(event)


if __name__ == "__main__":
    root = tk.Tk()
    app = IPTVManagerApp(root)
    root.mainloop()
