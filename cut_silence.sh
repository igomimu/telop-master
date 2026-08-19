#!/usr/bin/env bash
# 収録動画から「音も動きも無い区間」を自動カットする(auto-editor使用)
#
# 使い方:
#   ./cut_silence.sh input.mp4 [output.mp4]
#   ./cut_silence.sh -n input.mp4          # カット量を見るだけ(書き出さない)
#
# 囲碁解説向けの判定条件:
#   (or audio motion) : 音が無くても画面が動いていれば残す
#                       → 無音で碁盤に石を並べて手順を見せる区間が消えない
#   margin 1.5sec     : 音/動きの前後1.5秒は残す(「次の一手を考える間」の保護)
#
# 環境変数で調整可:
#   AUDIO_TH=0.04   音量のしきい値
#   MOTION_TH=0.02  画面変化のしきい値(下げるほど残りやすい)
#   MARGIN=1.5sec   前後に残す長さ
#
# 実測メモ(2026-08-19, auto-editor 29.3.1):
#   - 音のみ判定だと、無音で手順を見せる10秒が丸ごと消えた(30秒→13秒)
#     音+動きなら26.7秒残り、消えたのは本当の死に時間だけ
#   - 0.1秒(3フレーム)未満の音は無視される。碁石を置く「パチッ」だけを
#     頼りにすると拾われないことがある → 動き判定を併用する理由
#   - 画面に時計・検討ソフトのアニメ・マウス移動があると「動きあり」になり
#     カット量は減る(=安全側に外れる)
set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

DRY=0
if [[ "${1:-}" == "-n" || "${1:-}" == "--preview" ]]; then
  DRY=1; shift
fi

INPUT="${1:?使い方: ./cut_silence.sh [-n] input.mp4 [output.mp4]}"
OUTPUT="${2:-${INPUT%.*}_cut.${INPUT##*.}}"

AUDIO_TH="${AUDIO_TH:-0.04}"
MOTION_TH="${MOTION_TH:-0.02}"
MARGIN="${MARGIN:-1.5sec}"
EDIT="(or audio:threshold=${AUDIO_TH} motion:threshold=${MOTION_TH})"

[[ -f "$INPUT" ]] || { echo "入力が見つかりません: $INPUT" >&2; exit 1; }

echo "判定条件: ${EDIT} / margin=${MARGIN}"
echo "--- カット量の確認 ---"
auto-editor "$INPUT" --edit "$EDIT" --margin "$MARGIN" --preview

if [[ "$DRY" == "1" ]]; then
  echo "(-n 指定のため書き出しはしません)"
  exit 0
fi

if [[ -e "$OUTPUT" ]]; then
  echo "出力先が既にあります: $OUTPUT" >&2
  echo "別名を指定するか、先に退避してください(上書きはしません)" >&2
  exit 1
fi

echo "--- 書き出し: $OUTPUT ---"
auto-editor "$INPUT" --edit "$EDIT" --margin "$MARGIN" -o "$OUTPUT" --no-open

echo
echo "完了: $OUTPUT"
echo "※ カットは実データを切ります。元ファイル($INPUT)は消さずに残してください"
