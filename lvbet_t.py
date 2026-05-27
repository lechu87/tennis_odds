#!/usr/bin/python
# coding: utf-8

import json
import os
import re
from datetime import datetime

import connect_to_postgres as connect_to_wp_db
import tennis_functions

BASE_URL = 'https://offer.lvbet.pl/client-api/v5'
MATCHES_URL = BASE_URL + '/matches'
MARKETS_URL_TEMPLATE = BASE_URL + '/matches/{match_id}/markets'
SPORTS_GROUPS_URL = BASE_URL + '/sports-groups'

BUKMACHER = 'lvbet'
OUT_FILE_NAME = 'lvbet_odds.csv'
ODDS_JSON_PATH = 'lvbet_tennis.json'
ODDS_ORG_JSON_PATH = 'lvbet_tennis_org.json'
MATCH_ID_ENV_VAR = 'LVBET_MATCH_ID'

INCLUDE_TOURNAMENT_KEYWORDS = [
    'atp',
    'wta',
    'grand slam',
    'roland',
    'french',
    'wimbledon',
    'us open',
    'australian',
]

EXCLUDE_TOURNAMENT_KEYWORDS = ['itf', 'challenger']
DOUBLES_TOURNAMENT_KEYWORDS = ['debel', 'doubles', 'double', 'mikst', 'mixed']
SKIP_DOUBLES = os.getenv('LVBET_SKIP_DOUBLES', '1') == '1'

if SKIP_DOUBLES:
    EXCLUDE_TOURNAMENT_KEYWORDS = EXCLUDE_TOURNAMENT_KEYWORDS + DOUBLES_TOURNAMENT_KEYWORDS

# Same root tennis sports-group used by lvbet matches endpoint.
TENNIS_SPORT_GROUP_ID = 4

MARKET_MAP = {
    'match winner': {'name': 'win', 'cat1': 'overall', 'type': 'simple'},
    'set betting': {'name': 'score', 'cat1': 'overall', 'type': 'simple'},
    '1 set - correct score': {'name': 'score', 'cat1': 'set1', 'type': 'simple'},
    '1 set - winner': {'name': 'Sets', 'cat1': 'set1', 'type': 'simple'},
    '1st set/match': {'name': 'combined', 'cat1': 'set1_match', 'type': 'simple'},
    'total games': {'name': 'Gem', 'cat1': 'overall', 'type': 'und_ov'},
    '1 set total games': {'name': 'Gem', 'cat1': '1st_set', 'type': 'und_ov'},
    'player 1 total games': {'name': 'Gem', 'cat1': 'player1', 'type': 'und_ov'},
    'player 2 total games': {'name': 'Gem', 'cat1': 'player2', 'type': 'und_ov'},
    '1 set player 1 total games': {'name': 'Gem', 'cat1': '1st_set_player1', 'type': 'und_ov'},
    '1 set player 2 total games': {'name': 'Gem', 'cat1': '1st_set_player2', 'type': 'und_ov'},
    'total sets': {'name': 'Sets', 'cat1': 'overall', 'type': 'und_ov'},
    'tie-breaks total in match': {'name': 'TB', 'cat1': 'overall', 'type': 'und_ov'},
    'games handicap': {'name': 'Gem', 'cat1': 'handicap', 'type': 'simple'},
    '1 set games handicap': {'name': 'Gem', 'cat1': 'set1_handicap', 'type': 'simple'},
    'sets handicap': {'name': 'Sets', 'cat1': 'handicap', 'type': 'simple'},
    'score after first two sets': {'name': 'score', 'cat1': 'after_set2', 'type': 'simple'},
    'total games odd/even': {'name': 'Gem', 'cat1': 'odd_even', 'type': 'simple'},
    '1 set total games odd/even': {'name': 'Gem', 'cat1': 'set1_odd_even', 'type': 'simple'},
    'player 1: will win at least one set': {'name': 'Sets', 'cat1': 'player1_at_least_1', 'type': 'simple'},
    'player 2: will win at least one set': {'name': 'Sets', 'cat1': 'player2_at_least_1', 'type': 'simple'},
    'player 1: will win at least two sets': {'name': 'Sets', 'cat1': 'player1_at_least_2', 'type': 'simple'},
    'player 2: will win at least two sets': {'name': 'Sets', 'cat1': 'player2_at_least_2', 'type': 'simple'},
    'player will lose 1st set and win match': {'name': 'combined', 'cat1': 'lose_set1_win_match', 'type': 'simple'},
    'player 1: match winner and total games': {'name': 'combined', 'cat1': 'player1_win_total_games', 'type': 'und_ov'},
    'player 2: match winner and total games': {'name': 'combined', 'cat1': 'player2_win_total_games', 'type': 'und_ov'},
}


