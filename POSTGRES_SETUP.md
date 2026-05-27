# PostgreSQL Setup Guide

## 1. Instalacja PostgreSQL na Ubuntu

```bash
# Aktualizuj system
sudo apt update

# Instaluj PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Sprawdzenie że instalacja się powiodła
psql --version
```

## 2. Włączenie usługi PostgreSQL

```bash
sudo systemctl enable postgresql
sudo systemctl restart postgresql
```

## 3. Tworzenie użytkownika i bazy danych

```bash
# Zaloguj się jako postgres user
sudo -u postgres psql

# W PostgreSQL shell, wykonaj:
```

```sql
-- Utwórz użytkownika
CREATE USER odds_user WITH PASSWORD 'twoje_bezpieczne_haslo';
ALTER ROLE odds_user SET client_encoding TO 'utf8';
ALTER ROLE odds_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE odds_user SET default_transaction_deferrable TO on;

-- Utwórz bazę
CREATE DATABASE odds_db OWNER odds_user;
GRANT ALL PRIVILEGES ON DATABASE odds_db TO odds_user;
GRANT CONNECT ON DATABASE odds_db TO odds_user;
GRANT USAGE ON SCHEMA public TO odds_user;
GRANT CREATE ON SCHEMA public TO odds_user;

-- Wyjdź
\q
```

## 4. Zmienne środowiskowe

Utwórz plik `.env` (na podstawie `.env.example`):

```bash
cp .env.example .env
nano .env
```

Lub dodaj do `~/.bashrc`:

```bash
# Dodaj na koniec pliku
export ODDS_DB_HOST=localhost
export ODDS_DB_PORT=5432
export ODDS_DB_NAME=odds_db
export ODDS_DB_USER=odds_user
export ODDS_DB_PASSWORD=twoje_bezpieczne_haslo
```

Następnie załaduj ustawienia:

```bash
source ~/.bashrc
```

## 5. Instalacja Python dependencies

```bash
pip install -r requirements_postgres.txt
```

## 6. Inicjalizacja bazy danych

```bash
python3 connect_to_postgres.py
```

Powinien wyświetlić: `✓ PostgreSQL connected: ...`

Następnie utwórz tabele:

```bash
python3 -c "from connect_to_postgres import create_tables; create_tables()"
```

## 7. Weryfikacja

```bash
psql -U odds_user -d odds_db -h localhost

# W psql shell:
\dt  # Pokaż tabele
SELECT COUNT(*) FROM bookmakers;  # Test zapytania
\q   # Wyjście
```

## 8. Integracja z istniejącymi skryptami

Zaktualizuj import w swoim głównym skrypcie (np. `betclic.py`):

```python
# Zmień z:
import connect_to_wp_db

# Na:
import connect_to_postgres as db

# Zamiast:
conn = connect_to_wp_db.connect_to_db()

# Użyj:
conn = db.connect_to_postgres_local()
```

## Wskazówki

- Hasła przechowaj w `.env` (dodaj do `.gitignore`)
- PostgreSQL domyślnie słucha na porcie 5432
- Dla SSH tunelu - ustaw `ODDS_SSH_HOST` w zmiennych środowiskowych
- PostgreSQL jest bezpieczniejszy i szybszy od MySQL dla tego typu danych

## Troubleshoot

### "could not connect to server"
```bash
sudo systemctl status postgresql
sudo systemctl restart postgresql
```

### "password authentication failed"
```bash
# Sprawdź zmienne środowiskowe
echo $ODDS_DB_PASSWORD
# i czy hasło jest prawidłowe
```

### "database does not exist"
```bash
# Powtórz sekcję 3 - tworzenie bazy
sudo -u postgres psql
```

