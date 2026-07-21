"""
CyperMark — ядро обработки водяных знаков
Основа: Pillow + OpenCV
"""

from __future__ import annotations
import os
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Optional
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import cv2
import numpy as np


# ─── Позиции водяного знака ───────────────────────────────────
class Position(Enum):
    TOP_LEFT      = auto()
    TOP_CENTER    = auto()
    TOP_RIGHT     = auto()
    CENTER_LEFT   = auto()
    CENTER        = auto()
    CENTER_RIGHT  = auto()
    BOTTOM_LEFT   = auto()
    BOTTOM_CENTER = auto()
    BOTTOM_RIGHT  = auto()
    TILE          = auto()  # замостить всю картинку


# ─── Конфигурация водяного знака ──────────────────────────────
@dataclass
class WatermarkConfig:
    """Все настройки водяного знака"""
    # Тип: текст или изображение
    mode: str = "text"                     # "text" | "image"

    # Текст
    text: str = "© CyperMark"
    font_name: str = "Arial"
    font_path: str = ""
    font_size: int = 36
    font_color: str = "#FFFFFF"
    font_bold: bool = False
    font_italic: bool = False

    # Обводка текста (outline/stroke)
    stroke_width: int = 0
    stroke_color: str = "#000000"

    # Изображение-логотип
    logo_path: str = ""
    logo_scale: float = 0.15               # доля от ширины исходного изображения

    # Общие настройки
    position: Position = Position.BOTTOM_RIGHT
    opacity: int = 60                      # 0-100
    margin_x: int = 20
    margin_y: int = 20
    rotation: float = 0.0                  # градусы
    tile_spacing_x: int = 0
    tile_spacing_y: int = 0

    # AI Auto-Placement (опционально)
    ai_placement: bool = False
    ai_avoid_faces: bool = True
    ai_avoid_center: bool = True

    # Выходные настройки
    output_format: str = "PNG"             # "PNG" | "JPEG" | "WEBP"
    output_quality: int = 95               # 1-100
    preserve_metadata: bool = True
    overwrite: bool = False
    suffix: str = "_watermarked"


# ─── Форматы ──────────────────────────────────────────────────
SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}

def get_supported_formats() -> set:
    return SUPPORTED_FORMATS

def is_image_file(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_FORMATS


# ─── Шрифты ───────────────────────────────────────────────────
def get_installed_fonts() -> list[tuple[str, str]]:
    """
    Возвращает список установленных шрифтов как (display_name, file_path).
    Работает через реестр Windows, сортировка по имени.
    """
    fonts = []
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
        )
        count = winreg.QueryInfoKey(key)[1]
        for i in range(count):
            try:
                name, value, _ = winreg.EnumValue(key, i)
                if name.endswith(" (TrueType)"):
                    display = name[:-len(" (TrueType)")]
                    font_dir = os.environ.get("WINDIR", r"C:\Windows")
                    fonts_dir = os.path.join(font_dir, "Fonts")
                    fpath = os.path.join(fonts_dir, value) if not os.path.isabs(value) else value
                    if os.path.exists(fpath):
                        fonts.append((display, fpath))
            except (OSError, UnicodeDecodeError):
                continue
        winreg.CloseKey(key)
    except Exception:
        pass

    # Fallback: сканируем C:\Windows\Fonts
    if not fonts:
        font_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
        try:
            for f in sorted(os.listdir(font_dir)):
                if f.lower().endswith(".ttf"):
                    name = os.path.splitext(f)[0]
                    fpath = os.path.join(font_dir, f)
                    fonts.append((name, fpath))
        except Exception:
            pass

    # Сортируем и убираем дубликаты
    seen = set()
    unique = []
    for name, path in fonts:
        if name.lower() not in seen:
            seen.add(name.lower())
            unique.append((name, path))
    return sorted(unique, key=lambda x: x[0].lower())


def _load_font(config: WatermarkConfig, size: Optional[int] = None) -> ImageFont.FreeType:
    """
    Загружает шрифт из конфига.
    Приоритет: font_path → font_name → Arial → default.
    """
    fs = size if size is not None else config.font_size
    # 1. Прямой путь к файлу
    if config.font_path and os.path.exists(config.font_path):
        try:
            return ImageFont.truetype(config.font_path, fs)
        except (IOError, OSError):
            pass
    # 2. По имени — пробуем напрямую (работает на Windows)
    if config.font_name:
        try:
            return ImageFont.truetype(config.font_name, fs)
        except (IOError, OSError):
            pass
        # Пробуем найти в списке установленных
        try:
            for name, fpath in get_installed_fonts():
                if name.lower() == config.font_name.lower():
                    return ImageFont.truetype(fpath, fs)
        except Exception:
            pass
    # 3. Arial — дефолт Windows
    try:
        return ImageFont.truetype("arial.ttf", fs)
    except (IOError, OSError):
        pass
    # 4. Встроенный дефолт Pillow
    return ImageFont.load_default()


