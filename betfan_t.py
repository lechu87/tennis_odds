#!/usr/bin/python
# coding: utf-8

import betfan_tennis
import json
import tennis_functions
import connect_to_postgres as connect_to_wp_db
import os


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
SKIP_DOUBLES = os.getenv('BETFAN_SKIP_DOUBLES', '1') == '1'

if SKIP_DOUBLES:
    EXCLUDE_TOURNAMENT_KEYWORDS = EXCLUDE_TOURNAMENT_KEYWORDS + DOUBLES_TOURNAMENT_KEYWORDS

with open('tennis_dictionary.json') as dict_file:
    tennis_dictionary=json.load(dict_file)
#print (tennis_dictionary)

#all_games=tennis_functions.read_api('https://api.etoto.pl/rest/market/categories/multi/9887,8916,24139,16321,10128/events')

#print (all_games)
all_odds=[]
all_odds_converted=[]
all_odds_org = []
tmp_games=[]
#print ("MECZY:",len(all_games['data']))
conn=connect_to_wp_db.connect_to_db()
out_file_name='betfan_odds.csv'
outfile=open(out_file_name,'w')
print('tournament','player1','player2','name','cat1','cat2','value','odd','bukmacher','date',sep='\t',file=outfile)


all_categories=tennis_functions.read_api('https://api-v2.betfan.pl/api/v1/market/categories/all')
tennis_tournaments=[]
for category in all_categories['data']['categories']:
    if category['sportName']!='Tenis':
        continue

    category_name = category.get('categoryName', '')
    if not _is_allowed_tournament_name(
        category_name,
        include_keywords=INCLUDE_TOURNAMENT_KEYWORDS,
        exclude_keywords=EXCLUDE_TOURNAMENT_KEYWORDS,
    ):
        continue

    if category_name.lower() == 'tenis':
        continue

    if 'zakł. długoterminowe' in category_name.lower():
        continue

    tennis_tournaments.append(category['categoryId'])
all_games=set()
for tournament in tennis_tournaments:
    tournament_games=tennis_functions.read_api(f'https://api-v2.betfan.pl/api/v1/market/categories/{tournament}/events?date=&hours=')
    for events in tournament_games.get('data', {}).get('categories', [{}])[0].get('events', []):
        all_games.add(events['eventId'])

print('MECZY:', len(all_games))
print('FILTR include:', INCLUDE_TOURNAMENT_KEYWORDS)
print('FILTR exclude:', EXCLUDE_TOURNAMENT_KEYWORDS)

processed = 0

for match in sorted(all_games):
    #if match!=19980170:
    #    continue
    #match_url=f'https://api-v2.betfan.pl/api/v1/market/events/{match}'
    #match_details=tennis_functions.read_api(match_url)
    #match_obj=betfan_tennis.tennis_match(match_details,bukmacher="betfan")
        
    try:
        #match_id=match
        #if match!=19980170:
        #    continue
        #print (match['id'])
        match_url=f'https://api-v2.betfan.pl/api/v1/market/events/{match}'
        #wszystkie
        #print (match_id)
        match_details=tennis_functions.read_api(match_url)
        #pomijam typy bez zawodników, czyli ogólne na turniej itp
        if ' - ' not in match_details['data']['event']['eventName']:
            continue
        match_obj=betfan_tennis.tennis_match(match_details,bukmacher="betfan")
        #print ("JESTEM TU")
        #print (match_obj.tennis_match)
        #tymczasowo sobie wrzucę do listy:
        #tmp_games.append(match_obj(match_details))
        all_odds.append(match_obj.odds)
        #all_odds_converted.append(match_obj.odds_converted)
        all_odds_org.append(match_obj.odds_org)
        match_obj.print_odds_converted(outfile)
        processed += 1
        #match_obj.delete_odds_from_db()
        #match_obj.delete_odds_from_maria_db(conn)
        #match_obj.insert_odds_converted_to_db()
        #match_obj.insert_odds_converted_to_maria_db(conn)
        
    except Exception as e:
        print ("Błąd dla ",match_url,sep='\t')
        print (e)
        continue
outfile.close()

print('MECZY przetworzone:', processed)

json.dump(all_odds,open('betfan_tennis.json','w'))
#json.dump(all_odds_converted,open('iforbet_tennis_converted.json','w'))
json.dump(all_odds_org,open('betfan_tennis_org.json','w'))
#match_obj.insert_odds_converted_to_db()
players,dates=tennis_functions.read_players_and_dates(out_file_name)
tennis_functions.delete_players_and_dates(conn,players,dates,'betfan')
tennis_functions.insert_to_db_from_file_new(conn,out_file_name)
conn.close()

