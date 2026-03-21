#!/usr/bin/env python3
"""
Whisper文字起こし → Ollama LLM補正 → 囲碁用語修正 → ASS縦書き字幕生成

使い方:
  python generate_ass.py transcript.json -o output.ass

  # LLM補正なし（高速、辞書ルールのみ）
  python generate_ass.py transcript.json -o output.ass --no-llm

  # Ollamaホスト指定
  python generate_ass.py transcript.json -o output.ass --ollama-host http://localhost:11434

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
import csv
import argparse
import sys
from pathlib import Path

# --- 囲碁用語修正辞書（ルールベース、LLM前後どちらでも効く） ---

# 固定文字列置換（Whisperの誤認識を修正）
# 順序: 長いフレーズ→短い語。dictなので重複キー注意
GO_CORRECTIONS = {
    # --- 長い文脈依存フレーズ（先にマッチさせたい） ---
    '柴野一力、柴野一力': '芝野、一力。芝野、一力',
    '賞金の高い規制と低い規制': '賞金の高い棋戦と低い棋戦',
    '規制が一番大きくて': '棋聖が一番大きくて',
    # --- 棋士名（辞書 or 三村さん確認済み） ---
    '三村智康': '三村智保',
    'みむらくだん': '三村九段',
    'みむらともやす': '三村智保',
    '藤沢里奈': '藤沢里菜',
    '上野浅見': '上野愛咲美',
    '龍志くんさん': '柳時熏さん',
    '龍志くん': '柳時熏',
    '長知くん': '趙治勲',
    '超奥団': '趙治勲',
    '大立成': '王立誠',
    '関山穂野歌': '関山穂香',
    '甲原野の': '香原野乃',
    '本田光彦': '本田満彦',
    '後藤真奈': '五藤眞奈',
    '張千恵': '張心治',
    '柴野': '芝野',
    # --- 囲碁用語（確認済み） ---
    '三村文化': '三村門下',
    'ホミボー戦': '本因坊戦',
    '名人リグ': '名人リーグ',
    '規制戦': '棋聖戦',
    '日本金': '日本棋院',
    '関西金': '関西棋院',
    '指導後': '指導碁',
    '球場中': '休場中',
    '早子': '早碁',
    '異号': '囲碁',
    '以後': '囲碁',
    '視聴': 'シチョウ',
    # --- 段位 ---
    '初弾': '初段',
    '2弾': '二段',
    '3弾': '三段',
    '4弾': '四段',
    '5弾': '五段',
    '6弾': '六段',
    '7弾': '七段',
    '8弾': '八段',
    '9弾': '九段',
    # --- 一般 ---
    '騎士': '棋士',
    '入団': '入段',
    '彼これ': 'かれこれ',
    '字は': '地は',
    '特になりません': '得になりません',
    'うへん': '右辺',
    'かへん': '下辺',
    # --- 裂かれ形 ---
    '逆れがたち': '裂かれ形',
    '逆れが立ち': '裂かれ形',
    '裂かたち': '裂かれ形',
    '逆れ形': '裂かれ形',
    '盛れ形': '裂かれ形',
    '逆れ': '裂かれ',
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

# --- 辞書ロード ---

def load_kishi_dictionary() -> str:
    """棋士名辞書（491人）"""
    kishi_path = Path.home() / "projects" / "kishi-data" / "kishi_dictionary_final.txt"
    if not kishi_path.exists():
        return ""
    lines = []
    with open(kishi_path, "r", encoding="utf-8") as f:
        for line in f:
            cols = line.strip().split("\t")
            if len(cols) >= 2:
                lines.append(f"{cols[0]} → {cols[1]}")
    return "\n".join(lines)


def load_go_terms() -> str:
    """囲碁用語辞書（601語）"""
    master_path = Path.home() / "projects" / "go-dictionary-registration" / "data" / "master.csv"
    if not master_path.exists():
        return ""
    lines = []
    with open(master_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = row.get("term_ja", "")
            reading = row.get("reading_ja", "")
            cat = row.get("category", "")
            if term and reading:
                lines.append(f"{reading} → {term}（{cat}）")
            elif term:
                lines.append(f"{term}（{cat}）")
    return "\n".join(lines)

# --- Ollama LLM補正 ---

OLLAMA_SYSTEM_PROMPT = """\
囲碁の字幕校正者です。音声認識（Whisper）で生成された日本語テキストの誤変換を修正してください。

## ルール
1. 棋士名辞書にある名前は正確な漢字表記に修正する
2. 囲碁用語は正しい表記に修正する
3. 「騎士」→「棋士」「入団」→「入段」「規制戦」→「棋聖戦」「金」→「棋院」など音声認識特有の誤変換を修正する
4. 段位表記を統一する（初段、二段、三段...九段。「初弾」「2弾」等は段位に修正）
5. 文章の意味は変えない。修正が不要なら原文をそのまま返す
6. 修正結果のテキストのみ出力する（説明や注釈は不要）

## 棋士名辞書（読み → 正確な漢字表記）
{kishi_dictionary}