# ─── AI: найти свободную область ──────────────────────────────
def _find_free_area(
    cv_img: np.ndarray,
    watermark_w: int,
    watermark_h: int,
    prefer_side: str = "bottom_right"
) -> tuple[int, int]:
    """
    Примитивный AI-поиск свободной области (без моделей).
    Анализирует карту градиентов/текстур — ищет наименее детализированную зону.
    """
    h, w = cv_img.shape[:2]

    # Преобразуем в grayscale
    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # Карта градиентов (области с высокой детализацией)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    grad_map = np.abs(laplacian)

    # Разобьём на сектора
    step_x, step_y = watermark_w // 2, watermark_h // 2
    if step_x < 1 or step_y < 1:
        return (w - watermark_w - 10, h - watermark_h - 10)

    best_score = float("inf")
    best_pos = (w - watermark_w - 10, h - watermark_h - 10)

    # Приоритетные зоны (в зависимости от prefer_side)
    zones = []
    if "bottom" in prefer_side:
        y_range = range(max(0, h - 3 * watermark_h), max(0, h - watermark_h), step_y)
    else:
        y_range = range(0, h - watermark_h, step_y)

    if "right" in prefer_side:
        x_range = range(max(0, w - 3 * watermark_w), max(0, w - watermark_w), step_x)
    else:
        x_range = range(0, w - watermark_w, step_x)

    for y in y_range:
        for x in x_range:
            # Средняя градиентная энергия в области
            region = grad_map[y:y + watermark_h, x:x + watermark_w]
            score = float(np.mean(region))

            # Штраф за центр изображения
            if ai_avoid_center := True:
                cx, cy = w // 2, h // 2
                if (x < cx < x + watermark_w) and (y < cy < y + watermark_h):
                    score *= 1.5

            if score < best_score:
                best_score = score
                best_pos = (x, y)

    return best_pos


