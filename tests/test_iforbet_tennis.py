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


# Regression tests grounded in real raw labels pulled from production data quality audit
# (see /memories/repo/scraper-notes.md - most odds were falling into cat1='other').


def test_argument_stripping_does_not_corrupt_leading_set_number():
    # Real bug: when the handicap value equals the set number, a naive global
    # str.replace() used to strip both, turning "2. set - handicap gemy" into
    # ". set - handicap gemy" (unmapped). Only the trailing occurrence must be stripped.
    raw = make_raw_match([
        game('2. set - handicap gemy 2', 2.0, [('Poniżej 2', 1.9), ('Powyżej 2', 1.9)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert '. set - handicap gemy' not in odds['odds']
    assert odds['odds']['Gem']['set2_handicap']['Poniżej']['2'] == 1.9


def test_argument_embedded_mid_label_is_still_stripped():
    # Most labels carry the argument in the middle, not at the end - must keep working.
    raw = make_raw_match([
        game('poniżej/powyżej 16.5 gemów', 16.5, [('Poniżej 16.5 gemów', 1.9), ('Powyżej 16.5 gemów', 1.9)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert odds['odds']['Gem']['overall']


def test_parenthesized_argument_is_stripped():
    raw = make_raw_match([
        game('Handicap gemowy (-0.5)', -0.5, [('Poniżej', 1.9), ('Powyżej', 1.9)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert odds['odds']['Gem']['handicap']


def test_set_prefixed_winner_market_is_mapped_regardless_of_dot_style():
    for label in ('1. set - zwycięzca', '1.. set - zwycięzca', '2 set - zwycięzca'):
        raw = make_raw_match([
            game(label, None, [('Rafael Nadal', 1.5), ('Novak Djokovic', 2.5)]),
        ])

        odds = iforbet_tennis.tennis_match(raw).odds

        assert 'Sets' in odds['odds'], label
        assert any(cat1.startswith('set') for cat1 in odds['odds']['Sets']), label


def test_set_prefixed_exact_score_market_is_mapped():
    raw = make_raw_match([
        game('1.. set - dokładny wynik', None, [('6:4', 4.5), ('6:3', 5.0)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert 'set1' in odds['odds']['score']


def test_set_prefixed_total_games_and_match_combo_are_mapped():
    raw = make_raw_match([
        game('1.. set - poniżej/powyżej gemów 9.5', 9.5, [('Poniżej 9.5', 1.9), ('Powyżej 9.5', 1.9)]),
        game('1 set/mecz', None, [('1-1', 3.0), ('1-2', 4.0)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert odds['odds']['Gem']['set1']['Poniżej']['9.5'] == 1.9
    assert 'set1_match' in odds['odds']['combined']


def test_bare_handicap_and_placeholder_labels_are_mapped():
    raw = make_raw_match([
        game('Handicap gemy 3', 3.0, [('Poniżej 3', 1.9), ('Powyżej 3', 1.9)]),
        game('Handicap gemowy ()', None, [('Poniżej', 1.9), ('Powyżej', 1.9)]),
        game('Dokładna suma setów', None, [('2', 1.5), ('3', 2.5)]),
        game('Liczba gemów', None, [('Poniżej 22.5', 1.9), ('Powyżej 22.5', 1.9)]),
    ])

    odds = iforbet_tennis.tennis_match(raw).odds

    assert 'other' not in odds['odds'].get('Handicap gemy 3', {})
    assert 'other' not in odds['odds'].get('Handicap gemowy ()', {})
    assert odds['odds']['Sets']['exactly']
    assert odds['odds']['Gem']['overall']

