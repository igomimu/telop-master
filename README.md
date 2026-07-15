# Telop Master

動画テロップ生成ツール群。囲碁動画制作の効率化パイプライン（収録後の仕上げ工程）。

## 全体ワークフロー

```
録画(OBS) → 無音カット(auto-editor, LEGION) → Camtasiaで仕上げ編集 → 文字起こし+テロップ(LEGION) → BGM/サムネ/概要欄
```

## カット編集: auto-editor で無音区間を自動カット

Camtasia 2019には無音自動削除機能が無い（TechSmithの Remove Silence は Camtasia Audiate との連携機能で、2022年以降のバージョン向け）。代わりに無料OSSツール [auto-editor](https://auto-editor.com/) を使う。

```bash
pip install --user --break-system-packages auto-editor  # 導入済みならスキップ

./cut_silence.sh raw_recording.mp4 cut.mp4
```

`cut_silence.sh` は囲碁解説向けに `--margin 1.5sec` をデフォルトにしている。auto-editorの `--margin` は「loud区間の近くのLENGTH未満の無音はloudとみなす」仕様なので、1.5秒未満の無音（次の一手を考える間など）は自動的に残り、それより長い無音だけがカットされる。

生録画に対してCamtasiaで編集する**前**にかける。Camtasia側でタイムラインをいじった後だとカット区間がズレやすいため。

## ツール一覧

### 1. 自動字幕生成パイプライン

動画音声 → Whisper文字起こし → LLM補正(Gemini/Ollama) → 囲碁用語修正 → ASS縦書き字幕 → ffmpeg焼き込み

```bash
# Step 1: 文字起こし
python transcribe.py input.mp4 -o transcript.json

# Step 2: ASS字幕生成（Gemini補正がデフォルト。--save-refined-json で横書きJSONも保存）
python generate_ass.py transcript.json -o telops.ass -t "石の形講座" \
  --llm-backend gemini --save-refined-json refined.json

# Step 3: プレビュー（30秒）
ffmpeg -y -ss 0 -t 30 -i input.mp4 -vf "ass=telops.ass" \
  -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k preview.mp4

# Step 4: 本番エンコード
ffmpeg -y -i input.mp4 -vf "ass=telops.ass" \
  -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 192k output.mp4
```

#### LLM補正バックエンド

`--llm-backend gemini|ollama|none`（デフォルト: `gemini`）

- **gemini**（デフォルト）: `~/.secrets/gemini.env` のAPIキー（Google AI Pro無料枠、従量課金なし）を使用。棋士名・専門用語の文脈補正力が高い。利用不可・失敗時は自動で Ollama にフォールバックする（`--ollama-host` 指定時）
- **ollama**: ローカルの Ollama（Nemotron-Nano-9B）のみで補正。Geminiが使えない環境向け
- **none**: LLM補正なし、辞書ルールのみ（旧 `--no-llm` と同義）

無料枠のレート制限対策として、Geminiバッチ間に `--gemini-sleep`(デフォルト7秒)の待機を入れている。長尺動画では `--batch-size` を20〜30程度に増やすと1バッチあたりの辞書送信コストを償却できる。

#### 依存

```bash
pip install faster-whisper google-genai
```

#### 囲碁用語修正

`generate_ass.py` 内の2つの辞書で Whisper の誤認識を修正:

- **GO_CORRECTIONS** / **GO_CORRECTIONS_AUTO**: 固定置換（例: 視聴→シチョウ、異号→囲碁）
- **GO_VERB_RULES**: 正規表現ベースの活用形変換（例: 切り→キリ、繋が→ツナが）

LLM補正の後に適用される最後の砦。新しい動画で誤認識を見つけたら辞書に追加していく。

### 2. メタデータ生成 (`generate_metadata.py`)

`--save-refined-json` で保存した横書きtranscriptから、YouTube用のタイトル案・概要欄・章立てをGeminiで自動生成する。

```bash
python generate_metadata.py refined.json -o metadata.json
cat metadata.txt  # 概要欄にそのまま貼れる本文+チャプター
```

### 3. サムネイル生成 (`generate_thumbnail.py`)

動画から碁盤フレームを切り出し、棋士名・テーマ文言を合成する。

```bash
ffmpeg -y -ss 00:08:42 -i input.mp4 -frames:v 1 -q:v 2 frame.png
python generate_thumbnail.py frame.png -o thumbnail.jpg --kishi "三村智保九段" --theme "裂かれ形の急所"
```

### 4. BGM自動ミックス (`mix_bgm.py`)

```bash
python mix_bgm.py with_telops.mp4 ~/bgm/sample.mp3 -o with_bgm.mp4 --bgm-volume -20 [--duck]
```

`--duck` でナレーション時にBGM音量を自動で下げる（sidechaincompress）。

### 5. テロップ画像生成 (`text_generator.py`)

白フチ＋赤/黒文字のPNG画像を生成（旧方式、`generate_thumbnail.py`のテキスト合成ロジックの元ネタ）。

```bash
./gen_text.sh
```

## examples/

実際の生成例（石の形講座 裂かれ形）:
- `whisper_transcript.json` — Whisper文字起こし結果
- `telops.ass` — 生成されたASS字幕
