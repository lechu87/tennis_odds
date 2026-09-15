import requests
import csv
def delete_odds_from_db(self):
    import sqlite3
    conn = sqlite3.connect('betclic.db')
    c = conn.cursor()
    c.execute("DELETE FROM odds WHERE player1=? AND player2=? AND bukmacher=? AND date=?",(self.odds['player1'],self.odds['player2'],self.odds['bukmacher_name'],self.odds['date']))
    conn.commit()
    #print ("deleted player1:",self.odds['player1'],"player2:",self.odds['player2'],"bukmacher:",self.odds['bukmacher_name'],"date:",self.odds['date'])
    conn.close()

def delete_odds_from_maria_db(self, conn):
    c = conn.cursor()
    query = "DELETE FROM odds WHERE player1 = %s AND player2 = %s AND bukmacher = %s AND date = %s"
    values = (self.odds['player1'], self.odds['player2'], self.odds['bukmacher_name'], self.odds['date'])
    c.execute(query, values)
    conn.commit()
    #print("Deleted - player1:", self.odds['player1'], "player2:", self.odds['player2'], "bukmacher:", self.odds['bukmacher_name'], "date:", self.odds['date'])
    #conn.close()

def read_players_and_dates(filename):
    header=False
    players={}
    dates={}
    for lines in open(filename):
        #print (lines)
        row=lines.strip().split('\t')
        if not header:
            header=row
            continue
        line=dict(zip(header,row))
        players[line['player1']]={}
        players[line['player2']]={}
        dates[line['date']]={}

    return players,dates

