#!/usr/bin/python
# coding: utf-8

import sys
import json
import re
import time
import os
import struct
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import cloudscraper
except Exception:
    cloudscraper = None

try:
    import blackboxprotobuf
except Exception:
    blackboxprotobuf = None

import betclic_tennis
import connect_to_postgres as connect_to_wp_db
import tennis_functions

# Load tennis dictionary
with open('config/tennis_dictionary.json') as dict_file:
    tennis_dictionary = json.load(dict_file)

# Setup requests with timeout and retries
if cloudscraper is not None:
    session = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
else:
    session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
BASE_URL = 'https://www.betclic.pl'
TENNIS_URL = BASE_URL + '/tenis-stennis'
FAILED_URLS_FILE = 'data/runtime/betclic_failed_urls.txt'
REQUEST_DELAY_SECONDS = 0.35
BLOCK_COOLDOWN_SECONDS = 180
INCLUDE_LIVE = os.getenv('BETCLIC_INCLUDE_LIVE', '0') == '1'
BETCLIC_GRPC_MATCH_ENDPOINT = (
    'https://offering.begmedia.com/web/offering.access.api/'
    'offering.access.api.MatchService/GetMatchWithNotification'
)

ALLOWED_COMPETITION_KEYWORDS = (
    'atp',
    'wta',
    'french open',
    'roland garros',
    'wimbledon',
    'us open',
    'australian open',
)

EXCLUDED_COMPETITION_KEYWORDS = (
    'itf',
    'challenger',
)

DOUBLES_COMPETITION_KEYWORDS = (
    'debel',
    'doubles',
    'double',
    'mikst',
    'mixed',
)

SKIP_DOUBLES = os.getenv('BETCLIC_SKIP_DOUBLES', '1') == '1'


def extract_ng_state(html_content):
    """Extract ng-state JSON from HTML page"""
    try:
        match = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>',
                          html_content, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"Błąd podczas parsowania ng-state: {e}", file=sys.stderr)
    return {}


def fetch_page(url, attempts=1, retry_statuses=None):
    """Fetch URL and return HTML text with optional backoff retries."""
    retry_statuses = retry_statuses or set()
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=20)
            if response.status_code in retry_statuses and attempt < attempts:
                wait_seconds = min(10, 2 ** (attempt - 1))
                print(
                    f"Retry {attempt}/{attempts - 1} dla {url} po statusie {response.status_code}"
                    f" (czekam {wait_seconds}s)",
                    file=sys.stderr,
                )
                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            return response.text
        except Exception as e:
            last_error = e
            if attempt < attempts:
                wait_seconds = min(10, 2 ** (attempt - 1))
                print(
                    f"Retry {attempt}/{attempts - 1} dla {url} po błędzie: {e}"
                    f" (czekam {wait_seconds}s)",
                    file=sys.stderr,
                )
                time.sleep(wait_seconds)
                continue

    print(f"Błąd pobierania {url}: {last_error}", file=sys.stderr)
    return None


def is_allowed_competition_name(name):
    """Keep only ATP/WTA/Challenger competitions and skip ITF."""
    normalized = (name or '').strip().lower()
    if not normalized:
        return False
    if any(keyword in normalized for keyword in EXCLUDED_COMPETITION_KEYWORDS):
        return False
    if SKIP_DOUBLES and any(keyword in normalized for keyword in DOUBLES_COMPETITION_KEYWORDS):
        return False
    return any(keyword in normalized for keyword in ALLOWED_COMPETITION_KEYWORDS)


def extract_tennis_competitions(ng_state):
    """Extract allowed tennis competitions from sports catalog payload."""
    competitions = {}

    for key, val in ng_state.items():
        if not key.startswith('grpc:'):
            continue
        payload = val.get('response', val).get('payload', val.get('payload', {}))
        sports = payload.get('sports', []) if isinstance(payload, dict) else []
        for sport in sports:
            for category in sport.get('categories', []):
                for comp in category.get('competitions', []):
                    if comp.get('sportCode') != 'tennis' or not comp.get('competitionId'):
                        continue

                    competition_name = (
                        comp.get('competitionName')
                        or comp.get('name')
                        or category.get('name')
                        or ''
                    )
                    if not is_allowed_competition_name(competition_name):
                        continue

                    competition_id = str(comp['competitionId'])
                    competitions[competition_id] = competition_name

    return competitions


