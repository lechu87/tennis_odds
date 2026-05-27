import sys
import time
import re
import requests
from datetime import datetime
from collections import defaultdict
import urllib.request as urllib2
import json
import tennis_functions

class tennis_match:
    def __init__(self,tennis_match,bukmacher="iforbet"):
        with open('tennis_dictionary.json') as dict_file:
            tennis_dictionary=json.load(dict_file)
        self.dictionary=tennis_dictionary
        
        self.tennis_match=tennis_match
        self.player1 = self.get_player(0)
        self.player2 = self.get_player(1)
        self.player1_raw = self.tennis_match['data']['eventName'].split(' - ')[0]
        self.player2_raw = self.tennis_match['data']['eventName'].split(' - ')[1]
        self.bukmacher = bukmacher
        
        
        self.odds_dict={'Zwycięzca':{'name':'win','cat1':'overall','type':'simple'},
           'Dokładny wynik':{'name':'score','cat1':'overall'},
          self.player1_raw+' wygra seta' :{'name':'Sets','cat1':'player1'},
          self.player2_raw+' wygra seta' :{'name':'Sets','cat1':'player2'},
          'Liczba setów':{'name':'Sets','cat1':'exactly'},
          'Liczba setów poniżej/powyżej':{'name':'Sets','cat1':'overall','type':'und_ov','suffix':True},
           'Handicap setowy':{'name':'Sets','cat1':'handicap','type':'und_ov'},
           
           'Handicap gemowy':{'name':'Gem','cat1':'handicap','type':'und_ov'},
          'poniżej/powyżej gemów':{'name':'Gem','cat1':'overall','type':'und_ov','suffix':True},
          self.player1_raw+' poniżej/powyżej gemów':{'name':'Gem','cat1':'player1','type':'und_ov','suffix':True},
          self.player2_raw+' poniżej/powyżej gemów':{'name':'Gem','cat1':'player2','type':'und_ov','suffix':True},
           '1. set – poniżej/powyżej gemów':{'name':'Gem','cat1':'1st_set','type':'und_ov','suffix':True},
          
           'Więcej asów serwisowych w meczu (handicap)':{'name':'Ace','cat1':'handicap','type':'und_ov'},
           'Poniżej/powyżej asów w meczu':{'name':'Ace','cat1':'overall','type':'und_ov','suffix':True},
           'Suma asów serwisowych':{'name':'Ace','cat1':'overall','type':'und_ov','suffix':True},
            'Suma asów w meczu':{'name':'Ace','cat1':'overall','type':'und_ov','suffix':True},

           self.player1_raw+' poniżej/powyżej asów':{'name':'Ace','cat1':'player1','type':'und_ov','suffix':True},
           self.player1_raw+' - Suma asów w meczu':{'name':'Ace','cat1':'player1','type':'und_ov','suffix':True},
           self.player1_raw+' suma asów serwisowych':{'name':'Ace','cat1':'player1','type':'und_ov','suffix':True},

           self.player2_raw+' poniżej/powyżej asów':{'name':'Ace','cat1':'player2','type':'und_ov','suffix':True},
           self.player2_raw+' - Suma asów w meczu':{'name':'Ace','cat1':'player2','type':'und_ov','suffix':True},
           self.player2_raw+' suma asów serwisowych':{'name':'Ace','cat1':'player2','type':'und_ov','suffix':True},

           'Poniżej/powyżej asów serwisowych w 1. secie':{'name':'Ace','cat1':'1st_set','type':'und_ov','suffix':True},
           
           'Poniżej/powyżej podwójnych błędów w meczu':{'name':'DF','cat1':'overall','type':'und_ov','suffix':True},
           self.player1_raw+' poniżej/powyżej podwójnych błędów':{'name':'DF','cat1':'player1','type':'und_ov','suffix':True},
           self.player2_raw+' poniżej/powyżej podwójnych błędów':{'name':'DF','cat1':'player2','type':'und_ov','suffix':True},
           'Więcej podwójnych błędów serwisowych w meczu (3-drogowo)':{'name':'DF','cat1':'more'},
            'Poniżej/powyżej podwójnych błędów serwisowych w meczu':{'name':'DF','cat1':'overall','type':'und_ov','suffix':True},
             'Suma podwójnych błędów w meczu':{'name':'DF','cat1':'overall','type':'und_ov','suffix':True},
         
           'Poniżej/powyżej przełamań w meczu':{'name':'Breaks','cat1':'overall','type':'und_ov','suffix':True},
           'Liczba przegranych gemów serwisowych - poniżej/powyżej':{'name':'Breaks','cat1':'overall','type':'und_ov','suffix':True},

           self.player1_raw+' poniżej/powyżej przełamań w meczu':{'name':'Breaks','cat1':'player1','type':'und_ov','suffix':True},
           self.player1_raw+' przełamie serwis rywala poniżej/powyżej razy':{'name':'Breaks','cat1':'player1','type':'und_ov'},
           self.player1_raw+' suma przełamań serwisu':{'name':'Breaks','cat1':'player1','type':'und_ov'},


           self.player2_raw+' poniżej/powyżej przełamań w meczu':{'name':'Breaks','cat1':'player2','type':'und_ov','suffix':True},
           self.player2_raw+' przełamie serwis rywala poniżej/powyżej razy':{'name':'Breaks','cat1':'player2','type':'und_ov'},
           self.player2_raw+' suma przełamań serwisu':{'name':'Breaks','cat1':'player2','type':'und_ov'},

            'Suma przełamań serwisowych w meczu':{'name':'Breaks','cat1':'overall','type':'und_ov','suffix':True},
          
           'Poniżej/powyżej tie-breaków w meczu':{'name':'TB','cat1':'overall','type':'und_ov','suffix':True},
           'Zwycięzca i poniżej/powyżej gemów':{'name':'win_and_gems','cat1':'overall','suffix':True},

           # Totalbet label variants.
           'Suma gemów':{'name':'Gem','cat1':'overall','type':'und_ov','suffix':True},
           'Gemy - handicap':{'name':'Gem','cat1':'handicap','type':'simple'},
           '1 set - Suma gemów':{'name':'Gem','cat1':'1st_set','type':'und_ov','suffix':True},
           '1 set - Dokładny wynik':{'name':'score','cat1':'set1','type':'simple'},
           'Podwójny wynik (1. set/mecz)':{'name':'combined','cat1':'set1_match','type':'simple'},
           'Suma setów':{'name':'Sets','cat1':'overall','type':'und_ov','suffix':True},
           'Dokładna liczba setów':{'name':'Sets','cat1':'exactly','type':'simple'},
           '1 set - Zwycięzca':{'name':'Sets','cat1':'set1','type':'simple'},
           '2 set - Zwycięzca':{'name':'Sets','cat1':'set2','type':'simple'},
           'Wygra dokładnie 1 set':{'name':'Sets','cat1':'exactly1','type':'simple'},
           'Wygra dokładnie 2 sety':{'name':'Sets','cat1':'exactly2','type':'simple'},
           'Wygra seta':{'name':'Sets','cat1':'at_least_one_set','type':'simple'},
           'Suma gemów parzysta/nieparzysta':{'name':'Gem','cat1':'odd_even','type':'simple'},
           'Którykolwiek set do zera':{'name':'Sets','cat1':'set_to_nil','type':'simple'},
           'Zwycięzca + suma gemów':{'name':'combined','cat1':'win_and_gems','type':'und_ov','suffix':True}
          }
        self.tournament = self.get_tournament()
        self.date = self.get_date()
        self.odds_org = self.correct_input_odds(self.get_odds_org())
        self.odds = self.get_odds()
        #self.odds_converted = self.convert_odds()


        
    def get_player(self,number):
            player=self.tennis_match['data']['eventName'].split(' - ')[number].replace(' (Hit Dnia)','').replace(' (najwyższe kursy, 0% marży!)','')
            player=self.get_player_from_dictionary(player)
            #print ('"',player,'": ["',player,'"],',sep='')
            return player
    def get_tournament(self):
        tournament = self.tennis_match['data']['category3Name']
        return tournament
    
    def get_date(self):
        ts=self.tennis_match['data']['eventStart']/1000
        date=datetime.fromtimestamp(ts)
        formatted_date = date.strftime("%Y-%m-%d")
        return formatted_date
    #get best matching player from dictionary
    def get_player_from_dictionary(self,player):
        if player in self.dictionary['players']:
            return player
        else:
            for key in self.dictionary['players']:
                if player in self.dictionary['players'][key]:
                    return key
        print ('["'+player+'"]')
        return player
    def correct_input_odds(self,meczyk):
        to_add={}
        for odd_name in meczyk['odds']:
            if odd_name.startswith('Zwycięzca i poniżej/powyżej'):
                to_add[odd_name]={}
                gems=odd_name.split(' ')[-2]
                for el in meczyk['odds'][odd_name]:
                    to_add[odd_name][el+' '+gems+' gemów']=meczyk['odds'][odd_name][el]
        for k in to_add:
            meczyk['odds'].pop(k)
            meczyk['odds'].update(to_add)
        
        return meczyk

    def _normalize_cat1(self, cat1):
        if cat1 == 'overal':
            return 'overall'
        return cat1

    def _resolve_dynamic_meta(self, raw_name2):
        normalized = (raw_name2 or '').strip().lower()
        p1 = self.player1_raw.lower()
        p2 = self.player2_raw.lower()

        def _match_player_pattern(player, suffix_regex):
            return re.match(r'^' + re.escape(player) + r'\s*[-–]\s*' + suffix_regex, normalized) is not None

        if normalized == 'handicap sety':
            return {'name': 'Sets', 'cat1': 'handicap', 'type': 'simple', 'suffix': False}

        if _match_player_pattern(p1, r'suma gem[óo]w') or normalized.startswith(p1 + ' suma gemów'):
            return {'name': 'Gem', 'cat1': 'player1', 'type': 'und_ov', 'suffix': True}
        if _match_player_pattern(p2, r'suma gem[óo]w') or normalized.startswith(p2 + ' suma gemów'):
            return {'name': 'Gem', 'cat1': 'player2', 'type': 'und_ov', 'suffix': True}

        if _match_player_pattern(p1, r'suma as[óo]w') or normalized.startswith(p1 + ' suma asów'):
            return {'name': 'Ace', 'cat1': 'player1', 'type': 'und_ov', 'suffix': True}
        if _match_player_pattern(p2, r'suma as[óo]w') or normalized.startswith(p2 + ' suma asów'):
            return {'name': 'Ace', 'cat1': 'player2', 'type': 'und_ov', 'suffix': True}

        if _match_player_pattern(p1, r'poniżej/powyżej as[óo]w'):
            return {'name': 'Ace', 'cat1': 'player1', 'type': 'und_ov', 'suffix': True}
        if _match_player_pattern(p2, r'poniżej/powyżej as[óo]w'):
            return {'name': 'Ace', 'cat1': 'player2', 'type': 'und_ov', 'suffix': True}

        return None

    def get_odds_new(self):
        import math
        def remove_argument_tokens(odd_name, argument, should_remove):
            # Nie próbujemy nic usuwać jeśli nie trzeba
            if not should_remove:
                return odd_name

            name = odd_name if isinstance(odd_name, str) else ('' if odd_name is None else str(odd_name))
            tokens = set()

            # surowa reprezentacja
            if argument is not None:
                tokens.add(str(argument))

                # spróbuj float z obsługą przecinka
                s = str(argument).strip().replace(',', '.')
                arg_float = None
                try:
                    arg_float = float(s)
                    if not math.isnan(arg_float) and not math.isinf(arg_float):
                        tokens.add(str(arg_float))          # np. "2.0" lub "2.5"
                        tokens.add(str(-arg_float))         # np. "-2.0" lub "-2.5"
                except (ValueError, TypeError):
                    arg_float = None

                # int jeśli to liczba całkowita
                if arg_float is not None and arg_float.is_integer():
                    i = int(arg_float)
                    tokens.add(str(i))
                    tokens.add('-' + str(i))
                else:
                    # może to był czysty int jako string
                    try:
                        i = int(str(argument))
                        tokens.add(str(i))
                        tokens.add('-' + str(i))
                    except (ValueError, TypeError):
                        pass

            # usuwaj dłuższe tokeny najpierw (żeby np. "-10" nie ucięło "10")
            for t in sorted(tokens, key=len, reverse=True):
                name = name.replace(t, '')

            # porządki
            name = (name.replace('  ', ' ')
                        .replace(' / +', '')
                        .replace(' + / -', '')
                        .strip())
            return name

        odds_converted = {
            'player1': self.player1,
            'player2': self.player2,
            'tournament': self.tournament,
            'date': self.date,
            'odds': {},
            'bukmacher_name': self.bukmacher
        }

        odds_org_odds = self.odds_org.get('odds', {})
        arguments = self.odds_org.get('arguments', {})

        for raw_name, markets in odds_org_odds.items():
            argument = arguments.get(raw_name, None)

        # usuwamy argument tylko gdy jest (argument is not None) i:
        # - jest różny od 0.0, albo
        # - jest 0.0 i to "Handicap gemowy"
        should_remove = (
            argument is not None and (
                argument != 0.0 or
                (argument == 0.0 and isinstance(raw_name, str) and raw_name.startswith('Handicap gemowy'))
            )
        )

        raw_name2 = remove_argument_tokens(raw_name, argument, should_remove)

        meta = self.odds_dict.get(raw_name2, {})
        name = meta.get('name', raw_name2)
        cat1 = meta.get('cat1', 'other')
        typ = meta.get('type', 'simple')
        suffix = meta.get('suffix', False)

        odds_converted['odds'].setdefault(name, {}).setdefault(cat1, {})

        for market, value in markets.items():
            if typ == 'simple':
                odds_converted['odds'][name][cat1][market] = value

            elif typ == 'und_ov':
                # Rozbicie "ponad/powyżej/powyzej ... <wartość> ..." na (odd_n, value)
                odd_n = None
                val_str = None

                if suffix:
                    # Bierzemy pierwsze dwa tokeny: np. "Powyżej 21.5 gemów" -> ("Powyżej", "21.5")
                    parts = market.split()
                    if len(parts) >= 2:
                        odd_n = parts[0]
                        val_str = parts[1]
                    else:
                        # awaryjnie jak wcześniej
                        parts = market.rsplit(' ', 1)
                        if len(parts) == 2:
                            odd_n, val_str = parts[0], parts[1]
                else:
                    parts = market.rsplit(' ', 1)
                    if len(parts) == 2:
                        odd_n, val_str = parts[0], parts[1]
                    else:
                        # awaryjnie spróbuj pierwsze 2
                        parts = market.split()
                        if len(parts) >= 2:
                            odd_n = ' '.join(parts[:-1])
                            val_str = parts[-1]

                if odd_n is None or val_str is None:
                    # nie udało się zparsować – zapisz tak jak leci
                    odds_converted['odds'][name][cat1][market] = value
                    continue

                    odd_n = odd_n.replace('ponad', 'Powyżej').replace('poniżej', 'Poniżej')
                    odds_converted['odds'][name][cat1].setdefault(odd_n, {})
                    odds_converted['odds'][name][cat1][odd_n][val_str] = value

                else:
                    # nieznany typ – zapisz surowo
                    odds_converted['odds'][name][cat1][market] = value

        return odds_converted

    def get_odds(self):
        #meczyk=correct_input_odds(meczyk)
        odds_converted={}
        odds_converted['player1']=self.player1
        odds_converted['player2']=self.player2
        odds_converted['tournament']=self.tournament
        odds_converted['date']=self.date
        odds_converted['odds']={}
        odds_converted['bukmacher_name']=self.bukmacher
        for odd_name in self.odds_org['odds']:
            raw_name=odd_name
            argument=self.odds_org['arguments'][odd_name]
            if argument!=0.0 and argument or (argument==0.0 and odd_name.startswith('Handicap gemowy')):                
                raw_name2=odd_name.replace(str(argument),'').replace(str(float(argument)),'').replace(str(float(argument*-1)),'').replace(str(int(argument)),'').replace('-'+str(int(argument)),'').replace('  ',' ').replace(' / +','').replace(' + / -','').strip()
                #print ("usunąłem ",argument," z ",odd_name)
            else:
                raw_name2=odd_name
            meta = self.odds_dict.get(raw_name2)
            if meta is None:
                meta = self._resolve_dynamic_meta(raw_name2)

            if meta is not None:
                name = meta.get('name', raw_name2)
                cat1 = self._normalize_cat1(meta.get('cat1', 'other'))
                typ = meta.get('type', 'simple')
                suffix = meta.get('suffix', False)
            else:
                name = raw_name2
                cat1 = 'other'
                typ = 'simple'
                suffix = False
            
            if name not in odds_converted['odds']:
                odds_converted['odds'][name]={}
            if cat1 not in odds_converted['odds'][name]:
                odds_converted['odds'][name][cat1]={}
            #print(odds_converted)
            for market in self.odds_org['odds'][raw_name]:
                if typ=='simple':
                    odds_converted['odds'][name][cat1][market]=self.odds_org['odds'][raw_name][market]
                elif typ=='und_ov':
                    if suffix:
