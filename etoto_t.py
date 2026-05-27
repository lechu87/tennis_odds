#!/usr/bin/python
# coding: utf-8

import os

import iforbet_tennis
from bookmaker_runner import run_iforbet_family


DOUBLES_TOURNAMENT_KEYWORDS = ['debel', 'doubles', 'double', 'mikst', 'mixed']
BASE_EXCLUDE_TOURNAMENT_KEYWORDS = ['itf', 'challenger']
SKIP_DOUBLES = os.getenv('ETOTO_SKIP_DOUBLES', '1') == '1'

exclude_keywords = list(BASE_EXCLUDE_TOURNAMENT_KEYWORDS)
if SKIP_DOUBLES:
    exclude_keywords.extend(DOUBLES_TOURNAMENT_KEYWORDS)


run_iforbet_family(
    categories_url='https://api.etoto.pl/rest/market/categories/multi/5/events?gamesClass=major',
    event_url_template='https://api.etoto.pl/rest/market/events/{match_id}',
    bukmacher='etoto',
    out_file_name='data/odds/etoto_odds.csv',
    odds_json_path='data/raw/etoto_tennis.json',
    odds_org_json_path='data/raw/etoto_tennis_org.json',
    parser_module=iforbet_tennis,
    event_id_env_var='ETOTO_EVENT_ID',
    include_tournament_keywords=[
        'atp',
        'wta',
        'roland garros',
        'french open',
        'wimbledon',
        'us open',
        'australian open',
    ],
    exclude_tournament_keywords=exclude_keywords,
)

