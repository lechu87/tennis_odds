"""Unit tests for the pure parsing/normalization logic in betclic_tennis.tennis_match.

These tests build a fake "raw match" dict shaped like the output of
betclic.extract_match_from_match_page(), so they run without network or DB access.
"""
import betclic_tennis


def make_raw_match(grouped_markets, player1='Rafael Nadal', player2='Novak Djokovic'):
    return {
        'contestants': [
            {'name': player1, 'short_name': player1.split()[-1]},
            {'name': player2, 'short_name': player2.split()[-1]},
        ],
        'competition': {'name': 'ATP Roland Garros'},
        'date': '2026-06-01T12:00:00Z',
        'grouped_markets': grouped_markets,
    }


def simple_market(name, selections):
    """selections: list of (label, odd) tuples."""
    return {
        'name': name,
        'markets': [{'selections': [[{'name': label, 'odds': odd} for label, odd in selections]]}],
    }


def test_known_simple_market_is_mapped_by_dictionary():
    # Betclic sends short names ("Nadal") in selections, expanded to full names via the player dictionary.
    raw = make_raw_match([
        simple_market('Zwycięzca meczu', [('Nadal', 1.5), ('Djokovic', 2.5)]),
    ])

    odds = betclic_tennis.tennis_match(raw).odds

    assert odds['tournament'] == 'ATP Roland Garros'
    assert odds['player1'] == 'Rafael Nadal'
    assert odds['player2'] == 'Novak Djokovic'
    assert odds['odds']['win']['overall']['Rafael Nadal'] == 1.5
    assert odds['odds']['win']['overall']['Novak Djokovic'] == 2.5


def test_under_over_market_splits_label_and_line_value():
    raw = make_raw_match([
        simple_market('Asy Powyżej/Poniżej', [('Poniżej 8.5', 1.9), ('Powyżej 8.5', 1.9)]),
    ])

    odds = betclic_tennis.tennis_match(raw).odds

    ace_odds = odds['odds']['Ace']['overall']
    assert ace_odds['Poniżej']['8.5'] == 1.9
    assert ace_odds['Powyżej']['8.5'] == 1.9


def test_dynamic_player_set_winner_market_resolves_via_fallback_rules():
    raw = make_raw_match([
        simple_market('Rafael Nadal wygra seta', [('Tak', 1.2), ('Nie', 4.0)]),
    ])

    odds = betclic_tennis.tennis_match(raw).odds

    assert 'Sets' in odds['odds']
    assert 'player1' in odds['odds']['Sets']


def test_unknown_market_falls_back_to_other_category():
    raw = make_raw_match([
        simple_market('Zupelnie nowy rynek bukmachera', [('Tak', 1.1), ('Nie', 5.0)]),
    ])

    odds = betclic_tennis.tennis_match(raw).odds

    assert 'other' in odds['odds']['Zupelnie nowy rynek bukmachera']
