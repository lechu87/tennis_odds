"""Unit tests for the pure parsing/normalization logic in betfan_tennis.tennis_match."""
import betfan_tennis


def make_raw_match(games, player1='Rafael Nadal', player2='Novak Djokovic', tournament='ATP Roland Garros'):
    return {
        'data': {
            'event': {
                'eventName': f'{player1} - {player2}',
                'categoryName': tournament,
                'eventStart': 1750000000 * 1000,
                'games': games,
            }
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

    odds = betfan_tennis.tennis_match(raw).odds

    assert odds['tournament'] == 'ATP Roland Garros'
    assert odds['player1'] == 'Rafael Nadal'
    assert odds['player2'] == 'Novak Djokovic'
    assert odds['odds']['win']['overall']['Rafael Nadal'] == 1.5
    assert odds['odds']['win']['overall']['Novak Djokovic'] == 2.5


def test_under_over_market_with_embedded_argument_splits_label_and_line_value():
    raw = make_raw_match([
        game('poniżej/powyżej gemów 20.5', 20.5, [('Poniżej 20.5', 1.9), ('Powyżej 20.5', 1.9)]),
    ])

    odds = betfan_tennis.tennis_match(raw).odds

    gem_odds = odds['odds']['Gem']['overall']
    assert gem_odds['Poniżej']['20.5'] == 1.9
    assert gem_odds['Powyżej']['20.5'] == 1.9


def test_unknown_market_falls_back_to_other_category():
    raw = make_raw_match([
        game('Zupelnie nowy rynek bukmachera', None, [('Tak', 1.1), ('Nie', 5.0)]),
    ])

    odds = betfan_tennis.tennis_match(raw).odds

    assert 'other' in odds['odds']['Zupelnie nowy rynek bukmachera']


# Regression tests grounded in real raw labels pulled from production data quality audit
# (see /memories/repo/scraper-notes.md - betfan had 51.7% of odds falling into cat1='other').


def test_argument_stripping_does_not_corrupt_leading_set_number():
    raw = make_raw_match([
        game('2. set - handicap gemowy 2', 2.0, [('-2', 1.9), ('+2', 1.9)]),
    ])

    odds = betfan_tennis.tennis_match(raw).odds

    assert '. set - handicap gemowy' not in odds['odds']
    assert odds['odds']['Gem']['set2_handicap']


def test_set_prefixed_winner_and_score_markets_are_mapped():
    raw = make_raw_match([
        game('1. set - zwycięzca', None, [('Rafael Nadal', 1.5), ('Novak Djokovic', 2.5)]),
        game('2. set - dokładny wynik', None, [('6:4', 4.5), ('6:3', 5.0)]),
    ])

    odds = betfan_tennis.tennis_match(raw).odds

    assert any(cat1.startswith('set') for cat1 in odds['odds']['Sets'])
    assert 'set2' in odds['odds']['score']


def test_bare_alias_labels_are_mapped():
    raw = make_raw_match([
        game('Dokładna liczba setów', None, [('2', 1.5), ('3', 2.5)]),
        game('Liczba gemów', None, [('Poniżej 22.5', 1.9), ('Powyżej 22.5', 1.9)]),
        game('Kto wygra pierwszego seta/kto wygra mecz', None, [('1-1', 3.0), ('1-2', 4.0)]),
        game('Mecz zakończy się wynikiem 2:0', None, [('Tak', 3.5), ('Nie', 1.2)]),
        game('Zwycięzca i liczba gemów', None, [('Rafael Nadal 22.5', 3.0), ('Novak Djokovic 22.5', 4.0)]),
    ])

    odds = betfan_tennis.tennis_match(raw).odds

    assert odds['odds']['Sets']['exactly']
    assert odds['odds']['Gem']['overall']
    assert 'set1_match' in odds['odds']['combined']
    assert odds['odds']['score']['overall']
    assert odds['odds']['combined']['win_and_gems']


def test_trailing_sign_junk_after_argument_strip_is_cleaned_up():
    # Real bug: leftover "+ /" after stripping the embedded argument left labels
    # like "Handicap gemowy + /" unmapped.
    raw = make_raw_match([
        game('Handicap gemowy + / 3', 3.0, [('-3', 1.9), ('+3', 1.9)]),
        game('1. set - handicap gemowy + 2', 2.0, [('-2', 1.9), ('+2', 1.9)]),
    ])

    odds = betfan_tennis.tennis_match(raw).odds

    assert odds['odds']['Gem']['handicap']
    assert odds['odds']['Gem']['set1_handicap']

