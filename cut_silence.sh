#!/usr/bin/env bash
# 無音区間を自動カットする(auto-editor使用)
#
# 使い方:
#   ./cut_silence.sh input.mp4 [output.mp4]
#
# 囲碁解説向けデフォルト:
#   --margin 1.5sec  : 1.5秒未満の無音は「音あり」とみなして残す
#                       (「次の一手を考える間」を誤って削らないため)
#   threshold=0.04    : auto-editorの既定音量閾値
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

INPUT="${1:?使い方: ./cut_silence.sh input.mp4 [output.mp4]}"
OUTPUT="${2:-${INPUT%.*}_cut.${INPUT##*.}}"

auto-editor "$INPUT" \
  --edit "audio:threshold=0.04" \
  --margin 1.5sec \
  -o "$OUTPUT"