def _normalize_market_name(raw_name):
    name = (raw_name or '').strip().lower()
    name = re.sub(r'\s+', ' ', name)
    return name


def _as_clean_list(value):
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


def _is_h2h_match(match):
    home_candidates = _as_clean_list(match.get('home_labels') or match.get('home'))
    away_candidates = _as_clean_list(match.get('away_labels') or match.get('away'))

    if not home_candidates or not away_candidates:
        return False

    home_name = home_candidates[0]
    away_name = away_candidates[0]
    if not home_name or not away_name:
        return False

    # Outright entries carry tournament-like participant labels.
    if 'outright' in home_name.lower() or 'outright' in away_name.lower():
        return False

    return True


def _cleanup_legacy_invalid_rows(conn):
    cur = conn.cursor()
    outright_pattern = '%outright%'
    cur.execute(
        """
        DELETE FROM odds
        WHERE bukmacher = %s
          AND (
            coalesce(player2, '') = ''
            OR lower(coalesce(tournament, '')) LIKE %s
            OR lower(coalesce(player1, '')) LIKE %s
          )
        """,
        (BUKMACHER, outright_pattern, outright_pattern),
    )
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    if deleted:
        print('Usunieto starych niepoprawnych rekordow lvbet:', deleted)


def _is_allowed_tournament_name(name, include_keywords=None, exclude_keywords=None):
    normalized = (name or '').strip().lower()
    if not normalized:
        return False

    include_keywords = include_keywords or []
    exclude_keywords = exclude_keywords or []

    if exclude_keywords and any(keyword in normalized for keyword in exclude_keywords):
        return False

    if include_keywords and not any(keyword in normalized for keyword in include_keywords):
        return False

    return True


def _normalize_player(player, dictionary):
    if player in dictionary['players']:
        return player

    for canonical_name, aliases in dictionary['players'].items():
        if player in aliases:
            return canonical_name

    print(f'["{player}"]')
    return player


def _extract_players(match, dictionary):
    home_candidates = _as_clean_list(match.get('home_labels') or match.get('home'))
    away_candidates = _as_clean_list(match.get('away_labels') or match.get('away'))

    home_raw = home_candidates[0] if home_candidates else ''
    away_raw = away_candidates[0] if away_candidates else ''

    home = _normalize_player(home_raw, dictionary)
    away = _normalize_player(away_raw, dictionary)
    return home, away


def _extract_tournament_name(match, sports_groups_by_id):
    ids = match.get('sports_groups_ids') or []
    labels = [sports_groups_by_id.get(sid, '') for sid in ids if sports_groups_by_id.get(sid)]

    # Usually structure is: [Tennis, Country/Category, Tournament].
    # Prefer the deepest non-empty label.
    for label in reversed(labels):
        if label and label.lower() != 'tennis':
            return label

    return labels[-1] if labels else ''


def _parse_date_iso(date_iso):
    if not date_iso:
        return ''
    try:
        return datetime.fromisoformat(date_iso).strftime('%Y-%m-%d')
    except ValueError:
        return date_iso.split('T')[0]


