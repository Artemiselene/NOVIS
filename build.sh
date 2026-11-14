#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
rm -f astra-mind-extension.zip
zip -r astra-mind-extension.zip . -x "*/node_modules/*" "*/.venv/*" "*/__pycache__/*" "astra-mind-extension.zip"
echo "Built astra-mind-extension.zip"