#                        market=market.replace(' przełamań w meczu','').replace(self.player1,'').replace(self.player2,'')
                        parts = market.split(' ')
                        if len(parts) >= 2:
                            odd_n, value = parts[0], parts[1]
                        else:
                            # Fallback for malformed labels, keep entry instead of failing whole match.
                            odd_n = market
                            value = ''
#                        print ("AAAAA",odd_n,value)
                    else:
                        if ' ' in market:
                            odd_n,value=market.rsplit(' ',1)
                        else:
                            odd_n = market
                            value = ''

                    if value == '' and argument is not None:
                        value = str(argument)
                    #print (odd_n,value)
                    odd_n=odd_n.replace('ponad','Powyżej').replace('poniżej','Poniżej')
                    if odd_n not in odds_converted['odds'][name][cat1]:
                        odds_converted['odds'][name][cat1][odd_n]={}
                    odds_converted['odds'][name][cat1][odd_n][value]=self.odds_org['odds'][raw_name][market]
        return odds_converted

    def get_odds_old(self):
        odds={}
        odds['player1']=self.player1
        odds['player2']=self.player2
        odds['date']=self.date
        odds['odds']={}
        for eventGame in self.tennis_match['data']['eventGames']:
            name=eventGame['gameName'].lower()
            if name.startswith("poniżej"):
                if "asów w meczu" in name:
                    name="asów"
                elif "błędów w meczu" in name:
                    name="df"
                else:
                    name=name.rsplit(' ')[-1]
                for outcome in eventGame['outcomes']:
                    outcomeName,ile=outcome['outcomeName'].split(' ')[0:2]        
                    outcomeName=outcomeName.replace('ponad','powyżej')
                    odd=outcome['outcomeOdds']
                    #print (name,outcomeName,ile,odd)
                    if name not in odds['odds']:
                        odds['odds'][name]={}
                    if outcomeName not in odds['odds'][name]:
                        odds['odds'][name][outcomeName]={}
                    odds['odds'][name][outcomeName][ile]=odd
            elif name.startswith("Handicap gemowy"):
                name=name.rsplit(' ')[0:2]
                for outcome in eventGame['outcomes']:
                    ile=outcome['outcomeName'].pop()
                    oucomeName=outcome['outcomeName']
                    odd=outcome['outcomeOdds']
                    if name not in odds['odds']:
                        odds['odds'][name]={}
                    if outcomeName not in odds['odds'][name]:
                        odds['odds'][name][outcomeName][ile]=odd
            else:    
                odd_name=name
                if odd_name not in odds['odds']:
                    odds['odds'][odd_name]={}
                for outcome in eventGame['outcomes']:
                    outcomeName=outcome['outcomeName'].replace('ponad','powyżej')

                    odd=outcome['outcomeOdds']
                    odds['odds'][odd_name][outcomeName]=odd
        return odds

    def get_odds_org(self):
        odds={}
        odds['player1']=self.player1_raw
        odds['player2']=self.player2_raw
        odds['date']=self.date
        odds['odds']={}
        odds['arguments']={}
        
        for eventGame in self.tennis_match['data']['eventGames']:
            name=eventGame['gameName']
            argument=eventGame['argument']
            odd_name=name
            if odd_name not in odds['odds']:
                odds['odds'][odd_name]={}
                odds['arguments'][odd_name]=argument
            for outcome in eventGame['outcomes']:
                outcomeName=outcome['outcomeName']
                odd=outcome['outcomeOdds']
                odds['odds'][odd_name][outcomeName]=odd
        return odds
    
    def convert_odds(self):
        odds_converted={}
        keys_to_remove=[]
        odds_converted['tournament']=self.tournament
        odds_converted['bukmacher_name']=self.bukmacher
        odds_converted['player1']=self.player1
        odds_converted['player2']=self.player2
        odds_converted['odds']={'win':{'overall':{self.player2:{self.odds['odds']['zwycięzca'].get(self.player2)}}}}
        odds_converted['odds']['win']['overall'][self.player1]={self.odds['odds']['zwycięzca'].get(self.player1)}
        keys_to_remove.append('zwycięzca')
        odds_converted['Ace']={'overall':{'over':{},'under':{}}}
        for und_ov in self.odds['odds'].get('asów',[]):
            #print ("und_ov:",und_ov)
            if und_ov=='Poniżej':
                typ='over'
            else:
                typ='under'
            for line in self.odds['odds']['asów'][und_ov]:
                odds_converted['Ace']['overall'][typ][float(line)]=self.odds['odds']['asów'][und_ov][line]
        #hubert hurkacz poniżej/powyżej 14.5 asów
        odds_converted['Ace']={'player1':{'over':{},'under':{}},'player2':{'over':{},'under':{}}}
        for key in self.odds['odds']:
            if 'poniżej/powyżej' in key and 'asów' in key:
                if self.player1.lower() in key:
                    player='player1'
                else:
                    player='player2'
                for k in self.odds['odds'][key]:
                    if 'Poniżej' in k:
                        und_ov='under'
                    else:
                        und_ov='over'
                    ile=k.split(' ')[1]
                    odds_converted['Ace'][player][und_ov][ile]=self.odds['odds'][key][k]

        odds_converted['Gem']={'overall':{'over':{},'under':{}}}
        if 'gemów' in self.odds['odds']:
            for gems in self.odds['odds']['gemów']['Poniżej']:
                odds_converted['Gem']['overall']['under'][gems]=self.odds['odds']['gemów']['Poniżej'][gems]
            for gems in self.odds['odds']['gemów']['Powyżej']:
                odds_converted['Gem']['overall']['over'][gems]=self.odds['odds']['gemów']['Powyżej'][gems]
        #'handicap gemowy -1.5': {'Sebastian Baez -1.5': 1.52,
          #'Pedro Cachin +1.5': 2.44},
        for k in self.odds['odds']:
            if k.startswith('handicap gemowy'):
                for key,odd in self.odds['odds'][k].items():
                    key,value=key.rsplit(' ',1)
                    if 'handicap' not in odds_converted['Gem']:
                        odds_converted['Gem']['handicap']={}
                    if key not in odds_converted['Gem']['handicap']:
                        odds_converted['Gem']['handicap'][key]={}
                    odds_converted['Gem']['handicap'][key][value]=odd
        return odds_converted

    def delete_odds_from_db(self):
        tennis_functions.delete_odds_from_db(self)
    def delete_odds_from_maria_db(self,conn):
        tennis_functions.delete_odds_from_maria_db(self,conn)

    def insert_odds_to_db(self,conn):
        tennis_functions.insert_odds_to_db(self,conn)
        #converted_to_maria_db(self,conn)

    def insert_odds_converted_to_maria_db(self,conn):
        tennis_functions.insert_odds_converted_to_maria_db(self,conn)

    def insert_odds_converted_to_db(self):
        tennis_functions.insert_odds_converted_to_db(self)
    def print_odds_converted(self,filename):
        tennis_functions.print_odds_converted(self,filename)

            
    def insert_odds_to_db_to_del(self):
        import sqlite3
        conn = sqlite3.connect('betclic.db')
        c = conn.cursor()
        for name in self.odds['odds']:
            for cat1 in self.odds['odds'][name]:
                for cat2 in self.odds['odds'][name][cat1]:
                    if type(self.odds['odds'][name][cat1][cat2]) is dict:
                        for value in self.odds['odds'][name][cat1][cat2]:
                            odd=self.odds['odds'][name][cat1][cat2][value]
                            c.execute("INSERT INTO odds (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date) VALUES (?,?,?,?,?,?,?,?,?,?)",(self.odds['tournament'],self.odds['player1'],self.odds['player2'],name,cat1,cat2,value,odd,self.odds['bukmacher_name'],self.odds['date']))
                    else:
                        odd=self.odds['odds'][name][cat1][cat2]
                        c.execute("INSERT INTO odds (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date) VALUES (?,?,?,?,?,?,?,?,?,?)",(self.odds['tournament'],self.odds['player1'],self.odds['player2'],name,cat1,cat2,'',odd,self.odds['bukmacher_name'],self.odds['date']))
        conn.commit()
        conn.close()
    
    #delete game if exists in db
    def delete_odds_from_db_to_del(self):
        import sqlite3
        conn = sqlite3.connect('betclic.db')
        c = conn.cursor()
        c.execute("DELETE FROM odds WHERE player1=? AND player2=? AND bukmacher=? AND date=?",(self.odds['player1'],self.odds['player2'],self.odds['bukmacher_name'],self.odds['date']))
        conn.commit()
        print ("deleted player1:",self.odds['player1'],"player2:",self.odds['player2'],"bukmacher:",self.odds['bukmacher_name'],"date:",self.odds['date'])
        conn.close()
