#!/usr/bin/env python3
"""碁盤フレーム画像 + 棋士名/テーマ文言 → YouTubeサムネイル(1280x720 JPEG)

碁盤画像は動画からffmpegで切り出した静止画を想定する（実際に配信で映った盤面をそのまま使う）。

使い方:
  ffmpeg -y -ss 00:08:42 -i input.mp4 -frames:v 1 -q:v 2 frame.png
  python generate_thumbnail.py frame.png -o thumbnail.jpg --kishi "三村智保九段" --theme "裂かれ形の急所"
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

THUMB_SIZE = (1280, 720)

# text_generator.py と同じフォント選定（Noto Sans CJK JPを優先、無ければmsgothicにフォールバック）
FONT_CANDIDATES = [
    "/home/mimura/.local/share/fonts/NotoSansCJKjp-Bold.otf",
    "/mnt/c/Windows/Fonts/msgothic.ttc",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_outlined_text(draw, xy, text, font, fill, outline_fill, outline_width):
    draw.text(xy, text, font=font, fill=outline_fill, stroke_width=outline_width, stroke_fill=outline_fill)
    draw.text(xy, text, font=font, fill=fill, stroke_width=outline_width // 3, stroke_fill=fill)


def compose_thumbnail(
    board_image_path: str,
    output_path: str,
    kishi_name: str = "",
    theme_text: str = "",
) -> None:
    """碁盤画像を1280x720にフィットさせ、下部に棋士名・テーマ文言を合成してJPEG出力"""
    board = Image.open(board_image_path).convert("RGB")

    # 縦横比を保ってTHUMB_SIZEを覆うようにリサイズ→中央クロップ
    src_ratio = board.width / board.height
    dst_ratio = THUMB_SIZE[0] / THUMB_SIZE[1]
    if src_ratio > dst_ratio:
        new_h = THUMB_SIZE[1]
        new_w = int(new_h * src_ratio)
    else:
        new_w = THUMB_SIZE[0]
        new_h = int(new_w / src_ratio)
    board = board.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - THUMB_SIZE[0]) // 2
    top = (new_h - THUMB_SIZE[1]) // 2
    canvas = board.crop((left, top, left + THUMB_SIZE[0], top + THUMB_SIZE[1])).convert("RGBA")

    draw = ImageDraw.Draw(canvas)

    if theme_text:
        theme_font = _load_font(90)
        _draw_outlined_text(
            draw, (50, THUMB_SIZE[1] - 220), theme_text,
            font=theme_font, fill=(255, 240, 0, 255), outline_fill=(0, 0, 0, 255), outline_width=14,
        )

    if kishi_name:
        kishi_font = _load_font(48)
        _draw_outlined_text(
            draw, (50, THUMB_SIZE[1] - 90), kishi_name,
            font=kishi_font, fill=(255, 255, 255, 255), outline_fill=(0, 0, 0, 255), outline_width=8,
        )

    canvas.convert("RGB").save(output_path, "JPEG", quality=90)
    print(f"Generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="碁盤フレームからYouTubeサムネイルを生成")
    parser.add_argument("board_image", help="碁盤の静止画（ffmpegで切り出したフレーム等）")
    parser.add_argument("-o", "--output", default="/tmp/thumbnail.jpg", help="出力JPEGパス")
    parser.add_argument("--kishi", default="", help="棋士名（例: 三村智保九段）")
    parser.add_argument("--theme", default="", help="テーマ文言（例: 裂かれ形の急所）")
    args = parser.parse_args()

    compose_thumbnail(args.board_image, args.output, kishi_name=args.kishi, theme_text=args.theme)


if __name__ == "__main__":
    main()
