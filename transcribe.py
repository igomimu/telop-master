#!/usr/bin/env python3
"""
faster-whisperで動画を文字起こし → JSON出力

使い方:
  python transcribe.py input.mp4 -o transcript.json

出力: [{start, end, text}, ...] 形式のJSON
generate_ass.py の入力として使用する

依存: pip install faster-whisper
"""
import json
import argparse
import time


def transcribe(video_path, output_path, model_name="small", device="cpu"):
    from faster_whisper import WhisperModel

    print(f"Loading model: {model_name} (device={device})")
    model = WhisperModel(model_name, device=device, compute_type="int8")

    print(f"Transcribing: {video_path}")
    start_time = time.time()

    segments, info = model.transcribe(
        video_path,
        language="ja",
        word_timestamps=True,
        vad_filter=True,
    )

    result = []
    for seg in segments:
        result.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })

    elapsed = time.time() - start_time
    print(f"Done: {len(result)} segments in {elapsed:.0f}s")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='faster-whisperで動画を文字起こし → JSON出力'
    )
    parser.add_argument('video', help='入力動画ファイル')
    parser.add_argument('-o', '--output', default='/tmp/whisper_transcript.json',
                        help='出力JSONファイルパス')
    parser.add_argument('-m', '--model', default='small',
                        help='Whisperモデル (tiny/base/small/medium/large)')
    parser.add_argument('-d', '--device', default='cpu',
                        help='デバイス (cpu/cuda)')
    args = parser.parse_args()

    transcribe(args.video, args.output, args.model, args.device)


if __name__ == '__main__':
    main()
