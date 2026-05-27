#!/usr/bin/python
# coding: utf-8

import json
from datetime import datetime, timezone

import connect_to_postgres as connect_to_wp_db
import iforbet_tennis
import tennis_functions
import os

BASE_URL = 'https://totalbet.pl/dealer'

OUT_FILE_NAME = 'totalbet_odds.csv'
ODDS_JSON_PATH = 'totalbet_tennis_one_game.json'
ODDS_ORG_JSON_PATH = 'totalbet_tennis_org_one_game.json'
BUKMACHER = 'totalbet'

INCLUDE_TOURNAMENT_KEYWORDS = [
    'atp',
    'wta',
    'roland garros',
    'french open',
    'wimbledon',
    'us open',
    'australian open',
]

EXCLUDE_TOURNAMENT_KEYWORDS = ['itf', 'challenger']
DOUBLES_TOURNAMENT_KEYWORDS = ['debel', 'doubles', 'double', 'mikst', 'mixed']
SKIP_DOUBLES = os.getenv('TOTALBET_SKIP_DOUBLES', '1') == '1'

if SKIP_DOUBLES:
    EXCLUDE_TOURNAMENT_KEYWORDS = EXCLUDE_TOURNAMENT_KEYWORDS + DOUBLES_TOURNAMENT_KEYWORDS


def _cleanup_legacy_invalid_rows(conn):
        cur = conn.cursor()
        cur.execute(
                """
                DELETE FROM odds
                WHERE bukmacher = %s
                    AND (
                        name LIKE '%%, %% - suma gemów'
                        OR name LIKE '%%, %% - suma asów%%'
                        OR name LIKE '🔥 %%'
                    )
                """,
                (BUKMACHER,),
        )
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        if deleted:
                print('Usunieto starych niepoprawnych rekordow totalbet:', deleted)


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


def _iso_to_epoch_ms(value):
    if not value:
        return int(datetime.now(tz=timezone.utc).timestamp() * 1000)

    if isinstance(value, (int, float)):
        return int(float(value) * 1000)

    text = str(value)
    if text.endswith('Z'):
        text = text.replace('Z', '+00:00')

    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return int(datetime.now(tz=timezone.utc).timestamp() * 1000)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return int(dt.timestamp() * 1000)


def _extract_outcomes_from_grid(grid):
    outcomes = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return

        if not isinstance(node, dict):
            return

        if node.get('type') == 'outcome':
            odd_raw = node.get('odds')
            try:
                odd_value = float(odd_raw)
            except (TypeError, ValueError):
                return

            outcome_name = (node.get('name') or '').strip()
            if outcome_name:
                outcomes.append({'outcomeName': outcome_name, 'outcomeOdds': odd_value})

            return

        for value in node.values():
            if isinstance(value, (list, dict)):
                walk(value)

    walk(grid)
    return outcomes


def _get_tennis_uuid():
    categories = tennis_functions.read_api(f'{BASE_URL}/bdata/v1/bet/categories/popular-sports')
    for sport in categories.get('data', {}).get('sports', []):
        if sport.get('name') == 'Tenis ziemny' and sport.get('uuid'):
            return sport['uuid']
    raise RuntimeError('Nie znaleziono UUID kategorii Tenis ziemny w Totalbet API')


def _read_all_events(tennis_uuid):
    all_events = []
    page = 1

    while True:
        url = f'{BASE_URL}/bdata/v1/bet/events?category_uuid={tennis_uuid}&type=prematch&page={page}'
        payload = tennis_functions.read_api(url)

        data = payload.get('data', {})
        all_events.extend(data.get('events', []))

        meta = payload.get('_meta', {})
        pagination = meta.get('pagination', {})
        total_pages = int(pagination.get('total_pages', 1) or 1)

        if page >= total_pages:
            break

        page += 1

    return all_events


def _convert_event_to_iforbet_shape(event_uuid):
    payload = tennis_functions.read_api(f'{BASE_URL}/bdata/v1/bet/events/{event_uuid}')
    event = payload.get('data', {}).get('event', {})

    event_name = event.get('name', '')
    start_ms = _iso_to_epoch_ms(event.get('start_at'))

    path = event.get('path', [])
    tournament_name = path[-1]['name'] if path else ''

    event_games = []
    for component in event.get('component_lists', []):
        game_name = (component.get('name') or '').strip()
        if not game_name:
            continue

        outcomes = _extract_outcomes_from_grid(component.get('grid', []))
        if not outcomes:
            continue

        event_games.append(
            {
                'gameName': game_name,
                'argument': None,
                'outcomes': outcomes,
            }
        )

    return {
        'data': {
            'eventId': event_uuid,
            'eventName': event_name,
            'eventStart': start_ms,
            'category3Name': tournament_name,
            'eventGames': event_games,
        }
    }


def main():
    conn = connect_to_wp_db.connect_to_db()
    _cleanup_legacy_invalid_rows(conn)

    all_odds = []
    all_odds_org = []

    tennis_uuid = _get_tennis_uuid()
    events = _read_all_events(tennis_uuid)

    print('MECZY:', len(events))
    print('FILTR include:', INCLUDE_TOURNAMENT_KEYWORDS)
    print('FILTR exclude:', EXCLUDE_TOURNAMENT_KEYWORDS)

    total_seen = 0
    filtered_out = 0
    processed = 0

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

        for event in events:
            total_seen += 1

            event_name = event.get('name', '')
            if ' - ' not in event_name:
                continue

            tournament_name = ''
            path = event.get('path', [])
            if path:
                tournament_name = path[-1].get('name', '')

            if not _is_allowed_tournament_name(
                tournament_name,
                include_keywords=INCLUDE_TOURNAMENT_KEYWORDS,
                exclude_keywords=EXCLUDE_TOURNAMENT_KEYWORDS,
            ):
                filtered_out += 1
                continue

            event_uuid = event.get('uuid')
            if not event_uuid:
                continue

            try:
                match_details = _convert_event_to_iforbet_shape(event_uuid)
                if not match_details.get('data', {}).get('eventGames'):
                    continue

                match_obj = iforbet_tennis.tennis_match(match_details, bukmacher=BUKMACHER)
                all_odds.append(match_obj.odds)
                all_odds_org.append(match_obj.odds_org)
                match_obj.print_odds_converted(outfile)
                processed += 1
            except Exception as exc:
                print('Blad dla', event_uuid, sep='\t')
                print(exc)
                continue

    print('MECZY przetworzone:', processed)
    print('MECZY odfiltrowane:', filtered_out)
    print('MECZY sprawdzone:', total_seen)

    with open(ODDS_JSON_PATH, 'w') as odds_json_file:
        json.dump(all_odds, odds_json_file)

    with open(ODDS_ORG_JSON_PATH, 'w') as odds_org_json_file:
        json.dump(all_odds_org, odds_org_json_file)

    players, dates = tennis_functions.read_players_and_dates(OUT_FILE_NAME)
    tennis_functions.delete_players_and_dates(conn, players, dates, BUKMACHER)
    tennis_functions.insert_to_db_from_file_new(conn, OUT_FILE_NAME)
    conn.close()


if __name__ == '__main__':
    main()
