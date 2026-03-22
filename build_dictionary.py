#!/usr/bin/env python3
"""
囲碁用語辞書の自動構築: master.csv全語をTTS→Whisper→誤変換パターン収集

使い方:
  python build_dictionary.py
  python build_dictionary.py --limit 50  # テスト用に50語だけ

出力:
  /tmp/whisper_errors.json — 誤変換パターン一覧
  /tmp/go_corrections_new.py — GO_CORRECTIONSに追加すべきルール
"""
import csv
import json
import asyncio
import tempfile
import argparse
import time
from pathlib import Path


async def generate_audio(text, output_path):
    """edge-ttsで日本語音声を生成"""
    import edge_tts
    communicate = edge_tts.Communicate(text, "ja-JP-NanamiNeural")
    await communicate.save(output_path)


def transcribe_audio(model, audio_path):
    """Whisperで文字起こし"""
    segments, _ = model.transcribe(
        audio_path,
        language="ja",
        beam_size=5,
        vad_filter=True,
    )
    return "".join(seg.text.strip() for seg in segments)


async def main():
    parser = argparse.ArgumentParser(description='囲碁用語Whisper誤変換パターン自動収集')
    parser.add_argument('--limit', type=int, default=0, help='処理する語数の上限（0=全部）')
    parser.add_argument('--model', default='large-v3', help='Whisperモデル')
    parser.add_argument('--device', default='cuda', help='デバイス')
    args = parser.parse_args()

    # master.csv読み込み
    master_path = Path.home() / "projects" / "go-dictionary-registration" / "data" / "master.csv"
    terms = []
    with open(master_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term = row.get("term_ja", "").strip()
            reading = row.get("reading_ja", "").strip()
            category = row.get("category", "").strip()
            if term:
                terms.append({"term": term, "reading": reading, "category": category})

    if args.limit > 0:
        terms = terms[:args.limit]

    print(f"対象: {len(terms)}語")

    # Whisperモデルロード
    from faster_whisper import WhisperModel
    compute_type = "float16" if args.device == "cuda" else "int8"
    print(f"Whisper {args.model} ({args.device}) ロード中...")
    model = WhisperModel(args.model, device=args.device, compute_type=compute_type)

    errors = []
    correct = 0
    total = len(terms)

    for i, entry in enumerate(terms):
        term = entry["term"]
        # 文脈付きの文で発話（単語だけだとWhisperが不安定）
        test_sentence = f"囲碁の{term}について解説します。"

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
            try:
                await generate_audio(test_sentence, tmp.name)
                result = transcribe_audio(model, tmp.name)

                # 正解チェック: resultにtermが含まれているか
                if term in result:
                    correct += 1
                else:
                    # 誤変換を抽出（"囲碁の" と "について" の間）
                    whisper_term = result
                    # 前後の定型文を除去して誤変換部分を特定
                    for prefix in ["囲碁の", "以後の", "異語の", "異号の"]:
                        if prefix in whisper_term:
                            whisper_term = whisper_term.split(prefix, 1)[-1]
                    for suffix in ["について解説します", "について解説します。", "について", "について。"]:
                        if suffix in whisper_term:
                            whisper_term = whisper_term.split(suffix)[0]

                    whisper_term = whisper_term.strip().rstrip("。、")

                    if whisper_term and whisper_term != term:
                        errors.append({
                            "term": term,
                            "reading": entry["reading"],
                            "category": entry["category"],
                            "whisper": whisper_term,
                            "full_result": result,
                        })

            except Exception as e:
                print(f"  Error [{term}]: {e}")

        if (i + 1) % 20 == 0 or i + 1 == total:
            print(f"  進捗: {i+1}/{total} (正解: {correct}, 誤変換: {len(errors)})")

    # 結果保存
    print(f"\n=== 結果 ===")
    print(f"正解: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"誤変換: {len(errors)}語")

    # JSON出力
    with open("/tmp/whisper_errors.json", "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    print(f"詳細: /tmp/whisper_errors.json")

    # GO_CORRECTIONS形式で出力
    if errors:
        with open("/tmp/go_corrections_new.py", "w", encoding="utf-8") as f:
            f.write("# Whisper誤変換パターン（自動収集）\n")
            f.write("# generate_ass.py の GO_CORRECTIONS に追加\n")
            f.write("GO_CORRECTIONS_NEW = {\n")
            for e in sorted(errors, key=lambda x: x["category"]):
                f.write(f"    '{e['whisper']}': '{e['term']}',  # {e['category']}\n")
            f.write("}\n")
        print(f"追加ルール: /tmp/go_corrections_new.py")


if __name__ == "__main__":
    asyncio.run(main())
