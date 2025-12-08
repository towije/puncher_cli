python -m venv .venv
source .venv/bin/activate
pip install pyinstaller
pyinstaller \
  --onefile \
  --name puncher-cli \
  --add-data "data/questionnaire.txt:data" \
  puncher_cli.py