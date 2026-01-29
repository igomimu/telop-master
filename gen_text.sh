#!/bin/bash
# Wrapper script for text_generator.py
# Usage: ./gen_text.sh "Your Text" [color] [--font font_path]

PY_PATH="/home/mimura/projects/comfy-ui/venv/bin/python3"
SCRIPT_PATH="/home/mimura/.gemini/antigravity/brain/30ad5ff4-f82e-4093-b89e-9610d6c7003e/text_generator.py"

"$PY_PATH" "$SCRIPT_PATH" "$@"
