import psycopg2
from psycopg2.extras import DictCursor, execute_values
import paramiko
from sshtunnel import SSHTunnelForwarder
import os
import sys

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def _load_env_file():
    """Load local .env once so scripts work without manual export."""
    if load_dotenv is None:
        return
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)


_load_env_file()

def _env_required(name):
    """Get required environment variable"""
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f'Missing required environment variable: {name}')


def _env_int(name, default):
    """Get integer environment variable with default"""
    raw = os.getenv(name)
    if raw is None or raw == '':
        return default
    return int(raw)


def connect_to_postgres_local():
    """Połączenie do lokalnego PostgreSQL (bez tunelu SSH)"""
    db_host = os.getenv('ODDS_DB_HOST', 'localhost')
    db_user = os.getenv('ODDS_DB_USER', 'postgres')
    db_pass = os.getenv('ODDS_DB_PASSWORD', 'password')
    db_name = os.getenv('ODDS_DB_NAME', 'odds_db')
    db_port = _env_int('ODDS_DB_PORT', 5432)

    try:
        conn = psycopg2.connect(
            host=db_host,
            user=db_user,
            password=db_pass,
            database=db_name,
            port=db_port,
            connect_timeout=10
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"Błąd połączenia z PostgreSQL: {e}", file=sys.stderr)
        raise


def connect_to_postgres_ssh():
    """Połączenie do PostgreSQL przez tunel SSH"""
    # SSH config
    ssh_host = _env_required('ODDS_SSH_HOST')
    ssh_user = _env_required('ODDS_SSH_USER')
    ssh_port = _env_int('ODDS_SSH_PORT', 22)
    ssh_key_path = os.getenv('ODDS_SSH_KEY_PATH', os.path.expanduser('~/.ssh/id_rsa'))

    # Database config
    db_host = os.getenv('ODDS_DB_HOST', 'localhost')
    db_user = os.getenv('ODDS_DB_USER', 'postgres')
    db_pass = os.getenv('ODDS_DB_PASSWORD', 'password')
    db_name = os.getenv('ODDS_DB_NAME', 'odds_db')
    db_port = _env_int('ODDS_DB_PORT', 5432)

    try:
        mypkey = paramiko.RSAKey.from_private_key_file(ssh_key_path)
        tunnel = SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username=ssh_user,
            ssh_pkey=mypkey,
            remote_bind_address=(db_host, db_port),
            local_bind_address=('127.0.0.1', 0)
        )
        tunnel.start()
        
        conn = psycopg2.connect(
            host='127.0.0.1',
            user=db_user,
            password=db_pass,
            database=db_name,
            port=tunnel.local_bind_port,
            connect_timeout=10
        )
        return conn, tunnel
    except Exception as e:
        print(f"Błąd SSH tunelu: {e}", file=sys.stderr)
        raise


def connect_to_db():
    """
    Główna funkcja do połączenia.
    Jeśli ODDS_SSH_HOST jest ustawiony, używa tunelu SSH,
    w przeciwnym razie połączenie bezpośrednie.
    """
    use_ssh = os.getenv('ODDS_SSH_HOST')
    
    if use_ssh:
        return connect_to_postgres_ssh()
    else:
        return connect_to_postgres_local()


def create_tables():
    """Tworzy schema bazy danych"""
    conn = connect_to_db()
    cur = conn.cursor()
    
    sql_file = os.path.join(os.path.dirname(__file__), 'db_schema.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("✓ Tabele bazy danych utworzone")


def insert_bookmaker(name, slug):
    """Wstawia bukmachera (jeśli nie istnieje)"""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute("""
        INSERT INTO bookmakers (name, slug) 
        VALUES (%s, %s)
        ON CONFLICT (slug) DO NOTHING
        RETURNING id
    """, (name, slug))
    
    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return result['id'] if result else get_bookmaker_id(slug)


def get_bookmaker_id(slug):
    """Pobiera ID bukmachera"""
    conn = connect_to_db()
    cur = conn.cursor(cursor_factory=DictCursor)
    
    cur.execute("SELECT id FROM bookmakers WHERE slug = %s", (slug,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return result['id'] if result else None


def insert_odds_batch(odds_list):
    """
    Wstawia wiele wierszy kursów na raz.
    odds_list = list of dicts: {match_id, bookmaker_id, bet_type_id, value, odd}
    """
    conn = connect_to_db()
    cur = conn.cursor()
    
    sql = """
        INSERT INTO odds (match_id, bookmaker_id, bet_type_id, value, odd)
        VALUES %s
        ON CONFLICT (match_id, bookmaker_id, bet_type_id, value) 
        DO UPDATE SET odd = EXCLUDED.odd, scraped_at = CURRENT_TIMESTAMP
    """
    
    values = [
        (o['match_id'], o['bookmaker_id'], o['bet_type_id'], o.get('value'), o['odd'])
        for o in odds_list
    ]
    
    execute_values(cur, sql, values)
    conn.commit()
    cur.close()
    conn.close()


def test_connection():
    """Test czy połączenie działa"""
    try:
        conn = connect_to_postgres_local()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"✓ PostgreSQL connected: {version[0]}")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}", file=sys.stderr)
        return False


def connect_to_db():
    """Drop-in replacement dla connect_to_wp_db.connect_to_db() — używa lokalnego PostgreSQL."""
    return connect_to_postgres_local()


def create_tables():
    """Tworzy schemat bazy danych z db_schema.sql"""
    conn = connect_to_postgres_local()
    cur = conn.cursor()

    sql_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'db_schema.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("✓ Tabele bazy danych utworzone")


if __name__ == '__main__':
    if test_connection():
        print("✓ Wszystko OK! Możesz teraz uruchamiać skrypty.")
    else:
        print("✗ Problem z bazą danych", file=sys.stderr)
        sys.exit(1)
