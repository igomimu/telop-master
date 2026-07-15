#!/usr/bin/env python3
"""動画にBGMを自動ミックス（ffmpegラッパー）

使い方:
  python mix_bgm.py with_telops.mp4 ~/bgm/sample.mp3 -o with_bgm.mp4 --bgm-volume -20
  python mix_bgm.py with_telops.mp4 ~/bgm/sample.mp3 -o with_bgm.mp4 --duck  # ナレーション時にBGMを自動減衰
"""
import argparse
import subprocess


def _probe_duration(video_path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def mix_bgm(
    video_path: str,
    bgm_path: str,
    output_path: str,
    bgm_volume_db: float = -20.0,
    duck: bool = False,
    fade_in_sec: float = 2.0,
    fade_out_sec: float = 3.0,
) -> None:
    duration = _probe_duration(video_path)
    fade_out_start = max(duration - fade_out_sec, 0)

    if duck:
        filter_complex = (
            f"[1:a]volume={bgm_volume_db + 6}dB[bgm_pre];"
            f"[bgm_pre][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=5:release=300[bgm_ducked];"
            f"[0:a][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=0,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )
    else:
        filter_complex = (
            f"[1:a]volume={bgm_volume_db}dB,"
            f"afade=t=in:d={fade_in_sec},afade=t=out:st={fade_out_start}:d={fade_out_sec}[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=0,"
            f"loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="動画にBGMを自動ミックス")
    parser.add_argument("video", help="入力動画")
    parser.add_argument("bgm", help="BGM音源ファイル")
    parser.add_argument("-o", "--output", default="/tmp/with_bgm.mp4", help="出力動画パス")
    parser.add_argument("--bgm-volume", type=float, default=-20.0, help="BGM音量(dB、負の値。既定-20dB)")
    parser.add_argument("--duck", action="store_true", help="ナレーション時にBGMを自動減衰(sidechaincompress)")
    parser.add_argument("--fade-in", type=float, default=2.0, help="フェードイン秒数")
    parser.add_argument("--fade-out", type=float, default=3.0, help="フェードアウト秒数")
    args = parser.parse_args()

    mix_bgm(
        args.video, args.bgm, args.output,
        bgm_volume_db=args.bgm_volume, duck=args.duck,
        fade_in_sec=args.fade_in, fade_out_sec=args.fade_out,
    )


if __name__ == "__main__":
    main()
