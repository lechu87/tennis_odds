import re
from datetime import datetime
import json
import tennis_functions

class tennis_match:
    def __init__(self,tennis_match,bukmacher="iforbet"):
        with open('config/tennis_dictionary.json') as dict_file:
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

            
