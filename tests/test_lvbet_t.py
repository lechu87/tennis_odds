"""Unit tests for the pure market-mapping logic in lvbet_t._convert_match_to_odds."""
import lvbet_t


def test_match_winner_market_maps_to_win_overall():
    dictionary = {'players': {'Rafael Nadal': ['Rafael Nadal'], 'Novak Djokovic': ['Novak Djokovic']}}
    match = {
        'home_labels': ['Rafael Nadal'],
        'away_labels': ['Novak Djokovic'],
        'sports_groups_ids': [4, 10, 20],
        'date': '2026-06-01T12:00:00+00:00',
    }
    sports_groups_by_id = {4: 'Tennis', 10: 'ATP', 20: 'Roland Garros'}
    markets = [
        {
            'name': 'Match Winner',
            'line': None,
            'selections': [
                {'name': 'Rafael Nadal', 'rate': {'decimal': 1.5}},
                {'name': 'Novak Djokovic', 'rate': {'decimal': 2.5}},
            ],
        },
    ]

    odds, _ = lvbet_t._convert_match_to_odds(match, markets, sports_groups_by_id, dictionary)

    assert odds['tournament'] == 'Roland Garros'
    assert odds['player1'] == 'Rafael Nadal'
    assert odds['player2'] == 'Novak Djokovic'
    assert odds['odds']['win']['overall']['Rafael Nadal'] == 1.5


def test_total_games_market_parses_over_under_selection():
    dictionary = {'players': {}}
    match = {'home_labels': ['A'], 'away_labels': ['B'], 'sports_groups_ids': [4], 'date': '2026-06-01T12:00:00+00:00'}
    sports_groups_by_id = {4: 'Tennis'}
    markets = [
        {
            'name': 'Total Games',
            'line': 22.5,
            'selections': [
                {'name': 'Over (22.5)', 'rate': {'decimal': 1.9}},
                {'name': 'Under (22.5)', 'rate': {'decimal': 1.9}},
            ],
        },
    ]

    odds, _ = lvbet_t._convert_match_to_odds(match, markets, sports_groups_by_id, dictionary)

    gem_odds = odds['odds']['Gem']['overall']
    assert gem_odds['Powyzej']['22.5'] == 1.9
    assert gem_odds['Ponizej']['22.5'] == 1.9


def test_unknown_market_falls_back_to_other_category():
    dictionary = {'players': {}}
    match = {'home_labels': ['A'], 'away_labels': ['B'], 'sports_groups_ids': [4], 'date': '2026-06-01T12:00:00+00:00'}
    sports_groups_by_id = {4: 'Tennis'}
    markets = [
        {'name': 'Brand New Market', 'line': None, 'selections': [{'name': 'Yes', 'rate': {'decimal': 1.2}}]},
    ]

    odds, _ = lvbet_t._convert_match_to_odds(match, markets, sports_groups_by_id, dictionary)

    assert 'other' in odds['odds']['Brand New Market']
