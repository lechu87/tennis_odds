# odds_v2

Clean repository for the current tennis odds scraping pipeline.

## What is included

- Active scrapers and shared modules in the repo root:
	- `betclic.py`, `betclic_tennis.py`
	- `betfan_t.py`, `betfan_tennis.py`
	- `iforbet_t.py`, `iforbet_tennis.py`
	- `etoto_t.py`, `totalbet_t.py`, `lvbet_t.py`
	- `bookmaker_runner.py`, `tennis_functions.py`, `connect_to_postgres.py`
- `config/tennis_dictionary.json`: player-name dictionary used by all scrapers.
- `suggest_dictionary_updates.py`: log-to-dictionary helper and interactive review tool (defaults now point to `config/` and `data/`).
- `run.sh`: main entrypoint (uses lock file and doubles flags).
- `.env.example`: runtime configuration template.
- `requirements.txt` and `requirements_postgres.txt`: dependencies.
- `sql/SQL_QUERIES_POROWNANIE.sql` and `sql/db_schema.sql`: analysis and schema helpers.
- `data/odds`, `data/raw`, `data/reports`, `data/runtime`: generated runtime artifacts.
- `sql/`, `logs/`, `scripts/`: repository folders for queries, logs and utilities.

## Quick start

1. Create environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment:

```bash
cp .env.example .env
```

3. Run all bookmakers:

```bash
./run.sh
```

4. Run with doubles enabled for one bookmaker:

```bash
BETCLIC_SKIP_DOUBLES=0 ./run.sh
```

## Notes

Run `python -m py_compile` on the active `.py` files before the first production run.

## Push To GitHub

1. Create a new empty repository on GitHub.
2. Add the remote locally:

```bash
git remote add origin git@github.com:<your-user>/<your-repo>.git
```

3. Commit and push:

```bash
git add .
git commit -m "Initial clean repo"
git push -u origin main
```

4. If you prefer HTTPS, use:

```bash
git remote set-url origin https://github.com/<your-user>/<your-repo>.git
```
