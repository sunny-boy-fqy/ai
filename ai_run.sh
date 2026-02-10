#!/bin/bash
CONFIG_DIR="$HOME/.config/ai"
BASE_DIR=$(cat "$CONFIG_DIR/base_path.config")
"$CONFIG_DIR/python_venv/bin/python3" "$BASE_DIR/ai_caller.py" "$@"