def _parse_und_ov_selection(selection_name):
    match = re.match(
        r'^(Over|Under)\s*(?:\(?\s*([-+]?\d+(?:\.\d+)?)\s*\)?)$',
        selection_name.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return None, None

    side = match.group(1).lower()
    value = match.group(2)
    normalized_side = 'Powyzej' if side == 'over' else 'Ponizej'
    return normalized_side, value


def _convert_match_to_odds(match, markets, sports_groups_by_id, dictionary):
    player1, player2 = _extract_players(match, dictionary)
    tournament = _extract_tournament_name(match, sports_groups_by_id)
    date = _parse_date_iso(match.get('date'))

    odds = {
        'player1': player1,
        'player2': player2,
        'tournament': tournament,
        'date': date,
        'odds': {},
        'bukmacher_name': BUKMACHER,
    }

    odds_org = {
        'player1': player1,
        'player2': player2,
        'tournament': tournament,
        'date': date,
        'odds': {},
        'arguments': {},
        'bukmacher_name': BUKMACHER,
    }

    for market in markets:
        market_name = market.get('name', '').strip()
        if not market_name:
            continue

        line = market.get('line')
        selections = market.get('selections') or []

        if market_name not in odds_org['odds']:
            odds_org['odds'][market_name] = {}
            odds_org['arguments'][market_name] = line

        market_meta = MARKET_MAP.get(
            _normalize_market_name(market_name),
            {'name': market_name, 'cat1': 'other', 'type': 'simple'},
        )

        mapped_name = market_meta['name']
        cat1 = market_meta['cat1']
        market_type = market_meta['type']

        odds['odds'].setdefault(mapped_name, {}).setdefault(cat1, {})

        for selection in selections:
            selection_name = (selection.get('name') or '').strip()
            if not selection_name:
                continue

            decimal = (selection.get('rate') or {}).get('decimal')
            if decimal is None:
                continue

            try:
                odd = float(decimal)
            except (TypeError, ValueError):
                continue

            odds_org['odds'][market_name][selection_name] = odd

            if market_type == 'und_ov':
                side, value = _parse_und_ov_selection(selection_name)
                if side is None:
                    odds['odds'][mapped_name][cat1][selection_name] = odd
                    continue

                odds['odds'][mapped_name][cat1].setdefault(side, {})
                odds['odds'][mapped_name][cat1][side][value] = odd
            else:
                odds['odds'][mapped_name][cat1][selection_name] = odd

    return odds, odds_org


class _OddsPrinter:
    def __init__(self, odds):
        self.odds = odds


def main():
    with open('tennis_dictionary.json', 'r', encoding='utf-8') as dict_file:
        tennis_dictionary = json.load(dict_file)

    conn = connect_to_wp_db.connect_to_db()
    _cleanup_legacy_invalid_rows(conn)

    sports_groups = tennis_functions.read_api(SPORTS_GROUPS_URL)
    sports_groups_by_id = {
        entry['sports_group_id']: entry.get('label', '')
        for entry in sports_groups
        if isinstance(entry, dict) and entry.get('sports_group_id') is not None
    }

    matches = tennis_functions.read_api(
        MATCHES_URL + f'?is_live=false&sports_groups_ids={TENNIS_SPORT_GROUP_ID}'
    )

    all_odds = []
    all_odds_org = []

    total_seen = 0
    filtered_out = 0
    processed = 0

    match_id_filter = os.getenv(MATCH_ID_ENV_VAR)

    print('MECZY:', len(matches))
    print('FILTR include:', INCLUDE_TOURNAMENT_KEYWORDS)
    print('FILTR exclude:', EXCLUDE_TOURNAMENT_KEYWORDS)

    with open(OUT_FILE_NAME, 'w') as outfile:
        print(
            'tournament',
            'player1',
            'player2',
            'name',
            'cat1',
            'cat2',
            'value',
            'odd',
            'bukmacher',
            'date',
            sep='\t',
            file=outfile,
        )

        for match in matches:
            total_seen += 1

            match_id = match.get('match_id')
            if not match_id:
                continue

            if match_id_filter and str(match_id) != str(match_id_filter):
                continue

            if not _is_h2h_match(match):
                continue

            tournament_name = _extract_tournament_name(match, sports_groups_by_id)
            if not _is_allowed_tournament_name(
                tournament_name,
                include_keywords=INCLUDE_TOURNAMENT_KEYWORDS,
                exclude_keywords=EXCLUDE_TOURNAMENT_KEYWORDS,
            ):
                filtered_out += 1
                continue

            try:
                markets = tennis_functions.read_api(MARKETS_URL_TEMPLATE.format(match_id=match_id))
                odds, odds_org = _convert_match_to_odds(match, markets, sports_groups_by_id, tennis_dictionary)

                # Skip empty events after market parsing.
                if not odds['odds']:
                    continue

                all_odds.append(odds)
                all_odds_org.append(odds_org)

                printer = _OddsPrinter(odds)
                tennis_functions.print_odds_converted(printer, outfile)
                processed += 1
            except Exception as exc:
                print('Blad dla', match_id, sep='\t')
                print(exc)
                continue

    print('MECZY przetworzone:', processed)
    print('MECZY odfiltrowane:', filtered_out)
    print('MECZY sprawdzone:', total_seen)

    with open(ODDS_JSON_PATH, 'w', encoding='utf-8') as odds_json_file:
        json.dump(all_odds, odds_json_file)

    with open(ODDS_ORG_JSON_PATH, 'w', encoding='utf-8') as odds_org_json_file:
        json.dump(all_odds_org, odds_org_json_file)

    players, dates = tennis_functions.read_players_and_dates(OUT_FILE_NAME)
    tennis_functions.delete_players_and_dates(conn, players, dates, BUKMACHER)
    tennis_functions.insert_to_db_from_file_new(conn, OUT_FILE_NAME)
    conn.close()


if __name__ == '__main__':
    main()
