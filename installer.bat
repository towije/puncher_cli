python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller windows-curses
pyinstaller --onefile --name puncher-cli --add-data "data\\questionnaire.txt;data" puncher_cli.py