## 囲碁用語辞書
{go_terms}
"""

OLLAMA_MODEL = "qwen2.5:7b"


def refine_with_ollama(segments, ollama_host, batch_size=10):
    """Ollama LLMでWhisper出力を補正（バッチ処理）"""
    try:
        import requests
    except ImportError:
        print("Warning: requests not installed, skipping LLM refinement")
        return segments

    # 辞書ロード
    kishi_dict = load_kishi_dictionary()
    go_terms = load_go_terms()

    if not kishi_dict and not go_terms:
        print("Warning: 辞書が見つかりません、LLM補正をスキップ")
        return segments

    system_prompt = OLLAMA_SYSTEM_PROMPT.format(
        kishi_dictionary=kishi_dict,
        go_terms=go_terms,
    )
    print(f"LLM補正: 棋士{len(kishi_dict.splitlines())}人 + 囲碁用語{len(go_terms.splitlines())}語")

    # Ollama接続テスト
    try:
        r = requests.get(f"{ollama_host}/api/tags", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"Warning: Ollama接続失敗 ({ollama_host}): {e}")
        return segments

    refined = []
    total = len(segments)

    for i in range(0, total, batch_size):
        batch = segments[i:i + batch_size]
        batch_texts = "\n".join(
            f"[{j+1}] {seg['text']}" for j, seg in enumerate(batch)
        )

        try:
            resp = requests.post(
                f"{ollama_host}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"以下の字幕テキストを修正してください:\n\n{batch_texts}"},
                    ],
                },
                timeout=120,
            )
            resp.raise_for_status()
            result = resp.json()["message"]["content"].strip()

            # [1] ... [2] ... 形式をパース
            corrected = parse_numbered_response(result, len(batch))

            for j, seg in enumerate(batch):
                new_seg = dict(seg)
                if j < len(corrected) and corrected[j]:
                    new_seg["text"] = corrected[j]
                refined.append(new_seg)

            progress = min(i + batch_size, total)
            print(f"  LLM補正: {progress}/{total} segments")

        except Exception as e:
            print(f"  Warning: LLM補正失敗 (batch {i//batch_size + 1}): {e}")
            refined.extend(batch)

    return refined


def parse_numbered_response(text, expected_count):
    """[1] ... [2] ... 形式のレスポンスをパース"""
    lines = text.strip().split("\n")
    results = {}

    for line in lines:
        line = line.strip()
        m = re.match(r'\[(\d+)\]\s*(.*)', line)
        if m:
            idx = int(m.group(1)) - 1
            results[idx] = m.group(2).strip()

    # 番号なしの場合（1行ずつ返ってきた場合）
    if not results and len(lines) == expected_count:
        return [l.strip() for l in lines]

    # 番号ありの場合
    return [results.get(i, "") for i in range(expected_count)]


# --- テキスト処理 ---

def correct_text(text):
    """囲碁用語の修正: 固定置換（長いキー優先） → 正規表現ベースの活用形変換"""
    for wrong in sorted(GO_CORRECTIONS.keys(), key=len, reverse=True):
        text = text.replace(wrong, GO_CORRECTIONS[wrong])
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
    """横書き→縦書き変換: 各文字を\\Nで区切る（数字・カタカナ考慮）"""
    vertical_map = {
        '（': '︵', '）': '︶',
        '「': '﹁', '」': '﹂',
        '、': '︑', '。': '︒',
        'ー': '︱', '—': '︱', '─': '︱',
        '？': '？', '！': '！',
        '・': '・',
    }

    # 数字（1〜2桁）を縦中横にまとめる
    # カタカナ連続はそのまま縦に並べる（個別文字で問題ない）
    chars = list(text)
    result = []
    i = 0
    while i < len(chars):
        ch = chars[i]
        # 半角数字2桁をまとめる
        if ch.isdigit() and i + 1 < len(chars) and chars[i + 1].isdigit():
            result.append(ch + chars[i + 1])
            i += 2
            continue
        # 全角数字2桁をまとめる
        if '\uff10' <= ch <= '\uff19' and i + 1 < len(chars) and '\uff10' <= chars[i + 1] <= '\uff19':
            result.append(ch + chars[i + 1])
            i += 2
            continue
        result.append(vertical_map.get(ch, ch))
        i += 1

    return '\\N'.join(result)


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
        description='Whisper文字起こし → LLM補正 → 囲碁用語修正 → ASS縦書き字幕生成'
    )
    parser.add_argument('transcript', help='Whisper JSON file ([{start, end, text}, ...])')
    parser.add_argument('-o', '--output', default='/tmp/telops.ass', help='出力ASSファイルパス')
    parser.add_argument('-t', '--title', default='囲碁講座', help='字幕タイトル')
    parser.add_argument('--no-llm', action='store_true', help='LLM補正をスキップ（辞書ルールのみ）')
    parser.add_argument('--ollama-host', default='http://localhost:11434', help='Ollamaホスト')
    parser.add_argument('--batch-size', type=int, default=10, help='LLMバッチサイズ')
    args = parser.parse_args()

    with open(args.transcript) as f:
        transcript = json.load(f)

    print(f"Transcript: {len(transcript)} segments")

    # LLM補正（Ollama）
    if not args.no_llm:
        transcript = refine_with_ollama(transcript, args.ollama_host, args.batch_size)

    # ASS生成（ルールベース修正 + 縦書き変換）
    generate_ass(transcript, args.output, args.title)


if __name__ == '__main__':
    main()
