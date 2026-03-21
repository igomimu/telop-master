# Telop Master

動画テロップ生成ツール群。

## ツール一覧

### 1. 自動字幕生成パイプライン

動画音声 → Whisper文字起こし → 囲碁用語修正 → ASS縦書き字幕 → ffmpeg焼き込み

```bash
# Step 1: 文字起こし
python transcribe.py input.mp4 -o transcript.json

# Step 2: ASS字幕生成（囲碁用語を自動修正）
python generate_ass.py transcript.json -o telops.ass -t "石の形講座"

# Step 3: プレビュー（30秒）
ffmpeg -y -ss 0 -t 30 -i input.mp4 -vf "ass=telops.ass" \
  -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k preview.mp4

# Step 4: 本番エンコード
ffmpeg -y -i input.mp4 -vf "ass=telops.ass" \
  -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k output.mp4
```

#### 依存

```bash
pip install faster-whisper
```

#### 囲碁用語修正

`generate_ass.py` 内の2つの辞書で Whisper の誤認識を修正:

- **GO_CORRECTIONS**: 固定置換（例: 視聴→シチョウ、異号→囲碁）
- **GO_VERB_RULES**: 正規表現ベースの活用形変換（例: 切り→キリ、繋が→ツナが）

新しい動画で誤認識を見つけたら辞書に追加していく。

### 2. テロップ画像生成 (`text_generator.py`)

白フチ＋赤/黒文字のPNG画像を生成。

```bash
./gen_text.sh
```

### 3. ASS字幕生成 (`generate_ass.py`)（旧方式: テロップリストマッチング）

※ 現在は Whisper 直接字幕方式に移行済み。

## examples/

実際の生成例（石の形講座 裂かれ形）:
- `whisper_transcript.json` — Whisper文字起こし結果
- `telops.ass` — 生成されたASS字幕
