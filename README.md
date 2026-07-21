# ⚡ CyperMark

<p align="center">
  <b>Пакетное наложение водяных знаков на изображения</b><br>
  <b>Batch watermark tool for images</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white"/>
  <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat"/>
</p>

---

## 🇷🇺 CyperMark

**CyperMark** — это быстрый и удобный инструмент для пакетного наложения водяных знаков на изображения. Создан для AI-художников, фотографов и контент-мейкеров.

### Возможности

- ✏️ **Текстовый водяной знак** — любой текст, 147+ шрифтов, цвет, обводка
- 🖼️ **Логотип** — PNG, JPG, WEBP, BMP, TIFF (с прозрачностью)
- 📦 **Пакетная обработка** — 500 фото за 30 секунд
- 🎯 **AI Auto-Placement** — умное размещение в свободной области
- 🔄 **Замощение (Tile)** — водяной знак по всей поверхности с поворотом
- 👁️ **Live Preview** — мгновенное обновление при изменении настроек
- 💾 **Выходной формат** — PNG / JPEG / WebP с настройкой качества
- 📁 **Сохранение пресетов** — быстрый доступ к любимым настройкам

### Скриншот

<p align="center">
  <i>(Скриншот приложения)</i>
</p>

### Установка

**Вариант 1 — Готовый .exe (рекомендуется):**
1. Скачай последний релиз из [Releases](https://github.com/cyperxyk-lang/CyperMark/releases)
2. Запусти `CyperMark_v2.exe` — установка не требуется

**Вариант 2 — Из исходников:**
```bash
git clone https://github.com/cyperxyk-lang/CyperMark.git
cd CyperMark
pip install -r requirements.txt
python main_v2.py
```

### Использование

1. Нажми **"📁 Добавить файлы"** или **"📂 Добавить папку"**
2. Выбери тип водяного знака: **Текст** или **Логотип**
3. Настрой внешний вид (шрифт, размер, цвет, прозрачность, поворот)
4. Выбери позицию или **"Замостить"**
5. Нажми **"🚀 ЗАПУСТИТЬ"** — готово!

### CLI режим

```bash
CyperMark.exe --cli -i ./photos -o ./output -t "© 2026"
```

---

## 🇬🇧 CyperMark (English)

**CyperMark** is a fast batch watermark tool for images. Built for AI artists, photographers, and content creators.

### Features

- ✏️ **Text Watermark** — full customization: 147+ fonts, color, stroke
- 🖼️ **Image Watermark** — PNG, JPG, WEBP, BMP, TIFF (alpha support)
- 📦 **Batch Processing** — 500 photos in 30 seconds
- 🎯 **AI Auto-Placement** — smart positioning in low-detail areas
- 🔄 **Tile Mode** — full-surface watermark with rotation
- 👁️ **Live Preview** — instant feedback on all changes
- 💾 **Output** — PNG / JPEG / WebP with quality control
- 📁 **Presets** — save/load your favorite configurations

### Quick Start

1. Download the latest `.exe` from [Releases](https://github.com/cyperxyk-lang/CyperMark/releases)
2. Run `CyperMark_v2.exe` — no installation required
3. Add images → configure watermark → click START

Or run from source:
```bash
pip install -r requirements.txt
python main_v2.py
```

---

## ☕ Support / Поддержка

If you find this tool useful, consider supporting the project:

<p align="center">
  <a href="https://dalink.to/doublehook">
    <img src="https://img.shields.io/badge/Donate-DonationAlerts-orange?style=for-the-badge&logo=alipay&logoColor=white"/>
  </a>
</p>

---

## 📄 License / Лицензия

MIT License — free for personal and commercial use.