def collect_match_urls_from_competitions(competitions):
    """
    Collect match links by crawling each tennis competition page.
    This avoids missing events hidden behind infinite scroll on the main page.
    """
    all_links = set()

    for cid, competition_name in sorted(competitions.items(), key=lambda item: item[1].lower()):
        # Slug can be arbitrary as long as '-c<ID>' is present.
        comp_url = f"{BASE_URL}/tenis-stennis/x-c{cid}"
        html = fetch_page(comp_url, attempts=2, retry_statuses={403})
        if not html:
            continue

        links = re.findall(r'href="(/tenis-stennis/[^"]+m\d+)"', html)
        for link in links:
            all_links.add(BASE_URL + link)

        print(f"Turniej: {competition_name} -> {len(links)} linków", file=sys.stderr)
        time.sleep(REQUEST_DELAY_SECONDS)

    return sorted(all_links)


def normalize_date(date_str):
    """Normalize gRPC date (may have .0000000Z) to YYYY-MM-DDTHH:MM:SSZ"""
    if not date_str:
        return ''
    if '.' in date_str:
        return date_str.split('.')[0] + 'Z'
    return date_str


def _encode_varint(value):
    out = bytearray()
    while True:
        chunk = value & 0x7F
        value >>= 7
        if value:
            out.append(chunk | 0x80)
        else:
            out.append(chunk)
            break
    return bytes(out)


def _build_grpc_match_request(match_id, category_id, language='pl'):
    lang = (language or 'pl').encode('utf-8')
    cat = (category_id or '').encode('utf-8')

    message = b''
    message += b'\x08' + _encode_varint(int(match_id))
    message += b'\x12' + bytes([len(lang)]) + lang
    message += b'\x1a' + bytes([len(cat)]) + cat

    return b'\x00' + len(message).to_bytes(4, 'big') + message


def _grpc_headers():
    return {
        'referer': 'https://www.betclic.pl/',
        'origin': 'https://www.betclic.pl',
        'content-type': 'application/grpc-web+proto',
        'x-grpc-web': '1',
        'ngsw-bypass': '1',
        'x-bg-ref-brand': 'BETCLIC',
        'x-bg-ref-platform': 'DESKTOP',
        'x-bg-ref-regulator-zone': 'PL',
        'x-bg-regulation': 'PL',
        'user-agent': HEADERS['User-Agent'],
    }


def _decode_text(value):
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except Exception:
            return ''
    if isinstance(value, str):
        return value
    return ''


def _decode_fixed64_to_float(value):
    try:
        raw = int(value).to_bytes(8, 'little', signed=False)
        return round(struct.unpack('<d', raw)[0], 3)
    except Exception:
        return 0


def _extract_selections_from_proto_market_items(items):
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return []

    selections = []
    for item in items:
        if not isinstance(item, dict):
            continue
        oneof = item.get('1')
        if not isinstance(oneof, dict):
            continue
        selection = oneof.get('1')
        if not isinstance(selection, dict):
            continue

        name = _decode_text(selection.get('10') or selection.get('11'))
        odd = _decode_fixed64_to_float(selection.get('12'))
        if name and odd > 0:
            selections.append({'name': name, 'odds': odd})

    return selections


def fetch_additional_grouped_markets(match_id, category_id):
    """Fetch one Betclic subcategory via gRPC-web and map it into grouped_markets format."""
    if blackboxprotobuf is None:
        return []
    if not match_id or not category_id:
        return []

    try:
        payload = _build_grpc_match_request(match_id, category_id)
        response = session.post(
            BETCLIC_GRPC_MATCH_ENDPOINT,
            headers=_grpc_headers(),
            data=payload,
            stream=True,
            timeout=(15, 20),
        )
        response.raise_for_status()

        raw = b''
        frame = b''
        for chunk in response.iter_content(chunk_size=4096):
            if not chunk:
                continue
            raw += chunk
            if len(raw) < 5:
                continue
            frame_len = int.from_bytes(raw[1:5], 'big')
            if len(raw) >= 5 + frame_len:
                frame = raw[5:5 + frame_len]
                break

        if not frame:
            return []

        decoded, _ = blackboxprotobuf.decode_message(frame)
        match_payload = decoded.get('1', {}).get('1', {})
        subcategory = match_payload.get('11', {})
        proto_markets = subcategory.get('3', [])

        grouped_markets = []
        for market in proto_markets:
            if not isinstance(market, dict):
                continue

            market_name = _decode_text(market.get('2') or market.get('3'))
            selections = _extract_selections_from_proto_market_items(market.get('10'))
            if market_name and selections:
                grouped_markets.append({'name': market_name, 'markets': [{'selections': [selections]}]})

        return grouped_markets

    except Exception as e:
        print(
            f"Nie udało się dociągnąć kategorii {category_id} dla match_id={match_id}: {e}",
            file=sys.stderr,
        )
        return []


