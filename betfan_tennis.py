from datetime import datetime
import json
import tennis_functions

class tennis_match:
    def __init__(self,tennis_match,bukmacher="betfan"):
        with open('config/tennis_dictionary.json') as dict_file:
            tennis_dictionary=json.load(dict_file)
        self.dictionary=tennis_dictionary
        
        self.tennis_match=tennis_match
        self.player1 = self.get_player(0)
        self.player2 = self.get_player(1)
        self.player1_raw = self.tennis_match['data']['event']['eventName'].split(' - ')[0].strip()
        self.player2_raw = self.tennis_match['data']['event']['eventName'].split(' - ')[1].strip()
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
          self.player1_raw+' - liczba gemów':{'name':'Gem','cat1':'player1','type':'und_ov','suffix':True},
          self.player2_raw+' - liczba gemów':{'name':'Gem','cat1':'player2','type':'und_ov','suffix':True},
           '1. set – poniżej/powyżej gemów':{'name':'Gem','cat1':'1st_set','type':'und_ov','suffix':True},
          
           'Kto więcej asów serwisowych?':{'name':'Ace','cat1':'handicap','type':'und_ov'},
           'Liczba asów w meczu':{'name':'Ace','cat1':'overall','type':'und_ov'},
           self.player1_raw+' liczba asów w meczu':{'name':'Ace','cat1':'player1','type':'und_ov'},
           self.player2_raw+' liczba asów w meczu':{'name':'Ace','cat1':'player2','type':'und_ov'},
           'Poniżej/powyżej asów serwisowych w 1. secie':{'name':'Ace','cat1':'1st_set','type':'und_ov','suffix':True},
           
           'Poniżej/powyżej podwójnych błędów serwisowych w meczu':{'name':'DF','cat1':'overall','type':'und_ov','suffix':True},
           self.player1_raw+' poniżej/powyżej podwójnych błędów':{'name':'DF','cat1':'player1','type':'und_ov','suffix':True},
           self.player2_raw+' poniżej/powyżej podwójnych błędów':{'name':'DF','cat1':'player2','type':'und_ov','suffix':True},
           'Więcej podwójnych błędów serwisowych w meczu (3-drogowo)':{'name':'DF','cat1':'more'},
           
           'Poniżej/powyżej przełamań w meczu':{'name':'Breaks','cat1':'overall','type':'und_ov','suffix':True},
           'Liczba przegranych gemów serwisowych - poniżej/powyżej':{'name':'Breaks','cat1':'overall','type':'und_ov','suffix':True},

           self.player1_raw+' poniżej/powyżej przełamań w meczu':{'name':'Breaks','cat1':'player1','type':'und_ov'},
           self.player2_raw+' poniżej/powyżej przełamań w meczu':{'name':'Breaks','cat1':'player2','type':'und_ov'},
           
           'Poniżej/powyżej tie-breaków w meczu':{'name':'TB','cat1':'overall','type':'und_ov','suffix':True},
           'Zwycięzca i poniżej/powyżej gemów':{'name':'win_and_gems','cat1':'overall','suffix':True}
          }
        self.tournament = self.get_tournament()
        self.date = self.get_date()
        self.odds_org = self.correct_input_odds(self.get_odds_org())
        self.odds = self.get_odds()
        #self.odds_converted = self.convert_odds()


        
    def get_player(self,number):
            player=self.tennis_match['data']['event']['eventName'].split(' - ')[number]
            player=self.get_player_from_dictionary(player)
            #print ('"',player,'": ["',player,'"],',sep='')
            return player
    def get_tournament(self):
        tournament = self.tennis_match['data']['event']['categoryName']
        return tournament
    
    def get_date(self):
        ts=self.tennis_match['data']['event']['eventStart']/1000
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

        if normalized == '1. set - liczba gemów':
            return {'name': 'Gem', 'cat1': '1st_set', 'type': 'und_ov', 'suffix': True}

        if normalized.startswith(p1 + ' - liczba gemów'):
            return {'name': 'Gem', 'cat1': 'player1', 'type': 'und_ov', 'suffix': True}
        if normalized.startswith(p2 + ' - liczba gemów'):
            return {'name': 'Gem', 'cat1': 'player2', 'type': 'und_ov', 'suffix': True}

        if normalized.endswith('wygra przynajmniej jeden set') or normalized.endswith('wygra co najmniej jednego seta'):
            return {'name': 'Sets', 'cat1': 'at_least_one_set', 'type': 'simple', 'suffix': False}
        if normalized.endswith('wygra dokładnie jednego seta'):
            return {'name': 'Sets', 'cat1': 'exactly1', 'type': 'simple', 'suffix': False}
        if normalized.endswith('wygra dokładnie dwa sety'):
            return {'name': 'Sets', 'cat1': 'exactly2', 'type': 'simple', 'suffix': False}

        return None

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
            if argument is not None and (argument!=0.0 or (argument==0.0 and odd_name.startswith('Handicap gemowy'))):
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
                        parts = market.split(' ')
                        if len(parts) >= 2:
                            odd_n, value = parts[0], parts[1]
                        else:
                            odd_n = market
                            value = ''
                    elif '+' in market:
                        odd_n='Powyżej'
                        value=market.replace('+','')                     
                    else:
                        if ' ' in market:
                            odd_n,value=market.rsplit(' ',1)
                        else:
                            odd_n = market
                            value = ''
                    #print (odd_n,value)
                    if odd_n not in odds_converted['odds'][name][cat1]:
                        odds_converted['odds'][name][cat1][odd_n]={}
                    odds_converted['odds'][name][cat1][odd_n][value]=self.odds_org['odds'][raw_name][market]
        return odds_converted

    def get_odds_org(self):
        odds={}
        odds['player1']=self.player1_raw
        odds['player2']=self.player2_raw
        odds['date']=self.date
        odds['odds']={}
        odds['arguments']={}
        
        for eventGame in self.tennis_match['data']['event']['games']:
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
            
    def print_odds_converted(self,filename=None):
        tennis_functions.print_odds_converted(self,filename)
