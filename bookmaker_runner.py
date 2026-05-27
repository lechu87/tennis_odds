#!/usr/bin/python
# coding: utf-8

import json
import traceback

import connect_to_postgres as connect_to_wp_db
import tennis_functions


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


def run_iforbet_family(
    categories_url,
    event_url_template,
    bukmacher,
    out_file_name,
    odds_json_path,
    odds_org_json_path,
    parser_module,
    event_id_env_var=None,
    include_tournament_keywords=None,
    exclude_tournament_keywords=None,
):
    all_games = tennis_functions.read_api(categories_url)
    all_odds = []
    all_odds_org = []

    print('MECZY:', len(all_games.get('data', [])))
    print('FILTR include:', include_tournament_keywords or [])
    print('FILTR exclude:', exclude_tournament_keywords or [])

    conn = connect_to_wp_db.connect_to_db()
    total_seen = 0
    filtered_out = 0
    processed = 0

    with open(out_file_name, 'w') as outfile:
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

        event_id_filter = None
        if event_id_env_var:
            import os

            event_id_filter = os.getenv(event_id_env_var)

        for match in all_games.get('data', []):
            match_url = ''
            try:
                total_seen += 1
                match_id = match['eventId']
                if event_id_filter and str(match_id) != event_id_filter:
                    continue

                tournament_name = match.get('category3Name', '')
                if not _is_allowed_tournament_name(
                    tournament_name,
                    include_keywords=include_tournament_keywords,
                    exclude_keywords=exclude_tournament_keywords,
                ):
                    filtered_out += 1
                    continue

                match_url = event_url_template.format(match_id=match_id)
                match_details = tennis_functions.read_api(match_url)

                if ' - ' not in match_details['data']['eventName']:
                    continue

                match_obj = parser_module.tennis_match(match_details, bukmacher=bukmacher)
                all_odds.append(match_obj.odds)
                all_odds_org.append(match_obj.odds_org)
                match_obj.print_odds_converted(outfile)
                processed += 1
            except Exception as exc:
                print('Blad dla', match_url, sep='\t')
                print(exc)
                traceback.print_exc()
                continue

    print('MECZY przetworzone:', processed)
    print('MECZY odfiltrowane:', filtered_out)
    print('MECZY sprawdzone:', total_seen)

    with open(odds_json_path, 'w') as odds_json_file:
        json.dump(all_odds, odds_json_file)

    with open(odds_org_json_path, 'w') as odds_org_json_file:
        json.dump(all_odds_org, odds_org_json_file)

    players, dates = tennis_functions.read_players_and_dates(out_file_name)
    tennis_functions.delete_players_and_dates(conn, players, dates, bukmacher)
    tennis_functions.insert_to_db_from_file_new(conn, out_file_name)
    conn.close()
