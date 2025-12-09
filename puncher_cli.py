import curses
import csv
import os
from dataclasses import dataclass
from typing import List, Optional, Set, Dict
from pathlib import Path
import sys
from build_date import VER


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        # Wersja skompilowana — zapisujemy DANE OBOK aplikacji (.exe / binarki)
        return Path(sys.executable).resolve().parent
    else:
        # Wersja pythonowa — katalog źródłowy
        return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DICT_PATH = DATA_DIR / "questionnaire.txt"
CSV_PATH = DATA_DIR / "responses.csv"

UNIQUE_ID_VAR: str | None = None  # nazwa zmiennej identyfikatora, np. "P0"
USED_IDS: set[str] = set()  # zestaw wszystkich ID już użytych w responses.csv

# Motyw ASCII – bez znaków Unicode
BOX_TL = "╔"
BOX_TR = "╗"
BOX_BL = "╚"
BOX_BR = "╝"
BOX_H = "═"  # pozioma kreska
BOX_V = "║"  # pionowa kreska

HR_CHAR = "="  # separator sekcji (hr)

TEXT_PLACEHOLDER_CHAR = "_"
NUM_PLACEHOLDER_CHAR = "_"

MIN_WIDTH = 80
MIN_HEIGHT = 20  # opcjonalnie, ale zwykle warto

CONTENT_START_Y = 1  # Treść zaczyna się w wierszu 1, pod jednoliniowym headerem


# ---------- Pomocnicze ----------


def load_used_ids(csv_path: Path, id_var: str) -> set[str]:
    """
    Wczytuje wszystkie dotychczas użyte identyfikatory z CSV.
    Zakłada, że kolumna id_var istnieje w nagłówku responses.csv.
    """
    used: set[str] = set()
    if not csv_path.exists():
        return used

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or id_var not in reader.fieldnames:
            return used
        for row in reader:
            val = row.get(id_var)
            if val:
                used.add(str(val))
    return used


