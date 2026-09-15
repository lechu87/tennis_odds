"""Unit tests for the append-only odds_history diffing logic in tennis_functions.py.

These cover the pure in-memory comparison (rows_changed_since_last_snapshot), not the
DB-facing helpers (fetch_last_odds_map/append_odds_history), which need a live connection.
"""
import tennis_functions as tf


def make_row(odd='1.5000', **overrides):
    row = {
        'tournament': 'ATP Roland Garros',
        'player1': 'Rafael Nadal',
        'player2': 'Novak Djokovic',
        'name': 'win',
        'cat1': 'overall',
        'cat2': '',
        'value': '',
        'odd': odd,
        'bukmacher': 'betclic',
        'date': '2026-06-01',
    }
    row.update(overrides)
    return row


def test_row_with_no_previous_snapshot_is_included():
    row = make_row()

    changed = tf.rows_changed_since_last_snapshot([row], last_odds={})

    assert changed == [row]


def test_unchanged_odd_is_skipped():
    row = make_row(odd='1.5000')
    key = tf._history_key(row)

    changed = tf.rows_changed_since_last_snapshot([row], last_odds={key: 1.5})

    assert changed == []


def test_changed_odd_is_included():
    row = make_row(odd='1.6000')
    key = tf._history_key(row)

    changed = tf.rows_changed_since_last_snapshot([row], last_odds={key: 1.5})

    assert changed == [row]


def test_decimal_formatting_difference_does_not_count_as_change():
    # DB returns Decimal('1.5000'), CSV has '1.5' - must not be treated as a change.
    row = make_row(odd='1.5')
    key = tf._history_key(row)

    changed = tf.rows_changed_since_last_snapshot([row], last_odds={key: 1.5000})

    assert changed == []


def test_different_market_key_is_independent():
    row_win = make_row(odd='1.5', name='win')
    row_gem = make_row(odd='2.5', name='Gem', cat1='handicap')
    last_odds = {tf._history_key(row_win): 1.5}

    changed = tf.rows_changed_since_last_snapshot([row_win, row_gem], last_odds)

    assert changed == [row_gem]


def test_duplicate_key_within_one_run_keeps_last_occurrence():
    # Same natural key twice in one file (bookmaker data quality issue) - last one wins,
    # instead of depending on non-deterministic DB tie-breaking.
    row_first = make_row(odd='1.50')
    row_second = make_row(odd='1.60')

    changed = tf.rows_changed_since_last_snapshot([row_first, row_second], last_odds={})

    assert changed == [row_second]