# ─── Наложение текстового водяного знака ──────────────────────
def apply_text_watermark(
    image: Image.Image,
    text: str,
    config: WatermarkConfig,
    font: Optional[ImageFont.FreeType] = None
) -> Image.Image:
    """Накладывает текстовый водяной знак на изображение."""
    img = image.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Загружаем шрифт
    if font is None:
        font = _load_font(config)

    # Размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Позиция
    pos = _calc_position(img.size, (text_w, text_h), config)

    # Цвет с прозрачностью
    alpha = int(255 * config.opacity / 100)
    try:
        r, g, b = tuple(int(config.font_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    except (ValueError, IndexError):
        r, g, b = 255, 255, 255
    fill_color = (r, g, b, alpha)

    # Цвет обводки
    stroke_rgb = (0, 0, 0)
    if config.stroke_width > 0:
        try:
            sc = config.stroke_color
            stroke_rgb = tuple(int(sc.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        except (ValueError, IndexError):
            stroke_rgb = (0, 0, 0)

    # Рисуем текст (с обводкой, если указана)
    if config.position == Position.TILE:
        # Текст с замощением: создаём один элемент, поворачиваем, тайлим
        pad = config.font_size  # запас, чтобы текст не обрезался при повороте
        tile_wm = Image.new("RGBA", (text_w + pad * 2, text_h + pad * 2), (0,0,0,0))
        td = ImageDraw.Draw(tile_wm)
        td.text((pad, pad), text, font=font, fill=fill_color,
                stroke_width=config.stroke_width, stroke_fill=stroke_rgb)
        if config.rotation != 0:
            tile_wm = tile_wm.rotate(config.rotation, expand=True, resample=Image.BICUBIC)
        _tile_layer(overlay, tile_wm, img.size)
    else:
        draw.text(
            pos, text,
            font=font, fill=fill_color,
            stroke_width=config.stroke_width, stroke_fill=stroke_rgb
        )
        # Поворот
        if config.rotation != 0:
            overlay = overlay.rotate(config.rotation, expand=False, center=(
                pos[0] + text_w // 2, pos[1] + text_h // 2
            ))

    return Image.alpha_composite(img, overlay)


# ─── Наложение графического водяного знака ────────────────────
def apply_image_watermark(
    image: Image.Image,
    logo: Image.Image,
    config: WatermarkConfig
) -> Image.Image:
    """Накладывает изображение-логотип как водяной знак."""
    img = image.convert("RGBA")
    logo = logo.convert("RGBA")

    # Масштаб
    scale = config.logo_scale
    new_w = int(img.width * scale)
    new_h = int(logo.height * (new_w / logo.width))
    if new_w < 1 or new_h < 1:
        return img
    logo = logo.resize((new_w, new_h), Image.LANCZOS)

    # Прозрачность
    if config.opacity < 100:
        alpha_factor = config.opacity / 100
        r, g, b, a = logo.split()
        a = a.point(lambda x: int(x * alpha_factor))
        logo = Image.merge("RGBA", (r, g, b, a))

    # TILE — замостить (вращение внутри _tile_image)
    if config.position == Position.TILE:
        return _tile_image(img, logo, config)

    # Позиция
    pos = _calc_position(img.size, logo.size, config)

    # Поворот
    if config.rotation != 0:
        logo = logo.rotate(config.rotation, expand=True, center=(
            logo.width // 2, logo.height // 2
        ))
        # Пересчитываем позицию после поворота
        pos = _calc_position(img.size, logo.size, config)

    img.paste(logo, pos, logo)
    return img


# ─── TILE (замощение) ─────────────────────────────────────────
def _tile_layer(
    base_layer: Image.Image,
    tile: Image.Image,
    img_size: tuple[int, int],
    spacing_x: int = 0,
    spacing_y: int = 0,
) -> None:
    """Замостить tile по base_layer (in-place)."""
    tw, th = tile.size
    iw, ih = img_size
    if spacing_x <= 0:
        spacing_x = tw // 2
    if spacing_y <= 0:
        spacing_y = th // 2
    sx = tw + spacing_x
    sy = th + spacing_y
    for y in range(-th, ih, sy):
        for x in range(-tw, iw, sx):
            base_layer.paste(tile, (x, y), tile)


def _tile_image(
    image: Image.Image,
    watermark: Image.Image,
    config: WatermarkConfig
) -> Image.Image:
    """
    Замостить картинку изображением-водяным знаком.
    Создаёт один элемент с учётом поворота, потом тайлит.
    """
    img = image.convert("RGBA")
    # Поворот элемента (если указан)
    wm = watermark
    if config.rotation != 0:
        wm = wm.rotate(config.rotation, expand=True, resample=Image.BICUBIC)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    _tile_layer(overlay, wm, img.size,
                config.tile_spacing_x, config.tile_spacing_y)
    return Image.alpha_composite(img, overlay)


# ─── Расчёт позиции ───────────────────────────────────────────
def _calc_position(
    img_size: tuple[int, int],
    wm_size: tuple[int, int],
    config: WatermarkConfig
) -> tuple[int, int]:
    """Возвращает (x, y) верхнего левого угла водяного знака."""
    iw, ih = img_size
    ww, wh = wm_size
    mx, my = config.margin_x, config.margin_y

    pos_map = {
        Position.TOP_LEFT:      (mx, my),
        Position.TOP_CENTER:    ((iw - ww) // 2, my),
        Position.TOP_RIGHT:     (iw - ww - mx, my),
        Position.CENTER_LEFT:   (mx, (ih - wh) // 2),
        Position.CENTER:        ((iw - ww) // 2, (ih - wh) // 2),
        Position.CENTER_RIGHT:  (iw - ww - mx, (ih - wh) // 2),
        Position.BOTTOM_LEFT:   (mx, ih - wh - my),
        Position.BOTTOM_CENTER: ((iw - ww) // 2, ih - wh - my),
        Position.BOTTOM_RIGHT:  (iw - ww - mx, ih - wh - my),
        Position.TILE:          (0, 0),
    }

    return pos_map.get(config.position, (mx, my))


# ─── AI Auto-Placement ────────────────────────────────────────
def apply_ai_placement(
    image: Image.Image,
    wm_size: tuple[int, int],
    config: WatermarkConfig
) -> tuple[int, int]:
    """Определяет оптимальную позицию водяного знака через OpenCV."""
    # Конвертируем PIL -> OpenCV
    cv_img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)

    prefer_side = config.position.name.lower()
    x, y = _find_free_area(cv_img, wm_size[0], wm_size[1], prefer_side)

    return (x, y)


# ─── Пакетная обработка ───────────────────────────────────────
def batch_process(
    input_paths: list[str],
    output_dir: str,
    config: WatermarkConfig,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> list[str]:
    """
    Пакетная обработка списка файлов.
    Возвращает список сохранённых файлов.
    """
    os.makedirs(output_dir, exist_ok=True)
    processed = []
    total = len(input_paths)

    # Предзагружаем шрифт для текстового режима
    font = None
    if config.mode == "text":
        font = _load_font(config)

    # Предзагружаем логотип для графического режима
    logo = None
    if config.mode == "image" and config.logo_path:
        try:
            logo = Image.open(config.logo_path).convert("RGBA")
        except Exception as e:
            if progress_callback:
                progress_callback(0, total, f"Logo load error: {e}")
            return []

    for idx, filepath in enumerate(input_paths):
        try:
            # Имя файла
            path = Path(filepath)
            ext = path.suffix.lower()

            if ext not in SUPPORTED_FORMATS:
                continue

            # Открываем
            img = Image.open(filepath).convert("RGBA")

            # Накладываем водяной знак
            if config.mode == "text":
                result = apply_text_watermark(img, config.text, config, font)
            elif config.mode == "image" and logo is not None:
                # AI placement?
                if config.ai_placement:
                    wm_size = logo.size
                    x, y = apply_ai_placement(img, wm_size, config)
                    config_tmp = WatermarkConfig(**{
                        k: v for k, v in config.__dict__.items()
                        if k != "position"
                    })
                    config_tmp.position = Position.TOP_LEFT
                    config_tmp.margin_x = x
                    config_tmp.margin_y = y
                    result = apply_image_watermark(img, logo, config_tmp)
                else:
                    result = apply_image_watermark(img, logo, config)
            else:
                # Fallback: текст
                result = apply_text_watermark(img, config.text, config, font)

            # Конвертируем в нужный формат
            output_format = config.output_format.upper()
            if output_format == "JPEG":
                result = result.convert("RGB")

            # Имя выходного файла
            stem = path.stem
            if config.suffix:
                out_filename = f"{stem}{config.suffix}.{config.output_format.lower()}"
            else:
                out_filename = f"{stem}.{config.output_format.lower()}"

            out_path = os.path.join(output_dir, out_filename)

            # Проверка перезаписи
            if os.path.exists(out_path) and not config.overwrite:
                base = stem
                counter = 1
                while os.path.exists(out_path):
                    out_filename = f"{base}{config.suffix}_{counter}.{config.output_format.lower()}"
                    out_path = os.path.join(output_dir, out_filename)
                    counter += 1

            # Сохраняем
            save_kwargs = {}
            if config.output_format.upper() in ("JPEG", "WEBP"):
                save_kwargs["quality"] = config.output_quality

            result.save(out_path, format=config.output_format.upper(), **save_kwargs)
            processed.append(out_path)

            if progress_callback:
                progress_callback(idx + 1, total, f"[OK] {out_filename}")

        except Exception as e:
            if progress_callback:
                progress_callback(idx + 1, total, f"[ERR] {Path(filepath).name}: {e}")

    return processed


# ─── Превью ────────────────────────────────────────────────────
def generate_preview(
    image: Image.Image,
    config: WatermarkConfig,
    max_size: tuple[int, int] = (600, 600)
) -> Image.Image:
    """Генерирует превью с водяным знаком для предпросмотра."""
    # Масштабируем до max_size
    img = image.copy()
    img.thumbnail(max_size, Image.LANCZOS)

    if config.mode == "text":
        # Адаптируем размер шрифта под превью
        preview_config = WatermarkConfig(**{
            k: v for k, v in config.__dict__.items()
            if k != "font_size"
        })
        scale_factor = img.width / image.width
        preview_config.font_size = max(12, int(config.font_size * scale_factor))
        result = apply_text_watermark(img, config.text, preview_config)
    elif config.mode == "image" and config.logo_path and os.path.exists(config.logo_path):
        logo = Image.open(config.logo_path).convert("RGBA")
        result = apply_image_watermark(img, logo, config)
    else:
        result = apply_text_watermark(img, config.text, config)

    return result.convert("RGB")
