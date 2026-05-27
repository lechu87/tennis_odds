from datetime import datetime
import tennis_functions
import sys

class tennis_match:
    def __init__(self, tennis_match):
        self.bukmacher = 'betclic'
        self.tennis_match = tennis_match
        self.player1, self.player1_short = self.get_player(0)
        self.player2, self.player2_short = self.get_player(1)
        self.tournament = self.get_tournament()
        self.date = self.get_date()
        self.dictionary = {'poniżej': 'Poniżej', 'powyżej': 'Powyżej'}
        self.dictionary[self.player1_short] = self.player1
        self.dictionary[self.player2_short] = self.player2
        self.odds_dict = {
            'Asy Powyżej/Poniżej': {'name': 'Ace', 'cat1': 'overall', 'type': 'und_ov'},
            'Asy': {'name': 'Ace', 'cat1': 'overall', 'type': 'und_ov'},
            'Liczba asów': {'name': 'Ace', 'cat1': 'overall', 'type': 'und_ov'},
            'Liczba asów serwisowych': {'name': 'Ace', 'cat1': 'overall', 'type': 'und_ov'},
            'Suma asów': {'name': 'Ace', 'cat1': 'overall', 'type': 'und_ov'},
            'Łączna liczba gemów': {'name': 'Gem', 'cat1': 'overall', 'type': 'und_ov'},
            'Liczba setów': {'name': 'Sets', 'cat1': 'exactly', 'type': 'simple'},
            'Czy obaj zawodnicy wygrają seta w meczu': {'name': 'Sets', 'cat1': 'both_players'},
            'Wynik w setach': {'name': 'score', 'cat1': 'overall', 'type': 'simple'},
            'Zwycięzca meczu': {'name': 'win', 'cat1': 'overall', 'type': 'simple'},
            'Najwięcej asów': {'name': 'Ace', 'cat1': 'player'},
            'Ile asów zaserwuje zawodnik 1 w meczu': {'name': 'Ace', 'cat1': 'player1', 'type': 'und_ov'},
            'Ile asów zaserwuje zawodnik 2 w meczu': {'name': 'Ace', 'cat1': 'player2', 'type': 'und_ov'},
            'Suma Gemów Gracz 1': {'name': 'Gem', 'cat1': 'player1'},
            'Suma Gemów Gracz 2': {'name': 'Gem', 'cat1': 'player2'},
            'Zwycięzca 1. seta': {'name': 'Sets', 'cat1': 'set1'},
            'Zwycięzca seta': {'name': 'Sets', 'cat1': 'set1'},
            'Zwycięzca 2. seta': {'name': 'Sets', 'cat1': 'set2'},
            'Handicap': {'name': 'Sets', 'cat1': 'handicap', 'type': 'und_ov'},
            'Handicap setowy': {'name': 'Sets', 'cat1': 'handicap', 'type': 'und_ov'},
            'Handicap w gemach': {'name': 'Gem', 'cat1': 'handicap', 'type': 'und_ov'},
            self.player1 + ' wygra seta': {'name': 'Sets', 'cat1': 'player1'},
            self.player2 + ' wygra seta': {'name': 'Sets', 'cat1': 'player2'},
            'Liczba przełamań': {'name': 'Breaks', 'cat1': 'overall', 'type': 'und_ov'},
            'Liczba przełamań zawodnika 1': {'name': 'Breaks', 'cat1': 'player1', 'type': 'und_ov'},
            'Liczba przełamań zawodnika 2': {'name': 'Breaks', 'cat1': 'player2', 'type': 'und_ov'},
            'Tie-break w meczu': {'name': 'TB', 'cat1': 'overall'},
            'Set 1. Tie Break': {'name': 'TB', 'cat1': '1st_set'},
            'Zwycięzca i poniżej/powyżej gemów': {
                'name': 'combined',
                'cat1': 'win_and_gems',
                'cat2': 'overall',
                'type': 'und_ov',
            },
            'Wygra 1. seta / Zwycięzca meczu': {'name': 'combined', 'cat1': 'set1_match', 'type': 'simple'},
            'Zawodnik wygra 1. seta 6-0, 6-1, 6-2 lub wygra mecz': {
                'name': 'combined',
                'cat1': 'set1_big_or_match',
                'type': 'simple',
            },
            'Zawodnik ma przewagę 2 setów lub wygra mecz': {
                'name': 'combined',
                'cat1': 'two_sets_or_match',
                'type': 'simple',
            },
        }
        self.raw_markets=tennis_match['grouped_markets']
        self.odds=self.get_odds()

    def _resolve_dynamic_meta(self, raw_name):
        normalized = self.del_space(raw_name or '')
        lowered = normalized.lower()

        if normalized == '1. Set':
            return {'name': 'Sets', 'cat1': 'set1', 'type': 'simple'}
        if normalized == '2. Set':
            return {'name': 'Sets', 'cat1': 'set2', 'type': 'simple'}

        if lowered.endswith('wygra seta'):
            prefix = normalized[:-len('wygra seta')].strip()
            if prefix == self.player1:
                return {'name': 'Sets', 'cat1': 'player1', 'type': 'simple'}
            if prefix == self.player2:
                return {'name': 'Sets', 'cat1': 'player2', 'type': 'simple'}
            return {'name': 'Sets', 'cat1': 'player', 'type': 'simple'}

        if lowered.endswith('- liczba asów'):
            player_label = normalized[:-len('- Liczba asów')].strip()
            if player_label == self.player1:
                cat1 = 'player1'
            elif player_label == self.player2:
                cat1 = 'player2'
            else:
                cat1 = 'player'
            return {'name': 'Ace', 'cat1': cat1, 'type': 'und_ov'}

        if 'zwyciezca meczu' in lowered and 'suma asów' in lowered:
            return {'name': 'combined', 'cat1': 'win_and_aces', 'type': 'simple'}

        return None
        
    def del_space(self,text):
        text=' '.join(text.split())
        return text
        #self.player2 = model
    def get_player(self,number):
        player=self.del_space(self.tennis_match['contestants'][number]['name'])
        short_player=self.del_space(self.tennis_match['contestants'][number]['short_name'])
        #player=' '.join(player_raw.split())
        #print ('"',player,'": ["',player,'"],',sep='')
        return player,short_player

    def get_tournament(self):
        tournament = self.del_space(self.tennis_match['competition']['name'].strip())
        return tournament
    def get_date(self):
        data_str = self.tennis_match['date']
        data_obj = datetime.strptime(data_str, '%Y-%m-%dT%H:%M:%SZ')
        data_str=data_obj.strftime("%Y-%m-%d")
        #print (data_obj)
        return data_str
    
    def standarize_str(self,text):
        if text not in ['Zwycięzca 1. seta','Set 1. Tie Break','Liczba gemów w 1. secie','Dokładny wynik 1. seta','Przegrana w 1. secie i wygrana w meczu',]:
            for key in self.dictionary.keys():
                #text=' '.join(text.split()).lower().replace(key, self.dictionary[key])
                text=' '.join(text.split()).replace(key, self.dictionary[key])
        return text
    
    def get_odds(self):
        odds_converted={}
        odds_converted['tournament']=self.tournament
        odds_converted['player1']=self.player1
        odds_converted['player2']=self.player2
        odds_converted['odds']={}
        odds_converted['bukmacher_name']='betclic'
        odds_converted['date']=self.date
        for odd_name in self.raw_markets:
            raw_name=self.del_space(odd_name['name'])
            meta = self.odds_dict.get(raw_name)
            if meta is None:
                meta = self._resolve_dynamic_meta(raw_name)
            if meta is None:
                print ("Brak w słowniku: ",raw_name,file=sys.stderr)

            name=meta['name'] if meta is not None else self.standarize_str(raw_name)
            if name not in odds_converted['odds']:
                odds_converted['odds'][name]={}
            cat1=meta['cat1'] if meta is not None else 'other'
            if cat1 not in odds_converted['odds'][name]:
                odds_converted['odds'][name][cat1]={}
            typ=meta.get('type','simple') if meta is not None else 'simple'
            
            for market in odd_name['markets']:
                for selections in market['selections']:
                    for selection in selections:
                        #print (selection)
                        if typ=='simple':
                            odd_name=self.standarize_str(selection['name'])
                            if ' ' in odd_name and odd_name.split()[1] in self.player1.lower():
                                odd_name=self.player1
                            if ' ' in odd_name and odd_name.split()[1] in self.player2.lower():
                                odd_name=self.player2
                            odd=selection['odds']
                            if odd_name not in odds_converted['odds'][name][cat1]:
                                odds_converted['odds'][name][cat1][odd_name]=odd
                        else:
                            odd_name,value=self.standarize_str(selection['name']).rsplit(' ',1)
                            if ' ' in odd_name and odd_name.split()[1] in self.player1.lower():
                                odd_name=self.player1
                            if ' ' in odd_name and odd_name.split()[1] in self.player2.lower():
                                odd_name=self.player2
                            odd=selection['odds']
                            if odd_name not in odds_converted['odds'][name][cat1]:
                                odds_converted['odds'][name][cat1][odd_name]={}
                            odds_converted['odds'][name][cat1][odd_name][value]=odd
        return odds_converted

    def print_odds_converted(self,filename):
        tennis_functions.print_odds_converted(self,filename)

    def delete_odds_from_db(self):
        tennis_functions.delete_odds_from_db(self)
    def delete_odds_from_maria_db(self,conn):
        tennis_functions.delete_odds_from_maria_db(self,conn)

    def insert_odds_converted_to_maria_db(self,conn):
        tennis_functions.insert_odds_converted_to_maria_db(self,conn)

    def insert_odds_converted_to_db(self):
        tennis_functions.insert_odds_converted_to_db(self)

    def create_database_for_odds(self):
        import sqlite3
        conn = sqlite3.connect('betclic.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='odds';")
        if not c.fetchone():
            c.execute('''CREATE TABLE odds
             (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             tournament TEXT, 
             player1 TEXT, 
             player2 TEXT, 
             name TEXT, 
             cat1 TEXT, 
             cat2 TEXT, 
             value TEXT, 
             odd REAL, 
             bukmacher TEXT, 
             date TEXT);''')
            

