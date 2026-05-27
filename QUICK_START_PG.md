# QUICK START - Konfiguracja PostgreSQL (5 minut)

## Krok 1: Instalacja PostgreSQL (Ubuntu)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

Sprawdź:
```bash
psql --version
```

## Krok 2: Konfiguracja zmiennych środowiskowych

```bash
# Skopiuj plik przykładowy
cp .env.example .env

# Edytuj (zmień hasło na swoje)
nano .env
```

Zawartość `.env`:
```
ODDS_DB_HOST=localhost
ODDS_DB_PORT=5432
ODDS_DB_NAME=odds_db
ODDS_DB_USER=odds_user
ODDS_DB_PASSWORD=twoje_bezpieczne_haslo
```

## Krok 3: Instalacja Python dependencies

```bash
pip install -r requirements_postgres.txt
```

## Krok 4: Automatyczna inicjalizacja bazy

```bash
source .env
python3 init_db.py
```

Skrypt automatycznie:
- ✓ Sprawdzi PostgreSQL
- ✓ Utworzy użytkownika `odds_user`
- ✓ Utworzy bazę `odds_db`
- ✓ Załaduje schemat SQL
- ✓ Przetestuje połączenie

## Krok 5: Weryfikacja (opcjonalnie)

```bash
psql -U odds_user -d odds_db -h localhost -c "\dt"
```

Powinna wyświetlić tabelę z listą tabel.

## Gotowe! 

Teraz możesz:

1. **Zaktualizować istniejące skrypty:**
```python
# Zmień import:
import connect_to_postgres as db

# Zamiast connect_to_wp_db
conn = db.connect_to_postgres_local()
```

2. **Wstawiać dane:**
```python
from connect_to_postgres import insert_odds_batch

odds_list = [
    {'match_id': 1, 'bookmaker_id': 1, 'bet_type_id': 1, 'value': '1.5', 'odd': 2.45},
]
insert_odds_batch(odds_list)
```

3. **Pobierać dane:**
```python
import psycopg2

conn = db.connect_to_postgres_local()
cur = conn.cursor()
cur.execute("SELECT * FROM odds WHERE scraped_at > NOW() - INTERVAL '1 hour'")
results = cur.fetchall()
```

## Troubleshooting

**Problem: "could not connect to server"**
```bash
sudo systemctl restart postgresql
```

**Problem: "password authentication failed"**
```bash
# Sprawdź czy .env ma prawidłowe hasło
cat .env
```

**Problem: "database does not exist"**
```bash
# Powtórz krok 4
python3 init_db.py
```

## Dalej...

Zapoznaj się z pełną dokumentacją w `POSTGRES_SETUP.md` aby zrozumieć wszystkie opcje i zaawansowaną konfigurację.