def extract_match_from_match_page(ng_state):
    """
    Parse ng-state from an individual match page (new gRPC format).
    Returns match dict in old format expected by betclic_tennis.tennis_match().

    New gRPC format:
      subCategories[].markets[].mainSelections     -- simple bets (win, sets count)
      subCategories[].markets[].selectionMatrix[]  -- over/under bets
      subCategories[].markets[].groupMarkets[].selectionMatrix[] / mainSelections
    """
    for key, val in ng_state.items():
        if not key.startswith('grpc:'):
            continue
        payload = val.get('response', val).get('payload', val.get('payload', {}))
        if not payload or 'match' not in payload:
            continue
        m = payload['match']

        if m.get('isLive') and not INCLUDE_LIVE:
            return None

        contestants = [
            {'name': c.get('name', ''), 'short_name': c.get('shortName', c.get('name', ''))}
            for c in m.get('contestants', [])
        ]
        if len(contestants) < 2:
            return None

        def _sels_from_row(row):
            """Extract selection list from a selectionMatrix row"""
            result = []
            for sw in row.get('selections', []):
                oneof = sw.get('selectionOneof', {})
                if oneof.get('oneofKind') == 'selection':
                    s = oneof['selection']
                    result.append({'name': s.get('name', ''), 'odds': s.get('odds', 0)})
            return result

        grouped_markets = []
        for sc in m.get('subCategories', []):
            for mkt in sc.get('markets', []):
                inner = []

                # Simple bets
                if mkt.get('mainSelections'):
                    inner.append({'selections': [mkt['mainSelections']]})

                # Over/under rows
                for row in mkt.get('selectionMatrix', []):
                    sels = _sels_from_row(row)
                    if sels:
                        inner.append({'selections': [sels]})

                if inner:
                    grouped_markets.append({'name': mkt.get('name', ''), 'markets': inner})

                # Group sub-markets (set winners etc.)
                for gm in mkt.get('groupMarkets', []):
                    gm_inner = []
                    if gm.get('mainSelections'):
                        gm_inner.append({'selections': [gm['mainSelections']]})
                    for row in gm.get('selectionMatrix', []):
                        sels = _sels_from_row(row)
                        if sels:
                            gm_inner.append({'selections': [sels]})

                    if gm_inner:
                        grouped_markets.append({'name': gm.get('name', mkt.get('name', '')), 'markets': gm_inner})

        # Match page payload is lazy-loaded per category in UI tabs.
        # Dociągamy kluczową kategorię Punkty & Serwisy, bo zawiera m.in. rynki Asów.
        category_ids = {c.get('id', '') for c in m.get('categories', []) if c.get('id')}
        if 'ca_ten_ptss' in category_ids:
            extra_grouped = fetch_additional_grouped_markets(m.get('matchId', ''), 'ca_ten_ptss')
            existing_keys = {
                (gm.get('name', ''), tuple(sel.get('name', '') for block in gm.get('markets', []) for row in block.get('selections', []) for sel in row))
                for gm in grouped_markets
            }
            for gm in extra_grouped:
                key = (
                    gm.get('name', ''),
                    tuple(sel.get('name', '') for block in gm.get('markets', []) for row in block.get('selections', []) for sel in row),
                )
                if key not in existing_keys:
                    grouped_markets.append(gm)
                    existing_keys.add(key)

        competition = m.get('competition', {})
        return {
            'id': m.get('matchId', ''),
            'name': m.get('name', ''),
            'is_live': False,
            'contestants': contestants,
            'competition': {'name': competition.get('name', '')},
            'date': normalize_date(m.get('matchDateUtc', '')),
            'grouped_markets': grouped_markets,
        }
    return None


# Main execution
all_odds = []
conn = connect_to_wp_db.connect_to_db()