def delete_players_and_dates(conn,players,dates,bukmacher):
    if not players or not dates:
        print("Usunięto:", 0)
        return

    c = conn.cursor()
    chunk_size = 500
    total_deleted = 0
    player_list = list(players.keys())

    for date in dates.keys():
        for i in range(0, len(player_list), chunk_size):
            chunk = player_list[i:i + chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            query = (
                f"DELETE FROM odds WHERE bukmacher = %s AND date = %s "
                f"AND (player1 IN ({placeholders}) OR player2 IN ({placeholders}))"
            )
            values = [bukmacher, date] + chunk + chunk
            c.execute(query, values)
            total_deleted += c.rowcount

    conn.commit()
    print("Usunięto:", total_deleted)
    c.close()


HISTORY_KEY_FIELDS = ('tournament', 'player1', 'player2', 'name', 'cat1', 'cat2', 'value', 'date')


def _history_key(row):
    """Natural key identifying one odds line, scoped to a single bookmaker."""
    return tuple(row[field] for field in HISTORY_KEY_FIELDS)


def _normalize_odd(value):
    """Round to the same precision as the DECIMAL(10,4) column so string/Decimal formatting never causes false diffs."""
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def rows_changed_since_last_snapshot(rows, last_odds):
    """Keep only rows whose odd is new or differs from the last recorded value.

    rows: dicts read from the bookmaker's CSV output (tournament..date columns).
    last_odds: {history_key: last_known_odd} as returned by fetch_last_odds_map().

    If the same natural key appears more than once in `rows` (a bookmaker-side data
    quality issue, since cat2/value should disambiguate selections), only the last
    occurrence in the file is considered - matching "last write wins" semantics instead
    of depending on non-deterministic DB tie-breaking.
    """
    deduped = {}
    for row in rows:
        deduped[_history_key(row)] = row

    changed = []
    for key, row in deduped.items():
        previous = last_odds.get(key)
        current = _normalize_odd(row['odd'])
        if previous is None or previous != current:
            changed.append(row)
    return changed


def fetch_last_odds_map(conn, bukmacher):
    """Latest known odd per natural key for one bookmaker, from odds_history."""
    c = conn.cursor()
    c.execute(
        """
        SELECT DISTINCT ON (tournament, player1, player2, name, cat1, cat2, value, date)
               tournament, player1, player2, name, cat1, cat2, value, date, odd
        FROM odds_history
        WHERE bukmacher = %s
        ORDER BY tournament, player1, player2, name, cat1, cat2, value, date, observed_at DESC, id DESC
        """,
        (bukmacher,),
    )
    last_odds = {}
    for tournament, player1, player2, name, cat1, cat2, value, date, odd in c.fetchall():
        key = (tournament, player1, player2, name, cat1, cat2, value, str(date))
        last_odds[key] = _normalize_odd(odd)
    c.close()
    return last_odds


def append_odds_history(conn, filename, bukmacher):
    """Append only the odds that changed (or are new) since the last recorded snapshot.

    Keeps odds_history slim and meaningful instead of duplicating a full dump on every run.
    """
    with open(filename, 'r') as file:
        reader = csv.DictReader(file, delimiter='\t')
        rows = list(reader)

    last_odds = fetch_last_odds_map(conn, bukmacher)
    changed_rows = rows_changed_since_last_snapshot(rows, last_odds)

    if not changed_rows:
        print("Historia kursów bez zmian:", 0)
        return 0

    c = conn.cursor()
    sql = (
        "INSERT INTO odds_history (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    values = [
        (
            row['tournament'], row['player1'], row['player2'], row['name'],
            row['cat1'], row['cat2'], row['value'], row['odd'], row['bukmacher'], row['date'],
        )
        for row in changed_rows
    ]
    c.executemany(sql, values)
    conn.commit()
    c.close()
    print("Historia kursów zapisana (zmiany):", len(changed_rows))
    return len(changed_rows)


def insert_to_db_from_file_new(conn,filename):
    c = conn.cursor()
    with open(filename, 'r') as file:
        reader = csv.reader(file, delimiter='\t')
        next(reader)  # Pominięcie nagłówka pliku CSV (opcjonalne)

        # Inicjalizacja wsadu
        batch_size = 1000  # Rozmiar wsadu (liczba wierszy)
        batch_data = []  # Lista przechowująca dane wsadu
        sql = "INSERT INTO odds (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        # Przeglądanie wierszy pliku CSV i dodawanie ich do wsadu
        for row in reader:
            tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher_name, date = row
            values = (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher_name, date)
            batch_data.append(values)

            # Wykonanie wsadu, jeśli osiągnięto rozmiar wsadu
            if len(batch_data) == batch_size:
                # Tworzenie zapytania SQL
    
                # Wykonanie wsadu
                c.executemany(sql, batch_data)
                conn.commit()

                # Wyczyszczenie wsadu po wykonaniu
                batch_data = []

        # Wykonanie ewentualnego pozostałego wsadu
        if batch_data:
            c.executemany(sql, batch_data)
            conn.commit()

    # Zamknięcie kursora i połączenia




def insert_odds_converted_to_maria_db(self, conn):
    c = conn.cursor()
    for name in self.odds['odds']:
        for cat1 in self.odds['odds'][name]:
            for cat2 in self.odds['odds'][name][cat1]:
                if isinstance(self.odds['odds'][name][cat1][cat2], dict):
                    for value in self.odds['odds'][name][cat1][cat2]:
                        odd = self.odds['odds'][name][cat1][cat2][value]
                        query = "INSERT INTO odds (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                        values = (self.odds['tournament'], self.odds['player1'], self.odds['player2'], name, cat1, cat2, value, odd, self.odds['bukmacher_name'], self.odds['date'])
     #                   print(query, values)
                        c.execute(query, values)
                else:
                    odd = self.odds['odds'][name][cat1][cat2]
                    query = "INSERT INTO odds (tournament, player1, player2, name, cat1, cat2, value, odd, bukmacher, date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    values = (self.odds['tournament'], self.odds['player1'], self.odds['player2'], name, cat1, cat2, '', odd, self.odds['bukmacher_name'], self.odds['date'])
                    #print(query, values)
                    c.execute(query, values)

    conn.commit()


#insert odds converted to db if not exists
def insert_odds_converted_to_db(self):
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


def read_api(url):
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.1000.0 Safari/537.36",
    "Accept": "application/json",
}
    timeout = 20
    retries = 3

    last_error = None
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == retries - 1:
                raise

    raise last_error

def print_odds_converted(self,filename=None):
        for name in self.odds['odds']:
            for cat1 in self.odds['odds'][name]:
                for cat2 in self.odds['odds'][name][cat1]:
                    if type(self.odds['odds'][name][cat1][cat2]) is dict:
                        for value in self.odds['odds'][name][cat1][cat2]:
                            odd=self.odds['odds'][name][cat1][cat2][value]
                            if filename is None:
                                print(self.odds['tournament'],self.odds['player1'],self.odds['player2'],name,cat1,cat2,value,odd,self.odds['bukmacher_name'],self.odds['date'],sep='\t')
                            else:
                                print(self.odds['tournament'],self.odds['player1'],self.odds['player2'],name,cat1,cat2,value,odd,self.odds['bukmacher_name'],self.odds['date'],sep='\t',file=filename)
                    else:
                        odd=self.odds['odds'][name][cat1][cat2]
                        if filename is None:
                            print(self.odds['tournament'],self.odds['player1'],self.odds['player2'],name,cat1,cat2,'',odd,self.odds['bukmacher_name'],self.odds['date'],sep='\t')
                        else:
                            print(self.odds['tournament'],self.odds['player1'],self.odds['player2'],name,cat1,cat2,'',odd,self.odds['bukmacher_name'],self.odds['date'],sep='\t',file=filename)
