"""
CyperMark v2 — графический интерфейс на CustomTkinter
Modern Material Design, тёмная тема, улучшенный UX
"""

from __future__ import annotations

import os
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from tkinter import filedialog, colorchooser

import customtkinter as ctk
from PIL import Image, ImageTk

from watermark_core import (
    WatermarkConfig, Position, SUPPORTED_FORMATS,
    batch_process, generate_preview, get_installed_fonts,
)

# ─── Настройка темы CustomTkinter ─────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─── Цветовая палитра (дополнительные акценты) ───────────────
class Colors:
    bg_dark = "#0d1117"
    bg_card = "#161b22"
    bg_input = "#21262d"
    border = "#30363d"
    text_primary = "#f0f6fc"
    text_secondary = "#8b949e"
    accent = "#58a6ff"
    accent_hover = "#79c0ff"
    success = "#3fb950"
    warning = "#d29922"
    error = "#f85149"
    surface = "#0d1117"


# ─── Класс главного окна ─────────────────────────────────────
class CyperMarkV2(ctk.CTk):
    """CyperMark v2 — главное окно приложения."""

    def __init__(self):
        super().__init__()

        # ── Конфигурация окна ──
        self.title("CyperMark v2 — Пакетный водяной знак")
        self.geometry("1280x820")
        self.minsize(1024, 680)

        # ── Переменные состояния ──
        self.input_files: list[str] = []
        self.output_dir: str = ""
        self.preview_img: Optional[Image.Image] = None
        self.ctk_preview: Optional[ctk.CTkImage] = None
        self.is_running = False
        self.logo_path: str = ""
        self.font_color = "#FFFFFF"
        self.stroke_color = "#000000"
        self._preview_after_id = None

        # Конфигурация по умолчанию
        self.config = WatermarkConfig()

        # ── Сборка интерфейса ──
        self._build_ui()

        # ── Привязка событий ──
        self._bind_events()

        # Статус
        self._log("CyperMark v2 готов к работе. Добавьте изображения.")

    # ═══════════════════════════════════════════════════════════
    #  СБОРКА ИНТЕРФЕЙСА
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        """Собирает весь интерфейс."""
        # ── Конфигурация сетки главного окна ──
        self.grid_columnconfigure(0, weight=0)   # левая панель (файлы)
        self.grid_columnconfigure(1, weight=1)   # центр (превью)
        self.grid_columnconfigure(2, weight=0)   # правая панель (настройки)
        self.grid_rowconfigure(0, weight=0)      # верхняя панель
        self.grid_rowconfigure(1, weight=1)      # основная область
        self.grid_rowconfigure(2, weight=0)      # нижняя панель

        # ── Верхняя панель ──
        self._build_header()

        # ── Левая панель (файлы) ──
        self._build_file_panel()

        # ── Центр (превью) ──
        self._build_preview_panel()

        # ── Правая панель (настройки) ──
        self._build_settings_panel()

        # ── Нижняя панель ──
        self._build_bottom_panel()

    # ─── Верхняя панель ───────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self, height=56, corner_radius=0,
                              fg_color=Colors.bg_card)
        header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(1, weight=1)

        # Логотип + название
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=(20, 0), pady=10, sticky="w")

        self.title_label = ctk.CTkLabel(
            title_frame, text="⚡ CyperMark",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Colors.accent
        )
        self.title_label.pack(side="left")

        self.version_label = ctk.CTkLabel(
            title_frame, text="v2.0",
            font=ctk.CTkFont(size=11),
            text_color=Colors.text_secondary
        )
        self.version_label.pack(side="left", padx=(8, 0), pady=(6, 0))

        # Счётчик файлов
        self.file_count_label = ctk.CTkLabel(
            header, text="Файлов: 0",
            font=ctk.CTkFont(size=12),
            text_color=Colors.text_secondary
        )
        self.file_count_label.grid(row=0, column=1, padx=10, pady=10)

        # Кнопка "О программе"
        self.about_btn = ctk.CTkButton(
            header, text="?", width=32, height=32,
            font=ctk.CTkFont(size=14),
            fg_color=Colors.bg_input, hover_color=Colors.border,
            corner_radius=16, command=self._show_about
        )
        self.about_btn.grid(row=0, column=2, padx=(0, 16), pady=10, sticky="e")

    # ─── Левая панель (файлы) ─────────────────────────────────
    def _build_file_panel(self):
        panel = ctk.CTkFrame(self, width=240, corner_radius=12,
                             fg_color=Colors.bg_card)
        panel.grid(row=1, column=0, padx=(12, 6), pady=(8, 8), sticky="nsew")
        panel.grid_rowconfigure(4, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # ▸ Заголовок
        ctk.CTkLabel(
            panel, text="📁 Файлы",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Colors.text_primary
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="w")

        # ▸ Кнопки добавления
        self.btn_add_files = ctk.CTkButton(
            panel, text="+ Добавить файлы",
            command=self._add_files,
            fg_color=Colors.bg_input, hover_color=Colors.border,
            height=36
        )
        self.btn_add_files.grid(row=1, column=0, padx=12, pady=(0, 4), sticky="ew")

        self.btn_add_folder = ctk.CTkButton(
            panel, text="+ Добавить папку",
            command=self._add_folder,
            fg_color=Colors.bg_input, hover_color=Colors.border,
            height=36
        )
        self.btn_add_folder.grid(row=2, column=0, padx=12, pady=(0, 4), sticky="ew")

        self.btn_clear = ctk.CTkButton(
            panel, text="✕ Очистить список",
            command=self._clear_files,
            fg_color=Colors.bg_input, hover_color=Colors.error,
            height=32,
            font=ctk.CTkFont(size=11)
        )
        self.btn_clear.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")

        # ▸ Список файлов (скроллируемый)
        self.file_list_frame = ctk.CTkScrollableFrame(
            panel, corner_radius=8,
            fg_color=Colors.bg_input
        )
        self.file_list_frame.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="nsew")

        # Инфо-лейбл в списке
        self.file_list_info = ctk.CTkLabel(
            self.file_list_frame, text="Нет файлов",
            font=ctk.CTkFont(size=11),
            text_color=Colors.text_secondary
        )
        self.file_list_info.pack(pady=20)

    # ─── Центральная панель (превью) ──────────────────────────
    def _build_preview_panel(self):
        panel = ctk.CTkFrame(self, corner_radius=12, fg_color=Colors.bg_card)
        panel.grid(row=1, column=1, padx=(6, 6), pady=(8, 8), sticky="nsew")
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # ▸ Заголовок
        header_frame = ctk.CTkFrame(panel, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=16, pady=(16, 4), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame, text="🔍 Предпросмотр",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=Colors.text_primary
        ).pack(side="left")

        self.zoom_var = ctk.StringVar(value="100%")
        self.zoom_menu = ctk.CTkOptionMenu(
            header_frame, values=["25%", "50%", "75%", "100%", "150%", "200%", "Fit"],
            variable=self.zoom_var, width=80,
            fg_color=Colors.bg_input, button_color=Colors.bg_input,
            button_hover_color=Colors.border,
            command=self._on_zoom_change
        )
        self.zoom_menu.pack(side="right")

        # ▸ Область превью
        self.preview_frame = ctk.CTkFrame(
            panel, corner_radius=8, fg_color=Colors.surface
        )
        self.preview_frame.grid(row=1, column=0, padx=12, pady=(4, 12), sticky="nsew")
        self.preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            self.preview_frame, text="Добавьте изображения\nдля предпросмотра",
            font=ctk.CTkFont(size=14),
            text_color=Colors.text_secondary
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # ─── Правая панель (настройки) ────────────────────────────
    def _build_settings_panel(self):
        panel = ctk.CTkFrame(self, width=320, corner_radius=12,
                             fg_color=Colors.bg_card)
        panel.grid(row=1, column=2, padx=(6, 12), pady=(8, 8), sticky="nsew")
        panel.grid_rowconfigure(0, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # Скроллируемая область настроек
        self.settings_frame = ctk.CTkScrollableFrame(
            panel, corner_radius=8,
            fg_color="transparent"
        )
        self.settings_frame.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")
        self.settings_frame.grid_columnconfigure(0, weight=1)

        row = 0

        # ═══ СЕКЦИЯ: Выходная папка ═══
        self._section_title("📥 Выходная папка", row)
        row += 1

        self.btn_output = ctk.CTkButton(
            self.settings_frame, text="📁 Выбрать папку",
            command=self._select_output,
            fg_color=Colors.bg_input, hover_color=Colors.border,
            height=36
        )
        self.btn_output.grid(row=row, column=0, padx=12, pady=(4, 2), sticky="ew")
        row += 1

        self.lbl_output = ctk.CTkLabel(
            self.settings_frame, text="Не выбрана",
            font=ctk.CTkFont(size=10),
            text_color=Colors.text_secondary, wraplength=280
        )
        self.lbl_output.grid(row=row, column=0, padx=12, pady=(0, 12), sticky="w")
        row += 1

        # ═══ СЕКЦИЯ: Тип водяного знака ═══
        self._section_title("🎨 Тип водяного знака", row)
        row += 1

        self.wm_mode = ctk.StringVar(value="text")
        self.mode_segmented = ctk.CTkSegmentedButton(
            self.settings_frame, values=["Текст", "Логотип"],
            command=self._on_mode_change
        )
        self.mode_segmented.grid(row=row, column=0, padx=12, pady=(4, 12), sticky="ew")
        row += 1

        # ═══ СЕКЦИЯ: Текст ═══
        self._section_title("✏️ Текст", row)
        row += 1

        self.text_entry = ctk.CTkEntry(
            self.settings_frame, placeholder_text="© CyperMark",
            fg_color=Colors.bg_input, border_color=Colors.border
        )
        self.text_entry.insert(0, "© CyperMark")
        self.text_entry.grid(row=row, column=0, padx=12, pady=(4, 4), sticky="ew")
        row += 1

        # Шрифт
        lbl = ctk.CTkLabel(self.settings_frame, text="Шрифт",
                          font=ctk.CTkFont(size=11), text_color=Colors.text_secondary)
        lbl.grid(row=row, column=0, padx=12, pady=(4, 2), sticky="w")
        row += 1

        font_list = get_installed_fonts()
        font_names = [name for name, _ in font_list] if font_list else ["Arial"]
        # Arial почти всегда первый, проверим есть ли в списке
        default_font = "Arial" if "Arial" in font_names else font_names[0]
        self.font_name_var = ctk.StringVar(value=default_font)
        self.font_selector = ctk.CTkOptionMenu(
            self.settings_frame, values=font_names,
            variable=self.font_name_var,
            fg_color=Colors.bg_input, button_color=Colors.accent,
            button_hover_color=Colors.accent_hover,
            dropdown_fg_color=Colors.bg_card,
            dropdown_hover_color=Colors.accent_hover,
            font=ctk.CTkFont(size=11),
            dynamic_resizing=False
        )
        self.font_selector.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="ew")
        row += 1

        # Размер шрифта
        row = self._add_slider(row, "Размер шрифта", "font_size", 8, 200, 36)

        # Цвет шрифта (визуальный)
        lbl = ctk.CTkLabel(self.settings_frame, text="Цвет шрифта",
                          font=ctk.CTkFont(size=11), text_color=Colors.text_secondary)
        lbl.grid(row=row, column=0, padx=12, pady=(4, 2), sticky="w")
        row += 1

        color_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        color_frame.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="ew")
        color_frame.grid_columnconfigure(1, weight=1)
        row += 1

        self.color_btn = ctk.CTkButton(
            color_frame, text="", width=36, height=28,
            fg_color=self.font_color, hover_color=self.font_color,
            corner_radius=4,
            command=self._pick_color
        )
        self.color_btn.grid(row=0, column=0, padx=(0, 8))

        self.color_label = ctk.CTkLabel(
            color_frame, text=self.font_color,
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=Colors.text_secondary
        )
        self.color_label.grid(row=0, column=1, sticky="w")

        # ═══ СЕКЦИЯ: Обводка ═══
        self._section_title("✏️ Обводка текста", row)
        row += 1

        row = self._add_slider(row, "Толщина", "stroke_width", 0, 20, 0)

        lbl = ctk.CTkLabel(self.settings_frame, text="Цвет обводки",
                          font=ctk.CTkFont(size=11), text_color=Colors.text_secondary)
        lbl.grid(row=row, column=0, padx=12, pady=(4, 2), sticky="w")
        row += 1

        stroke_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        stroke_frame.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="ew")
        stroke_frame.grid_columnconfigure(1, weight=1)
        row += 1

        self.stroke_color_btn = ctk.CTkButton(
            stroke_frame, text="", width=36, height=28,
            fg_color=self.stroke_color, hover_color=self.stroke_color,
            corner_radius=4,
            command=self._pick_stroke_color
        )
        self.stroke_color_btn.grid(row=0, column=0, padx=(0, 8))

        self.stroke_color_label = ctk.CTkLabel(
            stroke_frame, text=self.stroke_color,
            font=ctk.CTkFont(size=11, family="Consolas"),
            text_color=Colors.text_secondary
        )
        self.stroke_color_label.grid(row=0, column=1, sticky="w")

        # ═══ СЕКЦИЯ: Логотип ═══
        self._section_title("🖼️ Логотип", row)
        row += 1

        self.btn_logo = ctk.CTkButton(
            self.settings_frame, text="🖼️ Выбрать PNG",
            command=self._select_logo,
            fg_color=Colors.bg_input, hover_color=Colors.border,
            height=36
        )
        self.btn_logo.grid(row=row, column=0, padx=12, pady=(4, 2), sticky="ew")
        row += 1

        self.lbl_logo = ctk.CTkLabel(
            self.settings_frame, text="Не выбран",
            font=ctk.CTkFont(size=10),
            text_color=Colors.text_secondary, wraplength=280
        )
        self.lbl_logo.grid(row=row, column=0, padx=12, pady=(0, 12), sticky="w")
        row += 1

        # ═══ СЕКЦИЯ: Позиция ═══
        self._section_title("📍 Позиция", row)
        row += 1

        self.position_var = ctk.StringVar(value="bottom_right")
        positions = [
            ("Вверху слева", "top_left"), ("Вверху центр", "top_center"),
            ("Вверху справа", "top_right"),
            ("Центр", "center"),
            ("Внизу слева", "bottom_left"), ("Внизу центр", "bottom_center"),
            ("Внизу справа", "bottom_right"),
            ("Замостить", "tile"),
        ]
        pos_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        pos_frame.grid(row=row, column=0, padx=12, pady=(4, 8), sticky="ew")
        pos_frame.grid_columnconfigure((0, 1), weight=1)
        row += 1

        for i, (label, val) in enumerate(positions):
            rb = ctk.CTkRadioButton(
                pos_frame, text=label, variable=self.position_var,
                value=val, font=ctk.CTkFont(size=10),
                fg_color=Colors.accent
            )
            rb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 8), pady=2)

        # ═══ СЕКЦИЯ: Прозрачность и поворот ═══
        row = self._add_slider(row, "Прозрачность", "opacity", 5, 100, 60)
        row = self._add_slider(row, "Поворот (°)", "rotation", -180, 180, 0)

        # ═══ СЕКЦИЯ: AI ═══
        self._section_title("🤖 AI Auto-Placement", row)
        row += 1

        self.ai_var = ctk.BooleanVar(value=False)
        self.ai_switch = ctk.CTkSwitch(
            self.settings_frame, text="Свободная область",
            variable=self.ai_var,
            font=ctk.CTkFont(size=11),
            progress_color=Colors.accent
        )
        self.ai_switch.grid(row=row, column=0, padx=12, pady=(4, 12), sticky="w")
        row += 1

        # ═══ СЕКЦИЯ: Формат и качество ═══
        self._section_title("💾 Выходной формат", row)
        row += 1

        self.format_var = ctk.StringVar(value="PNG")
        fmt_seg = ctk.CTkSegmentedButton(
            self.settings_frame, values=["PNG", "JPEG", "WEBP"],
            variable=self.format_var
        )
        fmt_seg.grid(row=row, column=0, padx=12, pady=(4, 4), sticky="ew")
        row += 1

        row = self._add_slider(row, "Качество (1-100)", "quality", 10, 100, 95)

        # ═══ СЕКЦИЯ: Суффикс ═══
        self._section_title("🏷️ Суффикс файла", row)
        row += 1

        self.suffix_entry = ctk.CTkEntry(
            self.settings_frame, placeholder_text="_watermarked",
            fg_color=Colors.bg_input, border_color=Colors.border
        )
        self.suffix_entry.insert(0, "_watermarked")
        self.suffix_entry.grid(row=row, column=0, padx=12, pady=(4, 8), sticky="ew")
        row += 1

        # ═══ КНОПКИ: Пресеты ═══
        preset_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        preset_frame.grid(row=row, column=0, padx=12, pady=(8, 4), sticky="ew")
        preset_frame.grid_columnconfigure((0, 1), weight=1)
        row += 1

        self.btn_save_preset = ctk.CTkButton(
            preset_frame, text="💾 Сохранить пресет",
            command=self._save_preset,
            fg_color=Colors.bg_input, hover_color=Colors.border,
            height=32, font=ctk.CTkFont(size=11)
        )
        self.btn_save_preset.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.btn_load_preset = ctk.CTkButton(
            preset_frame, text="📂 Загрузить пресет",
            command=self._load_preset,
            fg_color=Colors.bg_input, hover_color=Colors.border,
            height=32, font=ctk.CTkFont(size=11)
        )
        self.btn_load_preset.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        row += 1

        # Кнопка сброса
        self.btn_reset = ctk.CTkButton(
            self.settings_frame, text="↺ Сбросить настройки",
            command=self._reset_settings,
            fg_color=Colors.bg_input, hover_color=Colors.warning,
            height=32, font=ctk.CTkFont(size=11)
        )
        self.btn_reset.grid(row=row, column=0, padx=12, pady=(4, 16), sticky="ew")
        row += 1

        # Начальное состояние
        self._on_mode_change("Текст")

    # ─── Нижняя панель ────────────────────────────────────────
    def _build_bottom_panel(self):
        bottom = ctk.CTkFrame(self, height=60, corner_radius=0,
                              fg_color=Colors.bg_card)
        bottom.grid(row=2, column=0, columnspan=3, sticky="ew", padx=0, pady=0)
        bottom.grid_columnconfigure(0, weight=1)
        bottom.grid_columnconfigure(1, weight=0)

        # Прогресс
        progress_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        progress_frame.grid(row=0, column=0, padx=(16, 8), pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            progress_frame, text="Готов",
            font=ctk.CTkFont(size=11),
            text_color=Colors.text_secondary
        )
        self.status_label.grid(row=0, column=0, padx=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame, height=8, corner_radius=4,
            progress_color=Colors.accent,
            fg_color=Colors.bg_input
        )
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="",
            font=ctk.CTkFont(size=10),
            text_color=Colors.text_secondary
        )
        self.progress_label.grid(row=0, column=2, padx=(0, 8))

        # ❤️ Донат
        self.btn_donate = ctk.CTkButton(
            progress_frame, text="❤️",
            width=36, height=36,
            corner_radius=18,
            fg_color=Colors.warning,
            hover_color="#c0392b",
            font=ctk.CTkFont(size=16),
            command=self._open_donate
        )
        self.btn_donate.grid(row=0, column=3, padx=(8, 0))

        # Кнопка старт
        self.btn_start = ctk.CTkButton(
            bottom, text="🚀 ЗАПУСТИТЬ",
            command=self._start_processing,
            fg_color=Colors.accent, hover_color=Colors.accent_hover,
            height=40, width=180,
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8
        )
        self.btn_start.grid(row=0, column=1, padx=(8, 16), pady=10)

        # Лог (маленький текст)
        self.log_textbox = ctk.CTkTextbox(
            bottom, height=28, corner_radius=4,
            fg_color=Colors.bg_input, text_color=Colors.text_secondary,
            font=ctk.CTkFont(size=9, family="Consolas"),
            border_width=0
        )
        self.log_textbox.grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 8), sticky="ew")
        self.log_textbox.insert("0.0", "⚡ CyperMark v2 загружен")
        self.log_textbox.configure(state="disabled")

    # ═══════════════════════════════════════════════════════════
    #  ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ═══════════════════════════════════════════════════════════

    def _section_title(self, text: str, row: int):
        """Добавляет заголовок секции."""
        frame = ctk.CTkFrame(self.settings_frame, height=1,
                             fg_color=Colors.border)
        frame.grid(row=row, column=0, padx=12, pady=(12, 4), sticky="ew")

        lbl = ctk.CTkLabel(
            self.settings_frame, text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Colors.accent
        )
        lbl.grid(row=row + 1, column=0, padx=12, pady=(0, 2), sticky="w")

    def _add_slider(self, row: int, label: str, attr: str,
                    from_: int, to: int, default: int) -> int:
        """Добавляет слайдер с подписью."""
        lbl = ctk.CTkLabel(self.settings_frame, text=label,
                          font=ctk.CTkFont(size=11), text_color=Colors.text_secondary)
        lbl.grid(row=row, column=0, padx=12, pady=(4, 2), sticky="w")
        row += 1

        setattr(self, f"{attr}_slider",
                ctk.CTkSlider(self.settings_frame, from_=from_, to=to,
                             number_of_steps=to - from_,
                             fg_color=Colors.bg_input,
                             progress_color=Colors.accent,
                             button_color=Colors.accent,
                             button_hover_color=Colors.accent_hover,
                             command=lambda v, a=attr: self._on_slider_change(a, v)))
        slider = getattr(self, f"{attr}_slider")
        slider.set(default)
        slider.grid(row=row, column=0, padx=12, pady=(0, 8), sticky="ew")

        # value label
        val_lbl = ctk.CTkLabel(self.settings_frame, text=str(default),
                               font=ctk.CTkFont(size=10, family="Consolas"),
                               text_color=Colors.text_secondary)
        val_lbl.grid(row=row, column=0, padx=(12, 16), pady=(0, 8), sticky="e")
        setattr(self, f"{attr}_val", val_lbl)

        row += 1
        return row

    def _on_slider_change(self, attr: str, value: float):
        """Обновляет подпись значения слайдера + превью."""
        val_lbl = getattr(self, f"{attr}_val", None)
        if val_lbl:
            val_lbl.configure(text=str(int(value)))
        self._update_preview()

    def _log(self, message: str):
        """Добавляет сообщение в лог."""
        try:
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"\n{message}")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        except Exception:
            pass

    def _update_status(self, text: str):
        """Обновляет строку статуса."""
        self.status_label.configure(text=text)
        self.update_idletasks()

    def _bind_events(self):
        """Привязка событий — все изменения обновляют превью."""
        # Текст
        self.text_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        # Шрифт
        self.font_name_var.trace_add("write", lambda *a: self._update_preview())
        # Позиция
        self.position_var.trace_add("write", lambda *a: self._update_preview())
        # AI
        self.ai_var.trace_add("write", lambda *a: self._update_preview())
        # Формат
        self.format_var.trace_add("write", lambda *a: self._update_preview())
        # Режим (текст/лого): _on_mode_change уже вызывает _update_preview()

    def _get_config_from_ui(self) -> WatermarkConfig:
        """Собирает конфиг из UI."""
        pos_map = {
            "top_left": Position.TOP_LEFT, "top_center": Position.TOP_CENTER,
            "top_right": Position.TOP_RIGHT, "center": Position.CENTER,
            "center_left": Position.CENTER_LEFT, "center_right": Position.CENTER_RIGHT,
            "bottom_left": Position.BOTTOM_LEFT, "bottom_center": Position.BOTTOM_CENTER,
            "bottom_right": Position.BOTTOM_RIGHT, "tile": Position.TILE,
        }
        position = pos_map.get(self.position_var.get(), Position.BOTTOM_RIGHT)

        return WatermarkConfig(
            mode="text" if self.wm_mode.get() == "Текст" else "image",
            text=self.text_entry.get() or "© CyperMark",
            font_name=self.font_name_var.get(),
            font_size=int(self.font_size_slider.get()),
            font_color=self.font_color,
            stroke_width=int(self.stroke_width_slider.get()),
            stroke_color=self.stroke_color,
            logo_path=self.logo_path,
            logo_scale=0.15,
            position=position,
            opacity=int(self.opacity_slider.get()),
            margin_x=20, margin_y=20,
            rotation=int(self.rotation_slider.get()),
            ai_placement=self.ai_var.get(),
            output_format=self.format_var.get(),
            output_quality=int(self.quality_slider.get()),
            suffix=self.suffix_entry.get() or "_watermarked",
        )

    # ═══════════════════════════════════════════════════════════
    #  ОБРАБОТЧИКИ
    # ═══════════════════════════════════════════════════════════

    def _add_files(self):
        files = filedialog.askopenfilenames(
            title="Выберите изображения",
            filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
                       ("Все файлы", "*.*")]
        )
        if files:
            self.input_files = list(files)
            self._update_file_list()
            self._log(f"Добавлено {len(files)} файлов")
            self._update_preview()

    def _add_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с изображениями")
        if folder:
            extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
            files = sorted([
                os.path.join(folder, f) for f in os.listdir(folder)
                if Path(f).suffix.lower() in extensions
            ])
            self.input_files = files
            self._update_file_list()
            self._log(f"Добавлена папка: {Path(folder).name} ({len(files)} изображений)")
            self._update_preview()

    def _clear_files(self):
        self.input_files = []
        self._update_file_list()
        self.preview_label.configure(text="Нет файлов для предпросмотра")
        self.file_count_label.configure(text="Файлов: 0")
        self._log("Список файлов очищен")

    def _update_file_list(self):
        """Обновляет список файлов в левой панели."""
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        self.file_count_label.configure(text=f"Файлов: {len(self.input_files)}")

        if not self.input_files:
            self.file_list_info = ctk.CTkLabel(
                self.file_list_frame, text="Нет файлов",
                font=ctk.CTkFont(size=11), text_color=Colors.text_secondary
            )
            self.file_list_info.pack(pady=20)
            return

        # Показываем первые 30 файлов (для производительности)
        max_show = 30
        files_to_show = self.input_files[:max_show]
        remaining = len(self.input_files) - max_show

        for i, fpath in enumerate(files_to_show):
            name = Path(fpath).name
            ext = Path(fpath).suffix.upper()
            lbl = ctk.CTkLabel(
                self.file_list_frame, text=f"  {name}",
                font=ctk.CTkFont(size=10),
                text_color=Colors.text_secondary,
                anchor="w"
            )
            lbl.pack(fill="x", padx=4, pady=1)

        if remaining > 0:
            lbl = ctk.CTkLabel(
                self.file_list_frame, text=f"  ... и ещё {remaining} файлов",
                font=ctk.CTkFont(size=10, slant="italic"),
                text_color=Colors.text_secondary
            )
            lbl.pack(fill="x", padx=4, pady=1)

    def _select_output(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_dir = folder
            self.lbl_output.configure(text=folder)

    def _select_logo(self):
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
            self._update_preview()

    def _on_mode_change(self, value: str):
        """Переключение режима."""
        is_text = value == "Текст"
        # Text widgets
        self.text_entry.configure(state="normal" if is_text else "disabled")
        self.font_size_slider.configure(state="normal" if is_text else "disabled")
        self.color_btn.configure(state="normal" if is_text else "disabled")
        self.stroke_width_slider.configure(state="normal" if is_text else "disabled")
        self.stroke_color_btn.configure(state="normal" if is_text else "disabled")
        # Logo widgets
        state = "disabled" if is_text else "normal"
        self.btn_logo.configure(state=state)
        self._update_preview()

    def _pick_color(self):
        result = colorchooser.askcolor(
            title="Цвет шрифта",
            initialcolor=self.font_color,
            parent=self
        )
        if result and result[1]:
            self.font_color = result[1]
            self.color_btn.configure(fg_color=result[1], hover_color=result[1])
            self.color_label.configure(text=result[1])
            self._update_preview()

    def _pick_stroke_color(self):
        result = colorchooser.askcolor(
            title="Цвет обводки",
            initialcolor=self.stroke_color,
            parent=self
        )
        if result and result[1]:
            self.stroke_color = result[1]
            self.stroke_color_btn.configure(fg_color=result[1], hover_color=result[1])
            self.stroke_color_label.configure(text=result[1])
            self._update_preview()

    def _on_zoom_change(self, value: str):
        """Изменение зума превью."""
        self._update_preview()

    def _update_preview(self, debounce_ms: int = 50):
        """Обновляет превью с debounce."""
        # Отменяем предыдущий отложенный вызов
        if hasattr(self, '_preview_after_id') and self._preview_after_id:
            self.after_cancel(self._preview_after_id)
        # Ставим новый с задержкой (для слайдеров — сглаживание)
        self._preview_after_id = self.after(debounce_ms, self._do_update_preview)

    def _do_update_preview(self):
        """Реальная отрисовка превью."""
        self._preview_after_id = None
        if not self.input_files:
            return
        try:
            img = Image.open(self.input_files[0]).convert("RGBA")
            config = self._get_config_from_ui()

            # Определяем размер превью
            zoom = self.zoom_var.get()
            if zoom == "Fit":
                pw, ph = 500, 400
            else:
                pct = int(zoom.replace("%", ""))
                pw, ph = 500 * pct // 100, 400 * pct // 100

            preview = generate_preview(img, config, (pw, ph))

            # Конвертируем в CTkImage
            self.ctk_preview = ctk.CTkImage(
                light_image=preview,
                dark_image=preview,
                size=(preview.width, preview.height)
            )
            self.preview_label.configure(image=self.ctk_preview, text="")
        except Exception as e:
            self._log(f"Ошибка превью: {e}")

    def _save_preset(self):
        """Сохраняет текущие настройки в JSON."""
        file = filedialog.asksaveasfilename(
            title="Сохранить пресет",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if not file:
            return

        config = self._get_config_from_ui()
        data = {
            "version": "2.0",
            "date": datetime.now().isoformat(),
            "config": {
                "mode": config.mode,
                "text": config.text,
                "font_name": config.font_name,
                "font_size": config.font_size,
                "font_color": config.font_color,
                "stroke_width": config.stroke_width,
                "stroke_color": config.stroke_color,
                "position": config.position.name,
                "opacity": config.opacity,
                "rotation": config.rotation,
                "ai_placement": config.ai_placement,
                "output_format": config.output_format,
                "output_quality": config.output_quality,
                "suffix": config.suffix,
            }
        }
        try:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._log(f"Пресет сохранён: {Path(file).name}")
        except Exception as e:
            self._log(f"Ошибка сохранения: {e}")

    def _load_preset(self):
        """Загружает настройки из JSON."""
        file = filedialog.askopenfilename(
            title="Загрузить пресет",
            filetypes=[("JSON", "*.json")]
        )
        if not file:
            return

        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)

            cfg = data.get("config", {})
            self.text_entry.delete(0, "end")
            self.text_entry.insert(0, cfg.get("text", "© CyperMark"))
            font_name = cfg.get("font_name", "Arial")
            if font_name in self.font_selector.cget("values"):
                self.font_name_var.set(font_name)
            self.font_size_slider.set(cfg.get("font_size", 36))
            self._set_color_ui(cfg.get("font_color", "#FFFFFF"))
            self.stroke_width_slider.set(cfg.get("stroke_width", 0))
            self._set_stroke_color_ui(cfg.get("stroke_color", "#000000"))
            self.opacity_slider.set(cfg.get("opacity", 60))
            self.rotation_slider.set(cfg.get("rotation", 0))
            self.position_var.set(cfg.get("position", "bottom_right").lower())
            self.ai_var.set(cfg.get("ai_placement", False))
            self.format_var.set(cfg.get("output_format", "PNG"))
            self.quality_slider.set(cfg.get("output_quality", 95))
            self.suffix_entry.delete(0, "end")
            self.suffix_entry.insert(0, cfg.get("suffix", "_watermarked"))

            self._log(f"Пресет загружен: {Path(file).name}")
            self._update_preview()
        except Exception as e:
            self._log(f"Ошибка загрузки: {e}")

    def _set_color_ui(self, hex_color: str):
        self.font_color = hex_color
        self.color_btn.configure(fg_color=hex_color, hover_color=hex_color)
        self.color_label.configure(text=hex_color)

    def _set_stroke_color_ui(self, hex_color: str):
        self.stroke_color = hex_color
        self.stroke_color_btn.configure(fg_color=hex_color, hover_color=hex_color)
        self.stroke_color_label.configure(text=hex_color)

    def _reset_settings(self):
        """Сброс к стандартным."""
        self.text_entry.delete(0, "end")
        self.text_entry.insert(0, "© CyperMark")
        if "Arial" in self.font_selector.cget("values"):
            self.font_name_var.set("Arial")
        self.font_size_slider.set(36)
        self._set_color_ui("#FFFFFF")
        self.stroke_width_slider.set(0)
        self._set_stroke_color_ui("#000000")
        self.opacity_slider.set(60)
        self.rotation_slider.set(0)
        self.position_var.set("bottom_right")
        self.format_var.set("PNG")
        self.quality_slider.set(95)
        self.suffix_entry.delete(0, "end")
        self.suffix_entry.insert(0, "_watermarked")
        self.ai_var.set(False)
        self._log("Настройки сброшены")
        self._update_preview()

    def _open_donate(self):
        """Открыть ссылку на донат."""
        import webbrowser
        webbrowser.open("https://dalink.to/doublehook")
        self._log("❤️ Спасибо за поддержку!")

    def _show_about(self):
        """Окно 'О программе'."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("О CyperMark")
        dialog.geometry("380x300")
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog, text="⚡ CyperMark",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=Colors.accent
        ).pack(pady=(30, 4))

        ctk.CTkLabel(
            dialog, text="v2.0",
            font=ctk.CTkFont(size=12),
            text_color=Colors.text_secondary
        ).pack()

        ctk.CTkLabel(
            dialog, text="Пакетное наложение водяных знаков",
            font=ctk.CTkFont(size=12),
            text_color=Colors.text_primary
        ).pack(pady=(12, 4))

        ctk.CTkLabel(
            dialog, text="AI-защита ваших изображений",
            font=ctk.CTkFont(size=11),
            text_color=Colors.text_secondary
        ).pack()

        ctk.CTkLabel(
            dialog, text="© 2026 Cyper",
            font=ctk.CTkFont(size=10),
            text_color=Colors.text_secondary
        ).pack(pady=(20, 0))

        ctk.CTkButton(
            dialog, text="Закрыть", command=dialog.destroy,
            fg_color=Colors.accent, hover_color=Colors.accent_hover,
            width=120
        ).pack(pady=(20, 20))

    # ═══════════════════════════════════════════════════════════
    #  ЗАПУСК ОБРАБОТКИ
    # ═══════════════════════════════════════════════════════════

    def _start_processing(self):
        if self.is_running:
            return

        if not self.input_files:
            self._log("Ошибка: нет файлов для обработки")
            return

        if not self.output_dir:
            self._log("Ошибка: не выбрана выходная папка")
            return

        if self.wm_mode.get() == "Логотип" and not self.logo_path:
            self._log("Ошибка: не выбран логотип")
            return

        self.is_running = True
        self.btn_start.configure(state="disabled", text="⏳ ОБРАБОТКА...")
        self.progress_bar.set(0)
        self._log("🚀 Запуск обработки...")

        config = self._get_config_from_ui()

        def progress_callback(current: int, total: int, message: str):
            self.progress_bar.set(current / total)
            self.progress_label.configure(text=f"{current}/{total}")
            self._update_status(message)
            self.update_idletasks()

        def run():
            try:
                result = batch_process(
                    self.input_files, self.output_dir, config, progress_callback
                )
                self.after(0, lambda: self._on_complete(result))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _on_complete(self, result: list[str]):
        self.is_running = False
        self.btn_start.configure(state="normal", text="🚀 ЗАПУСТИТЬ")
        self.progress_bar.set(1)
        self.progress_label.configure(text=f"{len(result)}/{len(result)}")
        self._update_status(f"✅ Готово! Обработано {len(result)} файлов")
        self._log(f"✅ Готово! Сохранено в: {self.output_dir}")

    def _on_error(self, error: str):
        self.is_running = False
        self.btn_start.configure(state="normal", text="🚀 ЗАПУСТИТЬ")
        self._update_status(f"❌ Ошибка: {error}")
        self._log(f"❌ Ошибка: {error}")


# ─── Точка входа ──────────────────────────────────────────────
if __name__ == "__main__":
    app = CyperMarkV2()
    app.mainloop()