def warn_duplicate_id(stdscr, value: str):
    """
    Wyświetla krótkie ostrzeżenie, że ID już istnieje.
    """
    import curses

    h, w = stdscr.getmaxyx()

    msg2 = f" To ID '{value}' jest już użyte w bazie danych. "
    spcr = " " * len(msg2)
    msg11 = " DUPLIKAT ID ! "
    msg1 = msg11 + " " * (len(msg2) - len(msg11))
    msg33 = " Proszę użyć innego identyfikatora. "
    msg3 = msg33 + " " * (len(msg2) - len(msg33))

    lines = [spcr, msg1, spcr, msg2, msg3, spcr]
    max_len = max(len(x) for x in lines)
    start_y = max(0, h // 2 - len(lines) // 2)
    start_x = max(0, (w - max_len) // 2)

    for i, line in enumerate(lines):
        y = start_y + i
        if 0 <= y < h:
            text = line[: max(0, w - start_x)]
            try:
                stdscr.addstr(y, start_x, text)
                stdscr.chgat(y, start_x, len(text), curses.A_REVERSE)
            except curses.error:
                pass

    stdscr.refresh()
    stdscr.getch()  # czekamy na dowolny klawisz


def terminal_too_small(stdscr, min_w=MIN_WIDTH, min_h=MIN_HEIGHT) -> bool:
    h, w = stdscr.getmaxyx()
    return w < min_w or h < min_h


def draw_too_small_dialog(stdscr, min_w=MIN_WIDTH, min_h=MIN_HEIGHT):
    import curses

    stdscr.erase()
    h, w = stdscr.getmaxyx()

    lines = [
        "TERMINAL WINDOW TOO SMALL",
        f"Required minimum size: {min_w} x {min_h}",
        f"Current size: {w} x {h}",
        "",
        "Please enlarge the terminal window to continue.",
        "Press any key after resizing.",
    ]

    total = len(lines)
    max_len = max(len(x) for x in lines)
    start_y = max(0, h // 2 - total // 2)
    start_x = max(0, (w - max_len) // 2)

    for i, line in enumerate(lines):
        y = start_y + i
        if 0 <= y < h:
            text = line[: max(0, w - start_x)]
            try:
                stdscr.addstr(y, start_x, text)
                stdscr.chgat(y, start_x, len(text))
            except curses.error:
                pass

    stdscr.refresh()


def safe_addstr(stdscr, y: int, x: int, text: str):
    if not text:
        return
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    max_len = max(0, w - x - 1)
    if max_len <= 0:
        return
    stdscr.addstr(y, x, text[:max_len])


def safe_chgat(stdscr, y: int, x: int, length: int, attr):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w or length <= 0:
        return
    max_len = min(length, w - x - 1)
    if max_len <= 0:
        return
    stdscr.chgat(y, x, max_len, attr)


def confirm_exit(stdscr) -> bool:
    """
    Wyświetla wycentrowane okno dialogowe z ramką ASCII w trybie reverse.
    Zwraca True jeśli użytkownik wybierze 't|y', False przy 'n' lub ESC.
    """
    h, w = stdscr.getmaxyx()

    # Treść okna
    line1 = "!UWAGA! Zakończyć program? (T)ak/(N)ie"
    line2 = "Informacje z aktywnej, niedokończonej ankiety zostaną utracone!"

    content_width = max(len(line1), len(line2))
    box_width = content_width + 2  # 1 spacja z każdej strony wewnątrz ramki
    box_height = 4  # top + 2 linie tekstu + bottom

    # Wycentrowanie
    start_y = max(0, h // 2 - box_height // 2)
    start_x = max(0, (w - (box_width + 2)) // 2)  # +2 na rogi ramki

    # Ramka ASCII
    top = " " + " " * box_width + " "
    bottom = " " + " " * box_width + " "
    row1 = "  " + line1.ljust(content_width) + "  "
    row2 = "  " + line2.ljust(content_width) + "  "

    lines = [top, row1, row2, bottom]

    # Rysowanie okna
    for i, text in enumerate(lines):
        y = start_y + i
        safe_addstr(stdscr, y, start_x, text)
        # reverse na całej szerokości okna
        safe_chgat(stdscr, y, start_x, len(text), curses.A_REVERSE)

    stdscr.refresh()

    # Oczekiwanie na 'y', 'n' albo ESC
    while True:
        ch = stdscr.getch()
        if ch in (ord("y"), ord("Y"), ord("t"), ord("T")):
            return True
        if ch in (ord("n"), ord("N")):
            return False
        if ch == 27:  # ESC
            return False


def error_beep():
    curses.beep()
    curses.flash()


# ---------- Słownik: struktura i parser ----------


@dataclass
class DictItem:
    kind: str  # "question", "hr", "page"
    name: Optional[str] = None
    varlab: Optional[str] = None
    accept: Optional[str] = None
    text_len: Optional[int] = None
    condition: Optional[str] = None  # np. "P283=8"


def parse_dictionary(path: str) -> List[DictItem]:
    items: List[DictItem] = []

    current_name = None
    current_varlab = None
    current_accept = None
    current_text = None
    current_if = None

    def flush_question():
        nonlocal current_name, current_varlab, current_accept, current_text, current_if
        if current_name is not None:
            items.append(
                DictItem(
                    kind="question",
                    name=current_name,
                    varlab=current_varlab or current_name,
                    accept=current_accept,
                    text_len=int(current_text) if current_text else None,
                    condition=current_if,
                )
            )
        current_name = None
        current_varlab = None
        current_accept = None
        current_text = None
        current_if = None

    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith("[") and line.endswith("]"):
                flush_question()
                current_name = line[1:-1]
            elif line == "hr":
                flush_question()
                items.append(DictItem(kind="hr"))
            elif line == "page":
                flush_question()
                items.append(DictItem(kind="page"))
            elif "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if key == "varlab":
                    current_varlab = value
                elif key == "accept":
                    current_accept = value
                elif key == "text":
                    current_text = value
                elif key == "if":
                    current_if = value

    flush_question()
    return items


def split_pages(items: List[DictItem]) -> List[List[DictItem]]:
    pages: List[List[DictItem]] = []
    current: List[DictItem] = []
    for it in items:
        if it.kind == "page":
            if current:
                pages.append(current)
                current = []
        else:
            current.append(it)
    if current:
        pages.append(current)
    return pages


def get_question_order(items: List[DictItem]) -> List[str]:
    """Stała kolejność zmiennych do CSV."""
    return [it.name for it in items if it.kind == "question" and it.name is not None]


# ---------- Warunek if (złożony) ----------


def condition_met(condition: Optional[str], answers: Dict[str, str]) -> bool:
    """
    Obsługuje złożone warunki typu:
      if=P283=8
      if=P283!=8
      if=P283=1|2|3
      if=P283!=1|2|3
      if=P1=1 & P2=3
      if=P1=1|2 & P2!=4|5

    Składnia:
      AND:  expr & expr & ...
      expr: VAR=val1|val2|...   lub   VAR!=val1|val2|...

    Brak odpowiedzi w zmiennej -> warunek dla niej jest False.
    Cały warunek = AND wszystkich expr.
    """
    if not condition:
        return True

    and_parts = [p.strip() for p in condition.split("&") if p.strip()]
    if not and_parts:
        return True

    for part in and_parts:
        op = None
        if "!=" in part:
            var, rest = part.split("!=", 1)
            op = "!="
        elif "=" in part:
            var, rest = part.split("=", 1)
            op = "="
        else:
            continue  # nieznany fragment, ignorujemy

        var = var.strip()
        rest = rest.strip()

        values = [v.strip() for v in rest.split("|") if v.strip()]
        if not values:
            continue

        current = answers.get(var)
        if current is None:
            return False

        cur = str(current)

        if op == "=":
            if cur not in values:
                return False
        elif op == "!=":
            if cur in values:
                return False

    return True


# ---------- accept: parser & logika kodów ----------


def parse_accept(accept_str: str) -> Set[int]:
    """
    Np. "1:5,8,12:17,33,45" -> {1,2,3,4,5,8,12,13,14,15,16,17,33,45}
    """
    allowed: Set[int] = set()
    for part in accept_str.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            start, end = part.split(":", 1)
            start = int(start.strip())
            end = int(end.strip())
            step = 1 if end >= start else -1
            for v in range(start, end + step, step):
                allowed.add(v)
        else:
            allowed.add(int(part))
    return allowed


@dataclass
class Field:
    name: str
    label: str
    ftype: str  # "numeric" or "text"
    max_len: int
    input_row: int
    input_col: int
    label_row: int
    value: str = ""
    accept_str: Optional[str] = None
    allowed_values: Optional[Set[int]] = None
    code_strings: Optional[Set[str]] = None
    max_code_len: Optional[int] = None
    condition: Optional[str] = None
    active: bool = True


def prepare_numeric_field(field: Field, accept_str: str):
    allowed = parse_accept(accept_str)
    codes = {str(v) for v in allowed}
    max_len = max(len(c) for c in codes) if codes else field.max_len
    field.accept_str = accept_str
    field.allowed_values = allowed
    field.code_strings = codes
    field.max_code_len = max_len
    field.max_len = max_len


def numeric_next_state(field: Field, digit: str, current_value: Optional[str] = None):
    """Logika auto-skoków przy wpisywaniu na końcu pola."""
    if current_value is None:
        current_value = field.value

    if field.code_strings is None:
        if len(current_value) >= field.max_len:
            return current_value, False, False
        new_val = current_value + digit
        return new_val, False, True

    new_val = current_value + digit
    codes = field.code_strings
    matching_codes = {c for c in codes if c.startswith(new_val)}

    if not matching_codes:
        return current_value, False, False

    is_full_code = new_val in codes
    is_prefix_of_others = any(len(c) > len(new_val) for c in matching_codes)
    auto_advance = False

    if is_full_code and not is_prefix_of_others:
        auto_advance = True
    else:
        max_code_len = field.max_code_len or field.max_len
        if is_full_code and len(new_val) >= max_code_len:
            auto_advance = True

    return new_val, auto_advance, True


def is_numeric_value_valid(field: Field, value: str) -> bool:
    if value == "-" or value == "":
        return True
    if field.allowed_values is None:
        return True
    if not value.isdigit():
        return False
    return int(value) in field.allowed_values


# ---------- Pola z jednej strony słownika ----------


def build_fields_from_page(
    page_items: List[DictItem],
    page_width: int,
    answers: Dict[str, str],
) -> tuple[list[Field], list[int]]:
    fields: List[Field] = []
    hr_rows: List[int] = []
    content_width = max(60, page_width)
    row = 0

    for item in page_items:
        if item.kind == "hr":
            # zapamiętujemy, na którym logicznym wierszu jest pozioma linia
            hr_rows.append(row)
            row += 1
            continue

        if item.kind != "question":
            continue

        name = item.name
        label = item.varlab or name
        initial_value = answers.get(name, "")

        active = condition_met(item.condition, answers)

        # tekst
        if item.text_len is not None:
            label_row = row
            input_row = row + 1
            text_len = min(item.text_len, content_width)
            f = Field(
                name=name,
                label=f"{name}. {label}",
                ftype="text",
                max_len=text_len,
                input_row=input_row,
                input_col=0,
                label_row=label_row,
                value=initial_value if active else "",
                condition=item.condition,
                active=active,
            )
            fields.append(f)
            row += 3

        # liczba
        elif item.accept is not None:
            prefix = f"{name}. "
            f = Field(
                name=name,
                label="",
                ftype="numeric",
                max_len=1,
                input_row=row,
                input_col=len(prefix),
                label_row=row,
                value=initial_value if active else "",
                condition=item.condition,
                active=active,
            )
            prepare_numeric_field(f, item.accept)
            placeholder = "-" * f.max_len
            f.label = f"{prefix}{placeholder} {label}"
            fields.append(f)
            row += 1

        # fallback: tekstowe
        else:
            label_row = row
            input_row = row + 1
            text_len = content_width
            f = Field(
                name=name,
                label=f"{name}. {label}",
                ftype="text",
                max_len=text_len,
                input_row=input_row,
                input_col=0,
                label_row=label_row,
                value=initial_value if active else "",
                condition=item.condition,
                active=active,
            )
            fields.append(f)
            row += 3

    return fields, hr_rows


def recompute_field_actives(fields: List[Field], answers: Dict[str, str]):
    """Przelicza if-y, czyści wartości nieaktywnych pól."""
    for f in fields:
        is_active = condition_met(f.condition, answers)
        f.active = is_active
        if not is_active:
            f.value = ""
            answers.pop(f.name, None)


# ---------- CSV ----------


def save_answers_to_csv(answers: Dict[str, str], items: List[DictItem], path: str):
    """
    Zapis:
      - pytania nieaktywne -> puste pole (brak w answers),
      - brak danych ('-') -> puste pole (NULL),
      - normalne odpowiedzi -> wartość jako string.
    """
    var_order = get_question_order(items)
    file_exists = os.path.exists(path)

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=var_order)
        if not file_exists:
            writer.writeheader()

        row: Dict[str, str] = {}
        for var in var_order:
            val = answers.get(var, "")
            if val == "-":
                row[var] = ""  # brak danych jako NULL
            else:
                row[var] = val
        writer.writerow(row)


# ---------- Rysowanie ----------


def draw_header(stdscr, current_page: int, total_pages: int, interview_no: int):
    h, w = stdscr.getmaxyx()

    # Tekst nagłówka
    left = f"| WYWIAD {interview_no} | STRONA {current_page}/{total_pages} |"
    right = f"| PUNCHER_CLI, VER: {VER} |"

    # Zbudowanie pełnej linii
    # Między lewą i prawą częścią robimy odstęp tak, by całość wypełniała szerokość terminala.
    middle_space = max(1, w - len(left) - len(right) - 1)
    header_line = left + (" " * middle_space) + right

    # Ucięcie do szerokości terminala
    header_line = header_line[: max(0, w - 1)]

    # Wypisanie i reverse
    safe_addstr(stdscr, 0, 0, header_line)
    safe_chgat(stdscr, 0, 0, w - 1, curses.A_REVERSE)


def draw_footer(stdscr):
    h, w = stdscr.getmaxyx()
    y = h - 1
    footer = "| ↑/↓ | PgUp/PgDn | ENTER: dalej | minus: brak danych | ctrl+d: wyjście |"

    # Najpierw wypisz tekst (ucięty, jeśli terminal za wąski)
    safe_addstr(stdscr, y, 0, footer)

    # Potem odwróć atrybuty na całej linii z tekstem
    # (safe_chgat i tak zadba o to, żeby nie wyjść poza ekran)
    safe_chgat(stdscr, y, 0, max(0, min(len(footer), w - 1)), curses.A_REVERSE)


def draw_page(
    stdscr,
    fields: List[Field],
    hr_rows: List[int],
    current_index: int,
    scroll_offset: int,
    current_page: int,
    total_pages: int,
    interview_no: int,
):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    page_width = max(60, w)
    content_start_y = CONTENT_START_Y
    content_end_y = h - 2

    draw_header(stdscr, current_page, total_pages, interview_no)

    # najpierw rysujemy pytania
    for idx, f in enumerate(fields):
        label_y = content_start_y + (f.label_row - scroll_offset)
        if content_start_y <= label_y <= content_end_y:
            safe_addstr(stdscr, label_y, 0, f.label)
            if not f.active:
                safe_chgat(stdscr, label_y, 0, len(f.label), curses.A_DIM)

        if f.ftype == "text":
            input_y = content_start_y + (f.input_row - scroll_offset)
            if content_start_y <= input_y <= content_end_y:
                placeholder = TEXT_PLACEHOLDER_CHAR * max(
                    1, min(f.max_len, page_width - 1)
                )
                safe_addstr(stdscr, input_y, 0, placeholder)
                display_value = f.value[: f.max_len]
                safe_addstr(stdscr, input_y, f.input_col, display_value)
                if not f.active:
                    safe_chgat(stdscr, input_y, 0, f.max_len, curses.A_DIM)
                elif idx == current_index:
                    length = max(len(display_value), 1)
                    safe_chgat(stdscr, input_y, f.input_col, length, curses.A_REVERSE)
        else:
            input_y = content_start_y + (f.input_row - scroll_offset)
            if content_start_y <= input_y <= content_end_y:
                max_len = f.max_len
                placeholder = NUM_PLACEHOLDER_CHAR * max_len
                safe_addstr(stdscr, input_y, f.input_col, placeholder)
                display_value = f.value[:max_len]
                safe_addstr(stdscr, input_y, f.input_col, display_value)
                if not f.active:
                    safe_chgat(stdscr, input_y, f.input_col, max_len, curses.A_DIM)
                elif idx == current_index:
                    safe_chgat(stdscr, input_y, f.input_col, max_len, curses.A_REVERSE)

    # teraz rysujemy poziome linie hr w odpowiednich logicznych wierszach
    for hr_row in hr_rows:
        y = content_start_y + (hr_row - scroll_offset)
        if content_start_y <= y <= content_end_y:
            safe_addstr(stdscr, y, 0, HR_CHAR * (max(0, w - 1)))

    draw_footer(stdscr)
    stdscr.refresh()


# ---------- Pętla wielu ankiet ----------


def edit_page(stdscr, items, pages_items):
    curses.curs_set(1)
    stdscr.keypad(True)

    total_pages = len(pages_items)

    interview_no = 1

    while True:  # pętla kolejnych ankiet
        answers: Dict[str, str] = {}
        current_page_idx = 0

        h, w = stdscr.getmaxyx()
        fields, hr_rows = build_fields_from_page(
            pages_items[current_page_idx], w, answers
        )
        recompute_field_actives(fields, answers)

        def find_next_active(from_index: int) -> Optional[int]:
            i = from_index + 1
            while i < len(fields):
                if fields[i].active:
                    return i
                i += 1
            return None

        def find_prev_active(from_index: int) -> Optional[int]:
            i = from_index - 1
            while i >= 0:
                if fields[i].active:
                    return i
                i -= 1
            return None

        # start od pierwszego aktywnego
        current_index = 0
        if fields and not fields[current_index].active:
            nxt = find_next_active(-1)
            if nxt is not None:
                current_index = nxt
        scroll_offset = 0
        cursor_pos = 0

        while True:  # pętla w obrębie jednej ankiety
            if terminal_too_small(stdscr):
                draw_too_small_dialog(stdscr)
                stdscr.getch()  # czekamy aż user powiększy okno i wciśnie cokolwiek
                continue

            h, w = stdscr.getmaxyx()
            content_start_y = CONTENT_START_Y
            content_end_y = h - 2
            content_height = max(1, content_end_y - content_start_y + 1)

            # przelicz if-y po ewentualnych zmianach odpowiedzi
            recompute_field_actives(fields, answers)

            # jeśli na stronie nie ma żadnych aktywnych pól
            if not any(f.active for f in fields):
                if current_page_idx < total_pages - 1:
                    current_page_idx += 1
                    fields, hr_rows = build_fields_from_page(
                        pages_items[current_page_idx], w, answers
                    )
                    recompute_field_actives(fields, answers)
                    current_index = 0
                    if fields and not fields[0].active:
                        nxt = find_next_active(-1)
                        if nxt is not None:
                            current_index = nxt
                    scroll_offset = 0
                    cursor_pos = 0
                    continue
                else:
                    # ostatnia strona, nic aktywnego -> zapis i nowa ankieta
                    save_answers_to_csv(answers, items, CSV_PATH)
                    id_val = str(answers.get(UNIQUE_ID_VAR, "")).strip()
                    if id_val:
                        USED_IDS.add(id_val)
                    interview_no += 1
                    break  # nowa ankieta

            current = fields[current_index]

            # scroll
            target_logical_row = current.input_row
            screen_y = content_start_y + (target_logical_row - scroll_offset)
            if screen_y < content_start_y:
                scroll_offset = target_logical_row
            elif screen_y > content_end_y:
                scroll_offset = target_logical_row - content_height + 1
                if scroll_offset < 0:
                    scroll_offset = 0

            draw_page(
                stdscr,
                fields,
                hr_rows,
                current_index,
                scroll_offset,
                current_page=current_page_idx + 1,
                total_pages=total_pages,
                interview_no=interview_no,
            )

            input_y = content_start_y + (current.input_row - scroll_offset)
            if 0 <= input_y < h:
                cursor_x = min(
                    current.input_col + cursor_pos,
                    current.input_col + current.max_len - 1,
                    w - 1,
                )
                stdscr.move(input_y, cursor_x)

            stdscr.refresh()
            ch = stdscr.getch()

            # zmiana rozmiaru terminala
            if ch == curses.KEY_RESIZE:
                # przebuduj layout pól dla aktualnej strony z uwzględnieniem nowej szerokości
                h, w = stdscr.getmaxyx()
                fields, hr_rows = build_fields_from_page(
                    pages_items[current_page_idx], w, answers
                )
                recompute_field_actives(fields, answers)

                # opcja minimum: wróć na pierwsze aktywne pole na stronie
                current_index = 0
                if fields and not fields[0].active:
                    # znajdź pierwszy aktywny
                    i = 0
                    while i < len(fields) and not fields[i].active:
                        i += 1
                    if i < len(fields):
                        current_index = i

                scroll_offset = 0
                cursor_pos = 0
                stdscr.erase()
                stdscr.refresh()
                continue

            # WYJŚCIE: Ctrl+D (ASCII 4) + potwierdzenie
            if ch == 4:  # Ctrl+D
                if confirm_exit(stdscr):
                    return
                else:
                    continue

            # PAGE UP – powrót do poprzedniej strony
            if ch == curses.KEY_PPAGE:
                if current_page_idx > 0:
                    current_page_idx -= 1

                    h, w = stdscr.getmaxyx()
                    fields, hr_rows = build_fields_from_page(
                        pages_items[current_page_idx], w, answers
                    )
                    recompute_field_actives(fields, answers)

                    # ustawiamy kursor na OSTATNIM aktywnym polu na stronie
                    if fields:
                        idx = len(fields) - 1
                        while idx >= 0 and not fields[idx].active:
                            idx -= 1
                        current_index = max(idx, 0)

                        # scroll tak, żeby pole było widoczne
                        target_row = fields[current_index].input_row
                        content_start_y = CONTENT_START_Y
                        h, w = stdscr.getmaxyx()
                        content_end_y = h - 2
                        content_height = max(1, content_end_y - content_start_y + 1)
                        scroll_offset = max(0, target_row - content_height + 1)

                        cursor_pos = len(fields[current_index].value or "")
                    continue

            # PAGE DOWN – przejście do następnej strony (bez zapisu ankiety)
            if ch == curses.KEY_NPAGE:
                if current_page_idx < total_pages - 1:
                    current_page_idx += 1

                    h, w = stdscr.getmaxyx()
                    fields, hr_rows = build_fields_from_page(
                        pages_items[current_page_idx], w, answers
                    )
                    recompute_field_actives(fields, answers)

                    # ustawiamy kursor na PIERWSZYM aktywnym polu
                    current_index = 0
                    if fields and not fields[0].active:
                        i = 0
                        while i < len(fields) and not fields[i].active:
                            i += 1
                        if i < len(fields):
                            current_index = i

                    scroll_offset = 0
                    cursor_pos = len(fields[current_index].value or "") if fields else 0
                continue

            # GÓRA – poprzednie aktywne
            if ch == curses.KEY_UP:
                prev_idx = find_prev_active(current_index)
                if prev_idx is not None:
                    current_index = prev_idx
                    current = fields[current_index]
                    cursor_pos = 0
                else:
                    curses.beep()
                continue

            # DÓŁ / ENTER – kolejne aktywne / kolejna strona / zapis
            if ch in (curses.KEY_DOWN, curses.KEY_ENTER, 10, 13):
                if not current.active:
                    nxt = find_next_active(current_index)
                    if nxt is not None:
                        current_index = nxt
                        current = fields[current_index]
                        cursor_pos = 0
                    else:
                        if current_page_idx < total_pages - 1:
                            current_page_idx += 1
                            fields, hr_rows = build_fields_from_page(
                                pages_items[current_page_idx], w, answers
                            )
                            recompute_field_actives(fields, answers)
                            current_index = 0
                            if fields and not fields[0].active:
                                nxt2 = find_next_active(-1)
                                if nxt2 is not None:
                                    current_index = nxt2
                            scroll_offset = 0
                            cursor_pos = 0
                        else:
                            save_answers_to_csv(answers, items, CSV_PATH)
                            id_val = str(answers.get(UNIQUE_ID_VAR, "")).strip()
                            if id_val:
                                USED_IDS.add(id_val)
                            interview_no += 1
                            break
                    continue

                if current.value == "":
                    curses.beep()
                    continue
                if current.ftype == "numeric" and not is_numeric_value_valid(
                    current, current.value
                ):
                    error_beep()
                    continue

                # sprawdzenie unikalności ID przy opuszczaniu pola
                if current.name == UNIQUE_ID_VAR:
                    val = str(current.value or "").strip()
                    if val and val in USED_IDS:
                        error_beep()
                        warn_duplicate_id(stdscr, val)
                        # NIE opuszczamy pola, użytkownik musi zmienić ID
                        continue

                answers[current.name] = current.value
                recompute_field_actives(fields, answers)

                nxt = find_next_active(current_index)
                if nxt is not None:
                    current_index = nxt
                    current = fields[current_index]
                    cursor_pos = 0
                else:
                    if current_page_idx < total_pages - 1:
                        current_page_idx += 1
                        fields, hr_rows = build_fields_from_page(
                            pages_items[current_page_idx], w, answers
                        )
                        recompute_field_actives(fields, answers)
                        current_index = 0
                        if fields and not fields[0].active:
                            nxt2 = find_next_active(-1)
                            if nxt2 is not None:
                                current_index = nxt2
                        scroll_offset = 0
                        cursor_pos = 0
                    else:
                        save_answers_to_csv(answers, items, CSV_PATH)
                        id_val = str(answers.get(UNIQUE_ID_VAR, "")).strip()
                        if id_val:
                            USED_IDS.add(id_val)
                        interview_no += 1
                        break
                continue

            # BACKSPACE
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if current.value:
                    current.value = current.value[:-1]
                    answers[current.name] = current.value
                    recompute_field_actives(fields, answers)
                    cursor_pos = min(cursor_pos, len(current.value))
                else:
                    curses.beep()
                continue

            # normalny znak
            try:
                s = chr(ch)
            except ValueError:
                continue

            # brak danych '-'
            if s == "-":
                current.value = "-"
                answers[current.name] = current.value
                recompute_field_actives(fields, answers)
                cursor_pos = len(current.value)
                continue

            # NUMERIC – auto-skok
            if current.ftype == "numeric":
                if not s.isdigit():
                    curses.beep()
                    continue

                if cursor_pos == 0:
                    current.value = ""

                if len(current.value) >= current.max_len:
                    curses.beep()
                    continue

                new_val, auto_adv, ok = numeric_next_state(
                    current, s, current_value=current.value
                )
                if not ok:
                    error_beep()
                    continue

                current.value = new_val
                answers[current.name] = current.value
                cursor_pos = len(current.value)
                recompute_field_actives(fields, answers)

                if auto_adv and current.value not in ("", "-"):

                    # jeśli to pole identyfikatora – sprawdź duplikat PRZED auto-skokiem
                    if current.name == UNIQUE_ID_VAR:
                        val = str(current.value or "").strip()
                        if val and val in USED_IDS:
                            error_beep()
                            warn_duplicate_id(stdscr, val)
                            # zostajemy w tym polu, nie przeskakujemy dalej
                            continue

                    nxt = find_next_active(current_index)
                    if nxt is not None:
                        current_index = nxt
                        current = fields[current_index]
                        cursor_pos = 0
                    else:
                        if current_page_idx < total_pages - 1:
                            current_page_idx += 1
                            fields, hr_rows = build_fields_from_page(
                                pages_items[current_page_idx], w, answers
                            )
                            recompute_field_actives(fields, answers)
                            current_index = 0
                            if fields and not fields[0].active:
                                nxt2 = find_next_active(-1)
                                if nxt2 is not None:
                                    current_index = nxt2
                            scroll_offset = 0
                            cursor_pos = 0
                        else:
                            save_answers_to_csv(answers, items, CSV_PATH)
                            id_val = str(answers.get(UNIQUE_ID_VAR, "")).strip()
                            if id_val:
                                USED_IDS.add(id_val)
                            interview_no += 1
                            break
                continue

            # TEXT
            if current.ftype == "text":
                if len(current.value) >= current.max_len:
                    curses.beep()
                    continue
                if cursor_pos == 0:
                    current.value = ""
                current.value += s
                answers[current.name] = current.value
                recompute_field_actives(fields, answers)
                cursor_pos = len(current.value)
                continue


def main():
    global UNIQUE_ID_VAR, USED_IDS

    # 1. Parsujemy słownik tylko raz
    items = parse_dictionary(DICT_PATH)
    pages_items = split_pages(items)

    # 2. Lista wszystkich nazw zmiennych pytaniowych (kind=="question")
    question_items = [it for it in items if it.kind == "question" and it.name]
    if not question_items:
        raise RuntimeError(
            "Dictionary has no question items – cannot determine unique ID."
        )

    var_names = [it.name for it in question_items]

    # 3. Pierwsze pytanie traktujemy jako identyfikator ankiety
    UNIQUE_ID_VAR = var_names[0]

    # 4. Wczytujemy dotychczas użyte ID z responses.csv
    USED_IDS = load_used_ids(Path(CSV_PATH), UNIQUE_ID_VAR)

    # 5. Start curses, przekazujemy items + pages_items
    curses.wrapper(edit_page, items, pages_items)


if __name__ == "__main__":
    main()
