"""Unit tests for the pure parsing/normalization logic in iforbet_tennis.tennis_match.

This module is shared as the parser for iforbet, etoto and totalbet (see bookmaker_runner.py
and totalbet_t.py), so covering it here exercises all three integrations at once.
"""
import iforbet_tennis


def make_raw_match(games, player1='Rafael Nadal', player2='Novak Djokovic', tournament='ATP Roland Garros'):
    return {
        'data': {
            'eventName': f'{player1} - {player2}',
            'category3Name': tournament,
            'eventStart': 1750000000 * 1000,
            'eventGames': games,
        }
    }


def game(name, argument, outcomes):
    return {
        'gameName': name,
        'argument': argument,
        'outcomes': [{'outcomeName': label, 'outcomeOdds': odd} for label, odd in outcomes],
    }


def test_known_simple_market_is_mapped_by_dictionary():
    raw = make_raw_match([
        game('Zwycięzca', None, [('Rafael Nadal', 1.5), ('Novak Djokovic', 2.5)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert odds['tournament'] == 'ATP Roland Garros'
    assert odds['player1'] == 'Rafael Nadal'
    assert odds['player2'] == 'Novak Djokovic'
    assert odds['odds']['win']['overall']['Rafael Nadal'] == 1.5
    assert odds['odds']['win']['overall']['Novak Djokovic'] == 2.5


def test_under_over_market_with_embedded_argument_splits_label_and_line_value():
    raw = make_raw_match([
        game('poniżej/powyżej gemów 20.5', 20.5, [('Poniżej 20.5', 1.9), ('Powyżej 20.5', 1.9)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    gem_odds = odds['odds']['Gem']['overall']
    assert gem_odds['Poniżej']['20.5'] == 1.9
    assert gem_odds['Powyżej']['20.5'] == 1.9


def test_totalbet_label_variant_is_mapped_by_dictionary():
    # Totalbet-specific label aliases were added directly to the shared odds_dict.
    raw = make_raw_match([
        game('Suma gemów 20.5', 20.5, [('Poniżej 20.5', 1.9), ('Powyżej 20.5', 1.9)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    gem_odds = odds['odds']['Gem']['overall']
    assert gem_odds['Poniżej']['20.5'] == 1.9


def test_unknown_market_falls_back_to_other_category():
    raw = make_raw_match([
        game('Zupelnie nowy rynek bukmachera', None, [('Tak', 1.1), ('Nie', 5.0)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert 'other' in odds['odds']['Zupelnie nowy rynek bukmachera']
