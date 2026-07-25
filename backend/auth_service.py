import hashlib
import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.environ.get('APP_DB_PATH', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'app.db'))
DEFAULT_DEMO_EMAIL = 'demo@aegis.local'
DEFAULT_DEMO_PASSWORD = 'Demo123!'
DEFAULT_CARETAKER_EMAIL = 'caretaker@aegis.local'
DEFAULT_CARETAKER_PASSWORD = 'Caretaker123!'
VALID_ROLES = {'hero', 'caretaker'}


def _get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _close_connection(connection):
    if connection is not None:
        connection.close()


def init_db():
    connection = _get_connection()
    try:
        connection.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                password_hash TEXT,
                username TEXT NOT NULL,
                role TEXT NOT NULL,
                provider TEXT NOT NULL,
                is_anonymous INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        connection.commit()
    finally:
        _close_connection(connection)

    seed_demo_user()
    seed_caretaker_user()


def seed_demo_user():
    with _get_connection() as connection:
        existing = connection.execute('SELECT id FROM users WHERE email = ?', (DEFAULT_DEMO_EMAIL.lower(),)).fetchone()
        if existing:
            return

        connection.execute(
            '''
            INSERT INTO users (id, email, password_hash, username, role, provider, is_anonymous, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'demo-user',
                DEFAULT_DEMO_EMAIL.lower(),
                _hash_password(DEFAULT_DEMO_PASSWORD),
                'Demo User',
                'hero',
                'email',
                0,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()


def seed_caretaker_user():
    with _get_connection() as connection:
        existing = connection.execute('SELECT id FROM users WHERE email = ?', (DEFAULT_CARETAKER_EMAIL.lower(),)).fetchone()
        if existing:
            return

        connection.execute(
            '''
            INSERT INTO users (id, email, password_hash, username, role, provider, is_anonymous, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                'caretaker-user',
                DEFAULT_CARETAKER_EMAIL.lower(),
                _hash_password(DEFAULT_CARETAKER_PASSWORD),
                'Care Buddy',
                'caretaker',
                'email',
                0,
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def create_user(email: str, password: str, username: str, role: str = 'hero') -> dict:
    if not email or not password or not username:
        raise ValueError('Email, password, and username are required.')

    normalized_role = (role or 'hero').strip().lower()
    if normalized_role not in VALID_ROLES:
        raise ValueError('Invalid role selected.')

    init_db()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with _get_connection() as connection:
        try:
            connection.execute(
                '''
                INSERT INTO users (id, email, password_hash, username, role, provider, is_anonymous, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (user_id, email.lower(), _hash_password(password), username.strip(), normalized_role, 'email', 0, now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError('Email already registered.') from exc

    return {
        'id': user_id,
        'email': email.lower(),
        'username': username.strip(),
        'role': role.lower(),
        'provider': 'email',
        'is_anonymous': False,
    }


def create_anonymous_user(username: str = 'Guest User', role: str = 'hero') -> dict:
    init_db()
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    normalized_role = (role or 'hero').strip().lower()
    if normalized_role not in VALID_ROLES:
        normalized_role = 'hero'

    with _get_connection() as connection:
        connection.execute(
            '''
            INSERT INTO users (id, email, password_hash, username, role, provider, is_anonymous, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (user_id, None, None, username.strip(), normalized_role, 'anonymous', 1, now, now),
        )

    return {
        'id': user_id,
        'email': None,
        'username': username.strip(),
        'role': normalized_role,
        'provider': 'anonymous',
        'is_anonymous': True,
    }


def authenticate_user(email: str, password: str) -> dict | None:
    if not email or not password:
        return None

    init_db()
    with _get_connection() as connection:
        row = connection.execute(
            'SELECT * FROM users WHERE email = ? AND password_hash IS NOT NULL',
            (email.lower(),),
        ).fetchone()

    if not row:
        return None

    if row['password_hash'] != _hash_password(password):
        return None

    return {
        'id': row['id'],
        'email': row['email'],
        'username': row['username'],
        'role': row['role'],
        'provider': row['provider'],
        'is_anonymous': bool(row['is_anonymous']),
    }


def upgrade_anonymous_user(user_id: str, email: str, password: str, username: str, role: str = 'hero') -> dict:
    if not user_id or not email or not password or not username:
        raise ValueError('User ID, email, password, and username are required.')

    init_db()
    now = datetime.now(timezone.utc).isoformat()

    with _get_connection() as connection:
        existing = connection.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
        if not existing:
            raise ValueError('Anonymous user not found.')

        try:
            connection.execute(
                '''
                UPDATE users
                SET email = ?, password_hash = ?, username = ?, role = ?, provider = ?, is_anonymous = 0, updated_at = ?
                WHERE id = ?
                ''',
                (email.lower(), _hash_password(password), username.strip(), role.lower(), 'email', now, user_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError('Email already registered.') from exc

    return {
        'id': user_id,
        'email': email.lower(),
        'username': username.strip(),
        'role': role.lower(),
        'provider': 'email',
        'is_anonymous': False,
    }


def get_user_by_id(user_id: str) -> dict | None:
    init_db()
    with _get_connection() as connection:
        row = connection.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if not row:
        return None

    return {
        'id': row['id'],
        'email': row['email'],
        'username': row['username'],
        'role': row['role'],
        'provider': row['provider'],
        'is_anonymous': bool(row['is_anonymous']),
    }
