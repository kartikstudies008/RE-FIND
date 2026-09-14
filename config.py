import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


def get_database_uri():
    """
    Determine the database URI.
    Checks if a custom DATABASE_URL is provided, or constructs MySQL URI.
    If MySQL is configured but unreachable, gracefully falls back to SQLite
    to ensure seamless local testing and college demo capability.
    """
    custom_url = os.environ.get('DATABASE_URL')
    if custom_url and not custom_url.startswith('mysql'):
        return custom_url

    # Check MySQL settings
    mysql_user = os.environ.get('MYSQL_USER', 'root')
    mysql_pwd = os.environ.get('MYSQL_PASSWORD', '')
    mysql_host = os.environ.get('MYSQL_HOST', 'localhost')
    mysql_port = os.environ.get('MYSQL_PORT', '3306')
    mysql_db = os.environ.get('MYSQL_DATABASE', 'refind_db')

    mysql_uri = custom_url or f"mysql+pymysql://{mysql_user}:{mysql_pwd}@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"

    # Test if MySQL connection works, else fall back to SQLite
    try:
        import pymysql
        conn = pymysql.connect(
            host=mysql_host,
            user=mysql_user,
            password=mysql_pwd,
            port=int(mysql_port),
            connect_timeout=2
        )
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{mysql_db}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
        print(f"[ReFind AI] Successfully connected to MySQL at {mysql_host}:{mysql_port}/{mysql_db}")
        return mysql_uri
    except Exception as e:
        sqlite_fallback = f"sqlite:///{os.path.join(basedir, 'refind.db')}"
        print(f"[ReFind AI Note] MySQL connection not active ({e}). Falling back to local SQLite at {sqlite_fallback}")
        return sqlite_fallback


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'refind-ai-default-dev-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads configuration
    UPLOAD_FOLDER = os.path.join(basedir, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max file upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    # Matching Engine settings
    MATCH_THRESHOLD = float(os.environ.get('MATCH_THRESHOLD', 60.0))

    # Supported Item Categories
    CATEGORIES = [
        'Electronics',
        'Documents',
        'Wallet',
        'Mobile Phone',
        'Laptop',
        'Keys',
        'Bags',
        'Clothing',
        'Accessories',
        'Books',
        'Other'
    ]
