#!/usr/bin/env python3
"""補正済みtranscript(JSON) → YouTube用タイトル案・概要欄・章立てを自動生成

使い方:
  python generate_metadata.py refined.json -o metadata.json

入力: generate_ass.py --save-refined-json で保存した [{start, end, text}, ...]
出力: metadata.json（構造化データ）+ metadata.txt（概要欄にそのまま貼れる本文）
"""
import argparse
import json
from pathlib import Path

import llm_gemini

METADATA_SYSTEM_PROMPT = """\
あなたは囲碁講座YouTubeチャンネルの編集者です。
動画の文字起こしから、タイトル案・概要欄・章立てを作成してください。

## ルール
1. タイトルは5案、60文字以内。棋士名・手筋名・棋戦名など検索されやすいキーワードを含める
2. 概要欄は導入文（2〜3文）+ 関連ハッシュタグ（囲碁関連、3〜5個）
3. 章立て（チャプター）は必ず 0:00 から始める。最低3個、各チャプターは15秒以上離す
4. 章立てのラベルは内容が一目でわかる短い日本語（例: "裂かれ形とは" "実戦での回避法"）
5. 文字起こしに無い内容を作らない（推測で盛らない）
"""

METADATA_SCHEMA = {
    "type": "object",
    "properties": {
        "titles": {"type": "array", "items": {"type": "string"}, "minItems": 5, "maxItems": 5},
        "description": {"type": "string"},
        "chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "time": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["time", "label"],
            },
        },
    },
    "required": ["titles", "description", "chapters"],
}


def generate_metadata(transcript: list) -> dict:
    """transcript: [{start, end, text}, ...] → {titles, description, chapters}"""
    full_text = "\n".join(f"[{seg['start']:.0f}s] {seg['text']}" for seg in transcript)
    duration = transcript[-1]['end'] if transcript else 0

    messages = [
        {"role": "system", "content": METADATA_SYSTEM_PROMPT},
        {"role": "user", "content": f"動画の長さ: {duration:.0f}秒\n\n文字起こし全文:\n{full_text}"},
    ]
    result = llm_gemini.chat(messages, temperature=0.4, response_json_schema=METADATA_SCHEMA)
    if not result:
        print("Warning: メタデータ生成失敗（Gemini利用不可）")
        return {"titles": [], "description": "", "chapters": []}
    return json.loads(result)


def format_metadata_txt(metadata: dict) -> str:
    """YouTube概要欄にそのまま貼れるテキストを組み立てる"""
    lines = [metadata.get("description", ""), ""]
    for ch in metadata.get("chapters", []):
        lines.append(f"{ch['time']} {ch['label']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="補正済みtranscriptからYouTubeメタデータを自動生成")
    parser.add_argument("transcript", help="generate_ass.py --save-refined-json の出力JSON")
    parser.add_argument("-o", "--output", default="/tmp/metadata.json", help="出力JSONパス")
    args = parser.parse_args()

    with open(args.transcript, encoding="utf-8") as f:
        transcript = json.load(f)

    metadata = generate_metadata(transcript)

    output_path = Path(args.output)
    output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    txt_path = output_path.with_suffix(".txt")
    txt_path.write_text(format_metadata_txt(metadata), encoding="utf-8")

    print(f"Generated: {output_path}")
    print(f"Generated: {txt_path}")
    print()
    print("## タイトル案")
    for t in metadata.get("titles", []):
        print(f"  - {t}")


if __name__ == "__main__":
    main()