out_file_name = 'data/odds/betclic_odds.csv'
with open(out_file_name, 'w') as outfile:
    print('tournament', 'player1', 'player2', 'name', 'cat1', 'cat2', 'value', 'odd', 'bukmacher', 'date',
          sep='\t', file=outfile)

    print("TIME1:", datetime.now().strftime("%H:%M:%S"))

    # Krok 1: Pobierz stronę z listą meczy
    html_content = fetch_page(TENNIS_URL, attempts=3, retry_statuses={403})
    if not html_content:
        print("Nie udało się pobrać strony", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Krok 2: Linki z pierwszego widoku
    match_urls = set(BASE_URL + link_path for link_path in re.findall(r'href="(/tenis-stennis/[^"]+m\d+)"', html_content))

    # Krok 3: Dociągnij turnieje tenisowe i ich strony (bez zależności od infinite scroll)
    root_ng = extract_ng_state(html_content)
    competitions = extract_tennis_competitions(root_ng)
    print(f"Pomijanie deblowych: {'TAK' if SKIP_DOUBLES else 'NIE'}", file=sys.stderr)
    print(f"Wybrane turnieje: {len(competitions)}", file=sys.stderr)
    competition_match_urls = collect_match_urls_from_competitions(competitions)
    match_urls.update(competition_match_urls)

    match_urls = sorted(match_urls)

    print(f"Znaleziono {len(match_urls)} linków do meczy", file=sys.stderr)

    # Krok 4: Dla każdego meczu pobierz stronę i parsuj kursy
    matches_processed = 0
    failed_match_urls = []
    for match_url in match_urls:
        match_html = fetch_page(match_url, attempts=4, retry_statuses={403})
        if not match_html:
            failed_match_urls.append(match_url)
            continue

        if '403 forbidden' in match_html.lower() or 'access denied' in match_html.lower():
            print(
                f"Wykryto blokadę dla {match_url}, przerwa {BLOCK_COOLDOWN_SECONDS}s i koniec bieżącego przebiegu",
                file=sys.stderr,
            )
            failed_match_urls.append(match_url)
            break

        match_ng = extract_ng_state(match_html)
        match_details = extract_match_from_match_page(match_ng)

        if not match_details:
            print(f"Pomijam (live lub brak danych): {match_url}", file=sys.stderr)
            continue

        match_id = match_details.get('id', '')
        player1 = ''
        player2 = ''
        print(match_id, file=sys.stderr)

        try:
            match_obj = betclic_tennis.tennis_match(match_details)
            player1 = match_obj.player1
            player2 = match_obj.player2

            for player in [player1, player2]:
                if player and player not in tennis_dictionary['players']:
                    print(f'"{player}": ["{player}"],', sep='', file=sys.stderr)

            all_odds.append(match_obj.odds)
            match_obj.print_odds_converted(outfile)
            matches_processed += 1

        except Exception as e:
            print(f"Błąd dla {player1}\t{player2}\t{match_id}", file=sys.stderr)
            print(f"{e}", file=sys.stderr)
            continue

        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"Przetworzono {matches_processed} meczy", file=sys.stderr)

    with open(FAILED_URLS_FILE, 'w', encoding='utf-8') as failed_file:
        for failed_url in failed_match_urls:
            failed_file.write(failed_url + '\n')
    print(f"Niedostępne URL-e: {len(failed_match_urls)} zapisane do {FAILED_URLS_FILE}", file=sys.stderr)

# Save odds to files
with open('data/raw/betclick_tennis.txt', 'w') as all_odds_file:
    print(all_odds, file=all_odds_file)

print("TIME2:", datetime.now().strftime("%H:%M:%S"))

with open('data/raw/betclick_tennis.json', 'w') as all_odds_json_file:
    json.dump(all_odds, all_odds_json_file)

print("TIME3:", datetime.now().strftime("%H:%M:%S"))

# Database cleanup and insert
players, dates = tennis_functions.read_players_and_dates(out_file_name)
print("TIME4:", datetime.now().strftime("%H:%M:%S"))

tennis_functions.delete_players_and_dates(conn, players, dates, 'betclic')
print("TIME5:", datetime.now().strftime("%H:%M:%S"))

tennis_functions.insert_to_db_from_file_new(conn, out_file_name)
print("TIME6:", datetime.now().strftime("%H:%M:%S"))

conn.close()

# Generuj HTML tabelkę do szybkiego przeglądania
try:
    import pandas as pd
    df = pd.read_csv(out_file_name, sep='\t')
    df = df.sort_values(['player1', 'player2', 'name', 'cat1', 'value'])

    html_rows = df.to_html(index=False, border=0, classes='t')
    html_out = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<title>Betclic Kursy — {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
<style>
body {{ font-family: monospace; font-size: 13px; padding: 12px; }}
h2 {{ color: #333; }}
table.t {{ border-collapse: collapse; width: 100%; }}
table.t th {{ background: #2c5282; color: white; padding: 6px 10px; text-align: left; position: sticky; top: 0; }}
table.t td {{ padding: 4px 10px; border-bottom: 1px solid #e2e8f0; }}
table.t tr:hover td {{ background: #ebf8ff; }}
table.t tr:nth-child(even) td {{ background: #f7fafc; }}
table.t tr:nth-child(even):hover td {{ background: #ebf8ff; }}
input {{ margin-bottom: 10px; padding: 6px; width: 300px; font-size: 13px; }}
</style>
</head>
<body>
<h2>Betclic Kursy — {datetime.now().strftime('%Y-%m-%d %H:%M')}</h2>
<input type="text" id="filter" placeholder="Filtruj (gracz, turniej, typ zakładu...)" oninput="filterTable()">
{html_rows}
<script>
function filterTable() {{
  const q = document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('table.t tbody tr').forEach(r => {{
    r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body></html>"""

    html_file = 'data/reports/betclic_odds.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_out)
    print(f"✓ HTML tabelka: {html_file} ({len(df)} wierszy)")
except Exception as e:
    print(f"Nie udało się wygenerować HTML: {e}", file=sys.stderr)

exit()

