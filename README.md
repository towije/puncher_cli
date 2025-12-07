# puncher-cli

CLI do wprowadzania danych z papierowych ankiet (styl CSPro), z obsługą:
- słownika `questionnaire.txt`,
- warunków `if`,
- zakresów `accept`,
- auto-skoku,
- wielu stron,
- zapisu do CSV (`data/responses.csv`).

## Wymagania

- Python 3.10+
- Na Windows: pakiet `windows-curses`

## Instalacja (tryb developerski)

```bash
git clone <TU_WSTAW_REPO_ALBO_ROZPAKUJ_ZIP>
cd puncher-cli

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .