-- PostgreSQL Schema dla bazy kursów bukmacherskich
-- Flat schema (mirror MySQL) - prosta, szybka, kompatybilna z tennis_functions.py

CREATE TABLE IF NOT EXISTS odds (
    id        BIGSERIAL PRIMARY KEY,
    tournament VARCHAR(255),
    player1   VARCHAR(255),
    player2   VARCHAR(255),
    name      VARCHAR(255),
    cat1      VARCHAR(255),
    cat2      VARCHAR(255),
    value     VARCHAR(255),
    odd       DECIMAL(10, 4),
    bukmacher VARCHAR(100),
    date      DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indeksy zoptymalizowane pod porównywanie kursów
-- Główne zapytanie: "daj mi wszystkie kursy na mecz X"
CREATE INDEX IF NOT EXISTS idx_odds_match
    ON odds(player1, player2, date);

-- Szybkie filtrowanie po graczu
CREATE INDEX IF NOT EXISTS idx_odds_player1
    ON odds(player1);

-- Główne zapytanie porównawcze: ten sam mecz, te same zakłady
CREATE INDEX IF NOT EXISTS idx_odds_comparison
    ON odds(player1, player2, name, cat1, value, date);

-- Szybkie kasowanie przed wstawieniem nowych danych
CREATE INDEX IF NOT EXISTS idx_odds_delete
    ON odds(bukmacher, date, player1, player2);

-- Append-only history of odds changes (unlike `odds`, never DELETEd/overwritten).
-- A row is inserted only when the odd actually changed since the last observation
-- for the same (bukmacher, tournament, player1, player2, name, cat1, cat2, value, date) key
-- - see tennis_functions.append_odds_history().
CREATE TABLE IF NOT EXISTS odds_history (
    id          BIGSERIAL PRIMARY KEY,
    tournament  VARCHAR(255),
    player1     VARCHAR(255),
    player2     VARCHAR(255),
    name        VARCHAR(255),
    cat1        VARCHAR(255),
    cat2        VARCHAR(255),
    value       VARCHAR(255),
    odd         DECIMAL(10, 4),
    bukmacher   VARCHAR(100),
    date        DATE,
    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lookup of the latest odd for a given natural key (used to decide if a new odd differs).
CREATE INDEX IF NOT EXISTS idx_odds_history_lookup
    ON odds_history(bukmacher, tournament, player1, player2, name, cat1, cat2, value, date, observed_at DESC);

