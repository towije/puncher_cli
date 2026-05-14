```
██████╗ ██╗   ██╗███╗   ██╗ ██████╗██╗  ██╗███████╗██████╗      
██╔══██╗██║   ██║████╗  ██║██╔════╝██║  ██║██╔════╝██╔══██╗     
██████╔╝██║   ██║██╔██╗ ██║██║     ███████║█████╗  ██████╔╝     
██╔═══╝ ██║   ██║██║╚██╗██║██║     ██╔══██║██╔══╝  ██╔══██╗     
██║     ╚██████╔╝██║ ╚████║╚██████╗██║  ██║███████╗██║  ██║     
╚═╝      ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝     
```

Terminal-based questionnaire data entry tool

# puncher-cli

**puncher-cli** is a terminal-based data entry system for paper questionnaires.
It supports multi-page instruments, conditional logic, numeric range validation, auto-jumps, and CSV output — all in a fast curses-based UI.

---

## ✨ Features

- **Multi-page data entry**, matching the layout of paper questionnaires  
- **Numeric validation** via `accept=` (ranges, lists: e.g., `1:5,8,12:17`)  
- **Conditional activation** of questions using `if=` expressions  
- **Auto-jump**: moves to the next field based on fixed-width rules and range interpretability  
- **Text questions** with free-text entry  
- **Missing-value entry** (e.g. `-`)  
- **Automatic CSV export** (`data/responses.csv`)  
- **Cross-platform:** macOS, Linux, Windows (with `windows-curses`)  

---

## 📁 Project structure

```
puncher-cli/
├── puncher_cli.py         # main program (UI + logic)
├── README.md
├── requirements.txt
└── data/
    └── questionnaire.txt  # instrument definition
```

`responses.csv` is generated automatically when the first interview is saved.

---

## 🚀 Quick start (developer mode)

### 1. Clone the repository

```bash
git clone https://github.com/towije/puncher-cli.git
cd puncher-cli
```

### 2. Create and activate a virtual environment

macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell)

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

Windows only

```bash
pip install -r requirements.txt
```

(On Windows this installs windows-curses, enabling curses support.)

---

## ▶️ Run the program

```bash
python puncher_cli.py
```
---

## 📄 Instrument definition: questionnaire.txt

Example:

```ini
[P246]
varlab=In the past year, did your family...
accept=1:4,8

hr
# or, for legacy .ini compatibility:
hr=1

[P247]
varlab=To which social class would you say you belong?
accept=1:5

page
# or, for legacy .ini compatibility:
page=1
```

Supported tokens:
- `varlab=` — question text
- `accept=` — numeric validation (ranges, lists)
- `text=` — open-ended text question
- `if=` — activation condition (`p1=1`, `p1=1 & p2!=3`, etc.)
- `hr`, `hr=1` — horizontal divider
- `page`, `page=1` — explicit page break

---

## 💾 Output: CSV

Responses are saved in:

`data/responses.csv`

Example CSV:

```csv
interview_id,p246,p247,p248,...
1,3,1,7,...
2,4,2,9,...
```

Each row represents one completed interview.

---

## ⚠️ Terminal requirements

`puncher-cli` uses curses and requires:
- minimum width: 80 columns
- recommended: full-screen terminal

If the terminal is too small, the program will show a message and pause until the window is resized.

---

## 💻 Building standalone binaries (optional)

macOS / Linux

```bash
pip install pyinstaller
pyinstaller --onefile \
  --name puncher-cli \
  --add-data "data/questionnaire.txt:data" \
  puncher_cli.py
```

Windows

```bash
pip install pyinstaller windows-curses
pyinstaller --onefile `
  --name puncher-cli `
  --add-data "data\\questionnaire.txt;data" `
  puncher_cli.py
```

Output binaries appear in `dist/`.

---

## 🧪 Development notes
- The entire application logic and UI are in puncher_cli.py.
- questionnaire.txt can be modified without touching code.
- New conditions, pages or HR separators take effect immediately.
- CSV output is append-only and safe to ship to remote operators.

---

## 📬 Issues & contributions

If you encounter:
- incorrect conditional behavior,
- validation anomalies,
- terminal rendering issues on specific platforms,

please open an Issue or submit a Pull Request.

---

## 📄 License

MIT

---
