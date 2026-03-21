#!/usr/bin/env python3
"""
Whisper文字起こし → 囲碁用語修正 → ASS縦書き字幕生成

使い方:
  python generate_ass.py transcript.json -o output.ass

入力: faster-whisperで生成したJSON ([{start, end, text}, ...])
出力: ASS字幕ファイル（縦書き、左端、半透明暗背景）

ffmpegで焼き込み:
  # プレビュー（30秒）
  ffmpeg -y -ss 0 -t 30 -i input.mp4 -vf "ass=output.ass" \
    -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k preview.mp4

  # 本番エンコード
  ffmpeg -y -i input.mp4 -vf "ass=output.ass" \
    -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k output.mp4
"""
import json
import re
import argparse

# --- 囲碁用語修正辞書 ---

# 固定文字列置換（Whisperの誤認識を修正）
GO_CORRECTIONS = {
    # 名前
    'みむらくだん': '三村九段',
    'みむらともやす': '三村智保',
    # 一般
    '異号': '囲碁',
    '以後': '囲碁',
    '彼これ': 'かれこれ',
    '字は': '地は',
    '特になりません': '得になりません',
    # 裂かれ形
    '逆れ': '裂かれ',
    '裂かたち': '裂かれ形',
    '逆れがたち': '裂かれ形',
    '逆れが立ち': '裂かれ形',
    '逆れ形': '裂かれ形',
    '盛れ形': '裂かれ形',
    'うへん': '右辺',
    'かへん': '下辺',
    '視聴': 'シチョウ',
}

# 正規表現ベースの活用形変換（囲碁用語をカタカナ統一）
GO_VERB_RULES = [
    # カケツギ系
    (r'かけ継ぎ', 'カケツギ'),
    (r'かけつぎ', 'カケツギ'),
    (r'かけつ([ぐがぎげご])', r'カケツ\1'),
    # ツナギ系
    (r'繋が', 'ツナが'),
    (r'繋ぎ', 'ツナギ'),
    (r'繋い', 'ツナい'),
    (r'つなが', 'ツナが'),
    (r'つなぎ', 'ツナギ'),
    (r'つない', 'ツナい'),
    (r'つなげ', 'ツナげ'),
    (r'つなぐ', 'ツナぐ'),
    # ノゾキ系
    (r'覗き', 'ノゾキ'),
    (r'覗い', 'ノゾい'),
    (r'覗く', 'ノゾく'),
    (r'のぞき', 'ノゾキ'),
    (r'のぞい', 'ノゾい'),
    (r'のぞく', 'ノゾく'),
    # オサエ系
    (r'抑え', 'オサエ'),
    (r'おさえ', 'オサエ'),
    # アタリ系
    (r'当たり', 'アタリ'),
    (r'あたり', 'アタリ'),
    # ハネ系
    (r'跳ね', 'ハネ'),
    (r'はね', 'ハネ'),
    # ノビ系
    (r'伸び', 'ノビ'),
    (r'のび', 'ノビ'),
    # キリ系
    (r'切り', 'キリ'),
    (r'切る', 'キる'),
    (r'切れ', 'キれ'),
    (r'切っ', 'キッ'),
    (r'切ら', 'キら'),
    (r'きり', 'キリ'),
    # ワタリ系
    (r'渡り', 'ワタリ'),
    (r'渡る', 'ワタる'),
    (r'わたり', 'ワタリ'),
    # サガリ系
    (r'下がり', 'サガリ'),
    (r'下がる', 'サガる'),
    (r'さがり', 'サガリ'),
    # ツケ系
    (r'つけ', 'ツケ'),
    # マガリ系
    (r'曲が', 'マガ'),
    (r'まが', 'マガ'),
    # カカリ系
    (r'かかり', 'カカリ'),
    # ケイマ
    (r'けいま', 'ケイマ'),
    # ウチコミ系
    (r'うちこみ', 'ウチコミ'),
    (r'打ち込み', 'ウチコミ'),
    (r'打ち込[むんめ]', lambda m: 'ウチコ' + m.group(0)[-1]),
    # ワリコミ系
    (r'わりこみ', 'ワリコミ'),
    (r'割り込み', 'ワリコミ'),
    # ヌキ系
    (r'抜き', 'ヌキ'),
    (r'抜い', 'ヌい'),
    (r'抜く', 'ヌく'),
    (r'抜け', 'ヌけ'),
]

# --- ASS字幕テンプレート ---

# BorderStyle 3 = opaque box background
# Alignment 7 = top-left
# BackColour alpha: 80 (hex) = 50% transparent
ASS_HEADER = """\ufeff[Script Info]
Title: {title}
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Tategaki,IPAGothic,38,&H00FFFFFF,&H000000FF,&H00000000,&H80384030,-1,0,0,0,100,100,8,0,3,2,0,7,25,0,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# --- 関数 ---

def correct_text(text):
    """囲碁用語の修正: 固定置換 → 正規表現ベースの活用形変換"""
    for wrong, right in GO_CORRECTIONS.items():
        text = text.replace(wrong, right)
    for pattern, repl in GO_VERB_RULES:
        if callable(repl):
            text = re.sub(pattern, repl, text)
        else:
            text = re.sub(pattern, repl, text)
    return text


def time_to_ass(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def to_vertical(text):
    """横書き→縦書き変換: 各文字を\\Nで区切る"""
    vertical_map = {
        '（': '︵', '）': '︶',
        '「': '﹁', '」': '﹂',
        '、': '︑', '。': '︒',
        'ー': '︱', '—': '︱', '─': '︱',
        '？': '？', '！': '！',
        '・': '・',
    }
    return '\\N'.join(vertical_map.get(ch, ch) for ch in text)


def generate_ass(transcript, output_path, title="囲碁講座"):
    """Whisper JSONからASS字幕ファイルを生成"""
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write(ASS_HEADER.format(title=title))
        count = 0
        for seg in transcript:
            text = correct_text(seg['text'].strip())
            if not text:
                continue
            vtext = to_vertical(text)
            f.write(f"Dialogue: 0,{time_to_ass(seg['start'])},{time_to_ass(seg['end'])},Tategaki,,0,0,0,,{vtext}\n")
            count += 1
    print(f"Generated: {output_path} ({count} entries)")


def main():
    parser = argparse.ArgumentParser(
        description='Whisper文字起こし → 囲碁用語修正 → ASS縦書き字幕生成'
    )
    parser.add_argument('transcript', help='Whisper JSON file ([{start, end, text}, ...])')
    parser.add_argument('-o', '--output', default='/tmp/telops.ass', help='出力ASSファイルパス')
    parser.add_argument('-t', '--title', default='囲碁講座', help='字幕タイトル')
    args = parser.parse_args()

    with open(args.transcript) as f:
        transcript = json.load(f)

    print(f"Transcript: {len(transcript)} segments")
    generate_ass(transcript, args.output, args.title)


if __name__ == '__main__':
    main()
