#!/bin/zsh

echo "VER = '$(date +%y%m%d.%H%M)'" >build_date.py
pyinstaller \
  --onefile \
  --name puncher-cli \
  --add-data "data/questionnaire.pdi:data" \
  puncher_cli.py

mkdir -p dist/data
cp data/questionnaire.pdi dist/data/questionnaire.pdi
