# Telop Master (Video Asset Generator)

動画編集用の高品質な文字アセット（テロップ）を生成するツール群です。

## 含まれるツール

### 1. 文字作成ツール (`text_generator.py`)
指定したテキストを「白フチ＋赤文字（または黒文字）」の画像（PNG）として生成します。
生成された画像は、Windowsのデスクトップにある `Ichigo_Assets` フォルダに自動保存されます。

**使い方 (Windows側):**
デスクトップのショートカット `文字作成ツール.bat` をダブルクリックして起動します。

**使い方 (Linux側):**
```bash
./gen_text.sh
```

### 2. フォント追加ガイド (`how_to_add_fonts.md`)
新しいフォントを追加する方法を記載しています。

## 構成
- `text_generator.py`: 本体スクリプト（Python）
- `gen_text.sh`: 実行用ラッパースクリプト
- `how_to_add_fonts.md`: ドキュメント
