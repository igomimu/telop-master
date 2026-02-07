#!/bin/bash
# Wrapper script for text_generator.py
# Usage: ./gen_text.sh "Your Text" [color] [--font font_path]

PY_PATH="/home/mimura/telop-master/.venv/bin/python"
SCRIPT_PATH="/home/mimura/telop-master/text_generator.py"

"$PY_PATH" "$SCRIPT_PATH" "$@"
