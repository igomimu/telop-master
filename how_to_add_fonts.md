# How to Add Custom Fonts for Video Assets

To use a different font (e.g., a bolder Mincho or a stylish Brush font) for your text assets:

## 1. Get the Font File
- Ensure you have the font file (usually `.ttf` or `.otf`).
- **Recommended Free Fonts:**
    - **Google Fonts**: [Noto Sans JP](https://fonts.google.com/noto/specimen/Noto+Sans+JP) (You already have this)
    - **Zen Kurenaido**: Great handwritten feel.
    - **Yuji Syuku**: Nice calligraphy style.

## 2. Install the Font (System-wide)
This makes the font available to all applications (Camtasia, OBS, etc.) and our script.

1.  Create the font directory if it doesn't exist:
    ```bash
    mkdir -p ~/.local/share/fonts
    ```
2.  Copy your font file into this directory:
    ```bash
    cp /path/to/your/font.ttf ~/.local/share/fonts/
    ```
3.  Update the font cache:
    ```bash
    fc-cache -fv
    ```

## 3. Use the Font with the Script
I have updated `text_generator.py` so you can specify a font directly without editing the code.

**Command:**
```bash
python3 text_generator.py "文字" red --font ~/.local/share/fonts/MyNewFont.ttf
```

## Useful Commands
- **List all Japanese fonts installed:**
    ```bash
    fc-list :lang=ja
    ```
