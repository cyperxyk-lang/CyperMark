"""
CyperMark v1.0
Пакетное наложение водяных знаков на изображения.

Использование:
    python main.py              # GUI режим
    python main.py --cli        # CLI режим
    python main.py -i INPUT -o OUTPUT -t "© CyperMark"
"""

import sys
import os

# Добавляем текущую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from watermark_core import (
    WatermarkConfig, Position, SUPPORTED_FORMATS,
    batch_process, get_supported_formats
)


# ─── CLI режим ────────────────────────────────────────────────
def cli_mode(args: list[str]):
    """Режим командной строки."""
    import argparse

    parser = argparse.ArgumentParser(
        description="CyperMark — пакетное наложение водяных знаков",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python main.py --cli -i ./photos -o ./watermarked -t "© 2026"
  python main.py --cli -i ./photos -o ./watermarked -l logo.png -p center -o 50
        """
    )
    parser.add_argument("--cli", action="store_true", help="CLI режим")
    parser.add_argument("-i", "--input", required=True, help="Входная папка или файл")
    parser.add_argument("-o", "--output", required=True, help="Выходная папка")

    # Тип знака
    parser.add_argument("-m", "--mode", choices=["text", "image"], default="text",
                       help="Тип водяного знака (text/image)")

    # Текст
    parser.add_argument("-t", "--text", default="© CyperMark", help="Текст водяного знака")
    parser.add_argument("--font-size", type=int, default=36, help="Размер шрифта")
    parser.add_argument("--font-color", default="#FFFFFF", help="Цвет текста (HEX)")
    parser.add_argument("--stroke-width", type=int, default=0, help="Толщина обводки текста (0 = без обводки)")
    parser.add_argument("--stroke-color", default="#000000", help="Цвет обводки (HEX)")

    # Изображение
    parser.add_argument("-l", "--logo", help="Путь к логотипу (PNG)")
    parser.add_argument("--logo-scale", type=float, default=0.15, help="Масштаб логотипа (0-1)")

    # Позиция
    parser.add_argument("-p", "--position", default="bottom_right",
                       choices=[p.name.lower() for p in Position],
                       help="Позиция водяного знака")

    # Настройки
    parser.add_argument("--opacity", type=int, default=60, help="Прозрачность (0-100)")
    parser.add_argument("--rotation", type=float, default=0.0, help="Поворот (градусы)")
    parser.add_argument("--margin-x", type=int, default=20, help="Отступ по X")
    parser.add_argument("--margin-y", type=int, default=20, help="Отступ по Y")
    parser.add_argument("--ai", action="store_true", help="AI Auto-Placement")

    # Выход
    parser.add_argument("-f", "--format", choices=["PNG", "JPEG", "WEBP"], default="PNG",
                       help="Выходной формат")
    parser.add_argument("-q", "--quality", type=int, default=95, help="Качество (1-100)")
    parser.add_argument("--suffix", default="_watermarked", help="Суффикс файла")
    parser.add_argument("--overwrite", action="store_true", help="Перезаписывать файлы")

    parsed = parser.parse_args(args)

    # Маппинг позиции
    pos_map = {p.name.lower(): p for p in Position}
    position = pos_map.get(parsed.position, Position.BOTTOM_RIGHT)

    config = WatermarkConfig(
        mode=parsed.mode,
        text=parsed.text,
        font_size=parsed.font_size,
        font_color=parsed.font_color,
        stroke_width=parsed.stroke_width,
        stroke_color=parsed.stroke_color,
        logo_path=parsed.logo or "",
        logo_scale=parsed.logo_scale,
        position=position,
        opacity=parsed.opacity,
        margin_x=parsed.margin_x,
        margin_y=parsed.margin_y,
        rotation=parsed.rotation,
        ai_placement=parsed.ai,
        output_format=parsed.format,
        output_quality=parsed.quality,
        suffix=parsed.suffix,
        overwrite=parsed.overwrite,
    )

    # Собираем входные файлы
    input_path = parsed.input
    input_files = []
    if os.path.isfile(input_path):
        if any(input_path.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
            input_files = [input_path]
    elif os.path.isdir(input_path):
        for f in os.listdir(input_path):
            full = os.path.join(input_path, f)
            if os.path.isfile(full) and any(f.lower().endswith(ext) for ext in SUPPORTED_FORMATS):
                input_files.append(full)

    if not input_files:
        print(f"[!] No images found in: {input_path}")
        sys.exit(1)

    print("==> CyperMark -- CLI mode")
    print(f"  Files: {len(input_files)}")
    print(f"  Type: {config.mode.upper()}")
    print(f"  Output: {parsed.output}")
    print(f"  Format: {config.output_format}")
    print()

    # Progress
    def progress(current, total, message):
        bar_len = 30
        filled = int(bar_len * current / total)
        bar = "#" * filled + "." * (bar_len - filled)
        pct = int(100 * current / total)
        print(f"\r  [{bar}] {pct}%  {message}", end="")
        if current == total:
            print()

    result = batch_process(input_files, parsed.output, config, progress)
    print(f"\n[OK] Done! Processed {len(result)} files.")


# ─── Точка входа ──────────────────────────────────────────────
if __name__ == "__main__":
    if "--cli" in sys.argv:
        # Убираем --cli из аргументов для argparse
        args = [a for a in sys.argv[1:] if a != "--cli"]
        cli_mode(args)
    else:
        # GUI режим
        try:
            from gui import CyperMarkGUI
            import tkinter as tk

            root = tk.Tk()
            app = CyperMarkGUI(root)
            root.mainloop()
        except ImportError as e:
            print(f"❌ Ошибка загрузки GUI: {e}")
            print("  Используйте --cli для работы в командной строке.")
            sys.exit(1)
