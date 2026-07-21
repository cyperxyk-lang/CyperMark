"""
CyperMark — графический интерфейс (tkinter)
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from tkinter import (
    Tk, Toplevel, Frame, Label, Entry, Button, Text, Scrollbar, Canvas,
    Checkbutton, IntVar, StringVar, BooleanVar, NW, filedialog,
    messagebox, ttk, Scale, OptionMenu, DISABLED, NORMAL, END, LEFT,
    RIGHT, TOP, BOTTOM, X, Y, BOTH, W, E, N, S, HORIZONTAL, VERTICAL,
)
from tkinter.dnd import dnd_start
from typing import Optional
from tkinter.colorchooser import askcolor as tk_askcolor

from PIL import Image, ImageTk

from watermark_core import (
    WatermarkConfig, Position, SUPPORTED_FORMATS,
    batch_process, generate_preview,
    apply_text_watermark, apply_image_watermark
)


# ─── Цветовая схема ──────────────────────────────────────────
COLORS = {
    "bg_dark":       "#1a1a2e",
    "bg_medium":     "#16213e",
    "bg_light":      "#0f3460",
    "accent":        "#e94560",
    "accent_hover":  "#ff6b81",
    "text_primary":  "#ffffff",
    "text_secondary":"#a0a0b0",
    "success":       "#2ecc71",
    "warning":       "#f39c12",
    "error":         "#e74c3c",
    "border":        "#2a2a4a",
}

FONT_FAMILY = "Segoe UI"


class CyperMarkGUI:
    """Главное окно приложения CyperMark"""

    def __init__(self, master: Tk):
        self.master = master
        master.title("CyperMark — Пакетный водяной знак")
        master.geometry("1080x720")
        master.configure(bg=COLORS["bg_dark"])
        master.minsize(900, 600)

        # Иконка (если есть)
        try:
            master.iconbitmap("icons/cypermark.ico")
        except:
            pass

        # Переменные состояния
        self.input_files: list[str] = []
        self.input_dir: str = ""
        self.output_dir: str = ""
        self.preview_image: Optional[Image.Image] = None
        self.preview_tk: Optional[ImageTk.PhotoImage] = None
        self.is_running = False

        # Конфигурация
        self.config = WatermarkConfig()

        # --- Сборка интерфейса ---
        self._build_ui()

        # Статус
        self._update_status("Готов к работе. Добавьте изображения.")

    # ─── Сборка UI ────────────────────────────────────────────
    def _build_ui(self):
        """Собирает весь интерфейс."""
        # Основной контейнер
        main_container = Frame(self.master, bg=COLORS["bg_dark"])
        main_container.pack(fill=BOTH, expand=True, padx=12, pady=12)

        # Шапка
        self._build_header(main_container)

        # Панель навигации (левая)
        self._build_left_panel(main_container)

        # Центральная область (правая)
        self._build_right_panel(main_container)

        # Нижняя панель (статус, прогресс, кнопка)
        self._build_bottom_panel(main_container)

    # ─── Шапка ────────────────────────────────────────────────
    def _build_header(self, parent: Frame):
        header = Frame(parent, bg=COLORS["bg_dark"])
        header.pack(fill=X, pady=(0, 12))

        title = Label(
            header, text="⚡ CyperMark",
            font=(FONT_FAMILY, 24, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_dark"]
        )
        title.pack(side=LEFT)

        subtitle = Label(
            header, text="Пакетный водяной знак для изображений",
            font=(FONT_FAMILY, 10),
            fg=COLORS["text_secondary"], bg=COLORS["bg_dark"]
        )
        subtitle.pack(side=LEFT, padx=(12, 0), pady=(8, 0))

        # Кнопка "О программе"
        about_btn = Button(
            header, text="?", font=(FONT_FAMILY, 10),
            bg=COLORS["bg_medium"], fg=COLORS["text_primary"],
            relief="flat", padx=8, pady=0, cursor="hand2",
            command=self._show_about
        )
        about_btn.pack(side=RIGHT, padx=(0, 4))

    # ─── Левая панель (настройки) ─────────────────────────────
    def _build_left_panel(self, parent: Frame):
        left = Frame(parent, bg=COLORS["bg_medium"], width=320)
        left.pack(side=LEFT, fill=Y, padx=(0, 12))
        left.pack_propagate(False)

        # Скролл для левой панели
        canvas = Canvas(left, bg=COLORS["bg_medium"], highlightthickness=0)
        scrollbar = Scrollbar(left, orient=VERTICAL, command=canvas.yview)
        scroll_frame = Frame(canvas, bg=COLORS["bg_medium"])

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Привязка колесика мыши
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Секции настроек ---
        row = 0

        # ▸ Файлы
        self._add_section_title(scroll_frame, "📁 Файлы", row)
        row += 1

        btn_w = 280
        self.btn_add_files = Button(
            scroll_frame, text="➕ Добавить файлы", width=30,
            bg=COLORS["bg_light"], fg=COLORS["text_primary"],
            relief="flat", padx=8, pady=6, cursor="hand2",
            command=self._add_files
        )
        self.btn_add_files.grid(row=row, column=0, pady=(4, 2), padx=12, sticky=W)
        row += 1

        self.btn_add_folder = Button(
            scroll_frame, text="📂 Добавить папку", width=30,
            bg=COLORS["bg_light"], fg=COLORS["text_primary"],
            relief="flat", padx=8, pady=6, cursor="hand2",
            command=self._add_folder
        )
        self.btn_add_folder.grid(row=row, column=0, pady=(2, 2), padx=12, sticky=W)
        row += 1

        self.lbl_file_count = Label(
            scroll_frame, text="Файлов: 0",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        )
        self.lbl_file_count.grid(row=row, column=0, pady=(2, 8), padx=12, sticky=W)
        row += 1

        # ▸ Выходная папка
        self._add_section_title(scroll_frame, "📥 Выходная папка", row)
        row += 1

        self.btn_output = Button(
            scroll_frame, text="📁 Выбрать папку", width=30,
            bg=COLORS["bg_light"], fg=COLORS["text_primary"],
            relief="flat", padx=8, pady=6, cursor="hand2",
            command=self._select_output
        )
        self.btn_output.grid(row=row, column=0, pady=(4, 2), padx=12, sticky=W)
        row += 1

        self.lbl_output = Label(
            scroll_frame, text="Не выбрана",
            font=(FONT_FAMILY, 8), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"], wraplength=280
        )
        self.lbl_output.grid(row=row, column=0, pady=(2, 8), padx=12, sticky=W)
        row += 1

        # ▸ Тип водяного знака
        self._add_section_title(scroll_frame, "🎨 Тип знака", row)
        row += 1

        self.wm_mode = StringVar(value="text")
        rb_text = ttk.Radiobutton(
            scroll_frame, text="Текст", variable=self.wm_mode,
            value="text", command=self._on_mode_change
        )
        rb_text.grid(row=row, column=0, pady=(4, 0), padx=12, sticky=W)
        row += 1

        rb_image = ttk.Radiobutton(
            scroll_frame, text="Изображение (логотип)", variable=self.wm_mode,
            value="image", command=self._on_mode_change
        )
        rb_image.grid(row=row, column=0, pady=(2, 8), padx=12, sticky=W)
        row += 1

        # Стиль для Radiobutton
        style = ttk.Style()
        style.configure("TRadiobutton", background=COLORS["bg_medium"],
                       foreground=COLORS["text_primary"],
                       font=(FONT_FAMILY, 9))

        # ▸ Текст водяного знака
        self._add_section_title(scroll_frame, "✏️ Текст", row)
        row += 1

        self.text_entry = Entry(
            scroll_frame, width=32,
            font=(FONT_FAMILY, 10), bg=COLORS["bg_light"],
            fg=COLORS["text_primary"], relief="flat",
            insertbackground=COLORS["text_primary"]
        )
        self.text_entry.insert(0, "© CyperMark")
        self.text_entry.grid(row=row, column=0, pady=(4, 2), padx=12, sticky=W)
        row += 1

        # Размер шрифта
        Label(
            scroll_frame, text="Размер шрифта:",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        ).grid(row=row, column=0, pady=(4, 0), padx=12, sticky=W)
        row += 1

        self.font_size_slider = Scale(
            scroll_frame, from_=8, to=200, orient=HORIZONTAL,
            length=260, bg=COLORS["bg_medium"],
            fg=COLORS["text_primary"], troughcolor=COLORS["bg_light"],
            highlightthickness=0, font=(FONT_FAMILY, 8)
        )
        self.font_size_slider.set(36)
        self.font_size_slider.grid(row=row, column=0, pady=(0, 4), padx=12, sticky=W)
        row += 1

        # Цвет шрифта (визуальный)
        Label(
            scroll_frame, text="Цвет шрифта:",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        ).grid(row=row, column=0, pady=(4, 0), padx=12, sticky=W)
        row += 1

        # Контейнер для кнопки цвета и HEX-метки
        color_frame = Frame(scroll_frame, bg=COLORS["bg_medium"])
        color_frame.grid(row=row, column=0, pady=(4, 8), padx=12, sticky=W)
        row += 1

        self.color_value = "#FFFFFF"

        self.color_btn = Button(
            color_frame, width=3, height=1,
            bg=self.color_value, relief="ridge", bd=2,
            cursor="hand2",
            command=self._pick_color
        )
        self.color_btn.pack(side=LEFT, padx=(0, 8))

        self.color_label = Label(
            color_frame, text=self.color_value,
            font=("Consolas", 10), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        )
        self.color_label.pack(side=LEFT)

        # ▸ Обводка текста
        self._add_section_title(scroll_frame, "✏️ Обводка текста", row)
        row += 1

        # Толщина обводки
        Label(
            scroll_frame, text="Толщина:",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        ).grid(row=row, column=0, pady=(4, 0), padx=12, sticky=W)
        row += 1

        self.stroke_width_slider = Scale(
            scroll_frame, from_=0, to=20, orient=HORIZONTAL,
            length=260, bg=COLORS["bg_medium"],
            fg=COLORS["text_primary"], troughcolor=COLORS["bg_light"],
            highlightthickness=0, font=(FONT_FAMILY, 8)
        )
        self.stroke_width_slider.set(0)
        self.stroke_width_slider.grid(row=row, column=0, pady=(4, 4), padx=12, sticky=W)
        row += 1

        # Цвет обводки
        Label(
            scroll_frame, text="Цвет обводки:",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        ).grid(row=row, column=0, pady=(4, 0), padx=12, sticky=W)
        row += 1

        stroke_frame = Frame(scroll_frame, bg=COLORS["bg_medium"])
        stroke_frame.grid(row=row, column=0, pady=(4, 8), padx=12, sticky=W)
        row += 1

        self.stroke_color_value = "#000000"

        self.stroke_color_btn = Button(
            stroke_frame, width=3, height=1,
            bg=self.stroke_color_value, relief="ridge", bd=2,
            cursor="hand2",
            command=self._pick_stroke_color
        )
        self.stroke_color_btn.pack(side=LEFT, padx=(0, 8))

        self.stroke_color_label = Label(
            stroke_frame, text=self.stroke_color_value,
            font=("Consolas", 10), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        )
        self.stroke_color_label.pack(side=LEFT)

        # ▸ Логотип
        self._add_section_title(scroll_frame, "🖼️ Логотип", row)
        row += 1

        self.btn_logo = Button(
            scroll_frame, text="🖼️ Выбрать логотип", width=30,
            bg=COLORS["bg_light"], fg=COLORS["text_primary"],
            relief="flat", padx=8, pady=6, cursor="hand2",
            command=self._select_logo
        )
        self.btn_logo.grid(row=row, column=0, pady=(4, 2), padx=12, sticky=W)
        row += 1

        self.lbl_logo = Label(
            scroll_frame, text="Не выбран",
            font=(FONT_FAMILY, 8), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"], wraplength=280
        )
        self.lbl_logo.grid(row=row, column=0, pady=(2, 8), padx=12, sticky=W)
        row += 1

        # ▸ Позиция
        self._add_section_title(scroll_frame, "📍 Позиция", row)
        row += 1

        self.position_var = StringVar(value="bottom_right")
        positions = [
            ("Вверху слева", "top_left"),
            ("Вверху по центру", "top_center"),
            ("Вверху справа", "top_right"),
            ("По центру", "center"),
            ("Внизу слева", "bottom_left"),
            ("Внизу по центру", "bottom_center"),
            ("Внизу справа", "bottom_right"),
            ("Замостить", "tile"),
        ]

        pos_frame = Frame(scroll_frame, bg=COLORS["bg_medium"])
        pos_frame.grid(row=row, column=0, pady=(4, 4), padx=12, sticky=W)
        row += 1

        for i, (label, val) in enumerate(positions):
            rb = ttk.Radiobutton(
                pos_frame, text=label, variable=self.position_var,
                value=val
            )
            rb.grid(row=i // 2, column=i % 2, sticky=W, padx=(0, 12), pady=1)

        # ▸ Прозрачность
        self._add_section_title(scroll_frame, "🔆 Прозрачность", row)
        row += 1

        self.opacity_slider = Scale(
            scroll_frame, from_=5, to=100, orient=HORIZONTAL,
            length=260, bg=COLORS["bg_medium"],
            fg=COLORS["text_primary"], troughcolor=COLORS["bg_light"],
            highlightthickness=0, font=(FONT_FAMILY, 8)
        )
        self.opacity_slider.set(60)
        self.opacity_slider.grid(row=row, column=0, pady=(4, 8), padx=12, sticky=W)
        row += 1

        # ▸ Поворот
        self._add_section_title(scroll_frame, "🔄 Поворот (градусы)", row)
        row += 1

        self.rotation_slider = Scale(
            scroll_frame, from_=-180, to=180, orient=HORIZONTAL,
            length=260, bg=COLORS["bg_medium"],
            fg=COLORS["text_primary"], troughcolor=COLORS["bg_light"],
            highlightthickness=0, font=(FONT_FAMILY, 8)
        )
        self.rotation_slider.set(0)
        self.rotation_slider.grid(row=row, column=0, pady=(4, 8), padx=12, sticky=W)
        row += 1

        # ▸ AI Auto-Placement
        self._add_section_title(scroll_frame, "🤖 AI Placement (эксп.)", row)
        row += 1

        self.ai_var = BooleanVar(value=False)
        self.ai_check = ttk.Checkbutton(
            scroll_frame, text="AI: свободная область",
            variable=self.ai_var
        )
        self.ai_check.grid(row=row, column=0, pady=(4, 8), padx=12, sticky=W)
        row += 1

        # ▸ Выходной формат
        self._add_section_title(scroll_frame, "💾 Выходной формат", row)
        row += 1

        self.format_var = StringVar(value="PNG")
        fmt_frame = Frame(scroll_frame, bg=COLORS["bg_medium"])
        fmt_frame.grid(row=row, column=0, pady=(4, 4), padx=12, sticky=W)
        row += 1

        for i, fmt in enumerate(["PNG", "JPEG", "WEBP"]):
            rb = ttk.Radiobutton(
                fmt_frame, text=fmt, variable=self.format_var, value=fmt
            )
            rb.grid(row=0, column=i, sticky=W, padx=(0, 12))

        # Качество (для JPEG/WEBP)
        Label(
            scroll_frame, text="Качество (1-100):",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"]
        ).grid(row=row, column=0, pady=(4, 0), padx=12, sticky=W)
        row += 1

        self.quality_slider = Scale(
            scroll_frame, from_=10, to=100, orient=HORIZONTAL,
            length=260, bg=COLORS["bg_medium"],
            fg=COLORS["text_primary"], troughcolor=COLORS["bg_light"],
            highlightthickness=0, font=(FONT_FAMILY, 8)
        )
        self.quality_slider.set(95)
        self.quality_slider.grid(row=row, column=0, pady=(4, 8), padx=12, sticky=W)
        row += 1

        # ▸ Суффикс
        self._add_section_title(scroll_frame, "🏷️ Суффикс файла", row)
        row += 1

        self.suffix_entry = Entry(
            scroll_frame, width=20,
            font=(FONT_FAMILY, 10), bg=COLORS["bg_light"],
            fg=COLORS["text_primary"], relief="flat",
            insertbackground=COLORS["text_primary"]
        )
        self.suffix_entry.insert(0, "_watermarked")
        self.suffix_entry.grid(row=row, column=0, pady=(4, 4), padx=12, sticky=W)
        row += 1

        # Кнопка сброса настроек
        self.btn_reset = Button(
            scroll_frame, text="↺ Сбросить настройки", width=30,
            bg=COLORS["bg_light"], fg=COLORS["text_primary"],
            relief="flat", padx=8, pady=6, cursor="hand2",
            command=self._reset_settings
        )
        self.btn_reset.grid(row=row, column=0, pady=(8, 12), padx=12, sticky=W)
        row += 1

        # Начальное состояние
        self._on_mode_change()

    # ─── Правая панель (превью + лог) ─────────────────────────
    def _build_right_panel(self, parent: Frame):
        right = Frame(parent, bg=COLORS["bg_dark"])
        right.pack(side=RIGHT, fill=BOTH, expand=True)

        # ▸ Превью
        preview_frame = Frame(right, bg=COLORS["bg_medium"], height=400)
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 8))
        preview_frame.pack_propagate(False)

        Label(
            preview_frame, text="🔍 Превью",
            font=(FONT_FAMILY, 11, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_medium"]
        ).pack(anchor=NW, padx=8, pady=4)

        self.preview_label = Label(
            preview_frame, text="Добавьте изображения\nдля предпросмотра",
            font=(FONT_FAMILY, 12), fg=COLORS["text_secondary"],
            bg=COLORS["bg_medium"], justify="center"
        )
        self.preview_label.pack(expand=True, fill=BOTH, padx=8, pady=8)

        # ▸ Лог
        log_frame = Frame(right, bg=COLORS["bg_medium"], height=180)
        log_frame.pack(fill=X, pady=(0, 8))
        log_frame.pack_propagate(False)

        Label(
            log_frame, text="📋 Журнал",
            font=(FONT_FAMILY, 11, "bold"),
            fg=COLORS["text_secondary"], bg=COLORS["bg_medium"]
        ).pack(anchor=NW, padx=8, pady=(4, 0))

        log_text_frame = Frame(log_frame, bg=COLORS["bg_medium"])
        log_text_frame.pack(fill=BOTH, expand=True, padx=8, pady=4)

        self.log_text = Text(
            log_text_frame, height=6,
            font=("Consolas", 9), bg=COLORS["bg_dark"],
            fg=COLORS["text_secondary"], relief="flat",
            wrap="word", state=DISABLED
        )
        log_scroll = Scrollbar(log_text_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        self.log_text.pack(side=LEFT, fill=BOTH, expand=True)
        log_scroll.pack(side=RIGHT, fill=Y)

        # ▸ Drag & Drop файлов на превью
        self.preview_label.drop_target_register = lambda *a: None

    # ─── Нижняя панель ────────────────────────────────────────
    def _build_bottom_panel(self, parent: Frame):
        bottom = Frame(parent, bg=COLORS["bg_dark"])
        bottom.pack(fill=X)

        # Прогресс
        self.progress = ttk.Progressbar(
            bottom, length=300, mode="determinate"
        )
        self.progress.pack(side=LEFT, padx=(0, 12), fill=X, expand=True)

        # Статус
        self.status_var = StringVar(value="Готов")
        self.status_label = Label(
            bottom, textvariable=self.status_var,
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"]
        )
        self.status_label.pack(side=LEFT, padx=(0, 12))

        # Кнопка старта
        self.btn_start = Button(
            bottom, text="🚀 ЗАПУСТИТЬ", width=20,
            font=(FONT_FAMILY, 11, "bold"),
            bg=COLORS["accent"], fg=COLORS["text_primary"],
            relief="flat", padx=12, pady=8, cursor="hand2",
            command=self._start_processing
        )
        self.btn_start.pack(side=RIGHT)

    # ─── Вспомогательные методы ───────────────────────────────
    def _add_section_title(self, parent: Frame, text: str, row: int):
        """Добавляет заголовок секции в левую панель."""
        frame = Frame(parent, bg=COLORS["bg_light"], height=1)
        frame.grid(row=row, column=0, pady=(12, 4), padx=12, sticky="ew")

        lbl = Label(
            parent, text=text,
            font=(FONT_FAMILY, 10, "bold"), fg=COLORS["accent"],
            bg=COLORS["bg_medium"]
        )
        lbl.grid(row=row + 1, column=0, pady=(0, 2), padx=12, sticky=W)

    def _log(self, message: str):
        """Добавляет сообщение в лог."""
        self.log_text.configure(state=NORMAL)
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        self.log_text.configure(state=DISABLED)

    def _update_status(self, text: str):
        """Обновляет строку статуса."""
        self.status_var.set(text)
        self.master.update_idletasks()

    def _get_config_from_ui(self) -> WatermarkConfig:
        """Собирает конфиг из UI."""
        mode = self.wm_mode.get()

        # Позиция
        pos_map = {
            "top_left": Position.TOP_LEFT,
            "top_center": Position.TOP_CENTER,
            "top_right": Position.TOP_RIGHT,
            "center": Position.CENTER,
            "center_left": Position.CENTER_LEFT,
            "center_right": Position.CENTER_RIGHT,
            "bottom_left": Position.BOTTOM_LEFT,
            "bottom_center": Position.BOTTOM_CENTER,
            "bottom_right": Position.BOTTOM_RIGHT,
            "tile": Position.TILE,
        }
        position = pos_map.get(self.position_var.get(), Position.BOTTOM_RIGHT)

        config = WatermarkConfig(
            mode=mode,
            text=self.text_entry.get(),
            font_size=self.font_size_slider.get(),
            font_color=self.color_value,
            stroke_width=self.stroke_width_slider.get(),
            stroke_color=self.stroke_color_value,
            logo_path=self.logo_path if hasattr(self, 'logo_path') else "",
            logo_scale=0.15,
            position=position,
            opacity=self.opacity_slider.get(),
            margin_x=20,
            margin_y=20,
            rotation=self.rotation_slider.get(),
            ai_placement=self.ai_var.get(),
            output_format=self.format_var.get(),
            output_quality=self.quality_slider.get(),
            suffix=self.suffix_entry.get(),
        )
        return config

    # ─── Обработчики ──────────────────────────────────────────
    def _add_files(self):
        """Выбор файлов."""
        files = filedialog.askopenfilenames(
            title="Выберите изображения",
            filetypes=[
                ("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif"),
                ("Все файлы", "*.*")
            ]
        )
        if files:
            self.input_files = list(files)
            self.lbl_file_count.configure(text=f"Файлов: {len(self.input_files)}")
            self._log(f"Добавлено {len(files)} файлов")
            self._update_preview()

    def _add_folder(self):
        """Выбор папки с изображениями."""
        folder = filedialog.askdirectory(title="Выберите папку с изображениями")
        if folder:
            self.input_dir = folder
            extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
            files = [
                os.path.join(folder, f) for f in os.listdir(folder)
                if Path(f).suffix.lower() in extensions
            ]
            self.input_files = files
            self.lbl_file_count.configure(text=f"Файлов: {len(self.input_files)}")
            self._log(f"Добавлена папка: {folder} ({len(files)} изображений)")
            self._update_preview()

    def _select_output(self):
        """Выбор выходной папки."""
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_dir = folder
            self.lbl_output.configure(text=folder)
            self._log(f"Выходная папка: {folder}")

    def _select_logo(self):
        """Выбор логотипа."""
        file = filedialog.askopenfilename(
            title="Выберите логотип",
            filetypes=[
                ("Все изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.tif"),
                ("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg"),
                ("WEBP", "*.webp"), ("BMP", "*.bmp"),
                ("TIFF", "*.tiff *.tif"), ("Все файлы", "*.*")
            ]
        )
        if file:
            self.logo_path = file
            self.lbl_logo.configure(text=Path(file).name)
            self._log(f"Логотип: {file}")
            self._update_preview()

    def _on_mode_change(self):
        """Переключение между текстом и изображением."""
        mode = self.wm_mode.get()
        if mode == "text":
            self.text_entry.configure(state=NORMAL)
            self.font_size_slider.configure(state=NORMAL)
            self.color_btn.configure(state=NORMAL)
            self.stroke_width_slider.configure(state=NORMAL)
            self.stroke_color_btn.configure(state=NORMAL)
        else:
            self.text_entry.configure(state=DISABLED)
            self.font_size_slider.configure(state=DISABLED)
            self.color_btn.configure(state=DISABLED)
            self.stroke_width_slider.configure(state=DISABLED)
            self.stroke_color_btn.configure(state=DISABLED)

    def _reset_settings(self):
        """Сброс настроек к стандартным."""
        self.text_entry.delete(0, END)
        self.text_entry.insert(0, "© CyperMark")
        self.font_size_slider.set(36)
        self._set_color("#FFFFFF")
        self.stroke_width_slider.set(0)
        self._set_stroke_color("#000000")
        self.opacity_slider.set(60)
        self.rotation_slider.set(0)
        self.position_var.set("bottom_right")
        self.format_var.set("PNG")
        self.quality_slider.set(95)
        self.suffix_entry.delete(0, END)
        self.suffix_entry.insert(0, "_watermarked")
        self.ai_var.set(False)
        self._log("Настройки сброшены")

    def _update_preview(self):
        """Обновляет превью."""
        if not self.input_files:
            return

        try:
            # Открываем первое изображение
            img = Image.open(self.input_files[0]).convert("RGBA")
            config = self._get_config_from_ui()

            # Генерируем превью
            preview = generate_preview(img, config, (500, 400))
            self.preview_image = preview

            # Отображаем
            self.preview_tk = ImageTk.PhotoImage(preview)
            self.preview_label.configure(
                image=self.preview_tk,
                text="",
                justify="center"
            )
        except Exception as e:
            self._log(f"Ошибка превью: {e}")

    def _show_about(self):
        """Окно 'О программе'."""
        about = Toplevel(self.master)
        about.title("О CyperMark")
        about.geometry("400x300")
        about.configure(bg=COLORS["bg_dark"])
        about.resizable(False, False)

        Label(
            about, text="⚡ CyperMark",
            font=(FONT_FAMILY, 20, "bold"),
            fg=COLORS["accent"], bg=COLORS["bg_dark"]
        ).pack(pady=(30, 10))

        Label(
            about, text="Версия 1.0",
            font=(FONT_FAMILY, 10), fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"]
        ).pack()

        Label(
            about, text="Пакетное наложение водяных знаков\nна изображения",
            font=(FONT_FAMILY, 10), fg=COLORS["text_primary"],
            bg=COLORS["bg_dark"], justify="center"
        ).pack(pady=20)

        Label(
            about, text="© 2026 Cyper",
            font=(FONT_FAMILY, 9), fg=COLORS["text_secondary"],
            bg=COLORS["bg_dark"]
        ).pack(pady=10)

        Button(
            about, text="Закрыть", width=15,
            bg=COLORS["accent"], fg=COLORS["text_primary"],
            relief="flat", cursor="hand2",
            command=about.destroy
        ).pack(pady=10)

    # ─── Выбор цвета ──────────────────────────────────────────
    def _set_color(self, hex_color: str):
        """Устанавливает цвет и обновляет визуальный элемент."""
        self.color_value = hex_color
        self.color_btn.configure(bg=hex_color)
        self.color_label.configure(text=hex_color)

    def _pick_color(self):
        """Открывает диалог выбора цвета."""
        result = tk_askcolor(
            title="Выберите цвет шрифта",
            initialcolor=self.color_value,
            parent=self.master
        )
        if result and result[1]:
            self._set_color(result[1])

    def _set_stroke_color(self, hex_color: str):
        """Устанавливает цвет обводки и обновляет визуальный элемент."""
        self.stroke_color_value = hex_color
        self.stroke_color_btn.configure(bg=hex_color)
        self.stroke_color_label.configure(text=hex_color)

    def _pick_stroke_color(self):
        """Открывает диалог выбора цвета обводки."""
        result = tk_askcolor(
            title="Выберите цвет обводки",
            initialcolor=self.stroke_color_value,
            parent=self.master
        )
        if result and result[1]:
            self._set_stroke_color(result[1])

    # ─── Запуск обработки ─────────────────────────────────────
    def _start_processing(self):
        """Запускает пакетную обработку в отдельном потоке."""
        if self.is_running:
            return

        if not self.input_files:
            messagebox.showwarning("Нет файлов", "Добавьте изображения для обработки.")
            return

        if not self.output_dir:
            messagebox.showwarning("Нет папки", "Выберите выходную папку.")
            return

        if self.wm_mode.get() == "image" and (not hasattr(self, 'logo_path') or not self.logo_path):
            messagebox.showwarning("Нет логотипа", "Выберите изображение для водяного знака.")
            return

        self.is_running = True
        self.btn_start.configure(state=DISABLED, text="⏳ ОБРАБОТКА...")
        self.progress["value"] = 0
        self._log("🚀 Запуск обработки...")

        config = self._get_config_from_ui()

        def progress_callback(current: int, total: int, message: str):
            self.progress["maximum"] = total
            self.progress["value"] = current
            self._update_status(f"[{current}/{total}] {message}")
            self._log(message)
            self.master.update_idletasks()

        def run():
            try:
                result_files = batch_process(
                    self.input_files, self.output_dir, config, progress_callback
                )
                self.master.after(0, lambda: self._on_complete(result_files))
            except Exception as e:
                self.master.after(0, lambda: self._on_error(str(e)))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_complete(self, result_files: list[str]):
        """Обработка завершена."""
        self.is_running = False
        self.btn_start.configure(state=NORMAL, text="🚀 ЗАПУСТИТЬ")
        self.progress["value"] = self.progress["maximum"]
        self._update_status(f"✅ Готово! Обработано {len(result_files)} файлов")
        self._log(f"✅ Готово! Сохранено в: {self.output_dir}")

        messagebox.showinfo(
            "Готово!",
            f"Обработано файлов: {len(result_files)}\n"
            f"Сохранено в: {self.output_dir}"
        )

    def _on_error(self, error: str):
        """Ошибка обработки."""
        self.is_running = False
        self.btn_start.configure(state=NORMAL, text="🚀 ЗАПУСТИТЬ")
        self._update_status(f"❌ Ошибка: {error}")
        self._log(f"❌ Ошибка: {error}")

        messagebox.showerror("Ошибка", error)
