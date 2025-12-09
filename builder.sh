echo "VER = '$(date +%y%m%d.%H%M)'" >build_date.py
pyinstaller \
  --onefile \
  --name puncher-cli \
  --add-data "data/questionnaire.txt:data" \
  puncher_cli.py
