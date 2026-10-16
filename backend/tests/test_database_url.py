from app.core.database import normalize_database_url as n


def test_neon_url_is_made_asyncpg_ready():
    url = "postgresql://u:p@ep-x-pooler.eu-west-2.aws.neon.tech/db?sslmode=require&channel_binding=require"
    assert n(url) == "postgresql+asyncpg://u:p@ep-x-pooler.eu-west-2.aws.neon.tech/db?ssl=require"


def test_postgres_scheme_alias():
    assert n("postgres://u:p@h/db") == "postgresql+asyncpg://u:p@h/db"


def test_sqlite_and_asyncpg_urls_untouched():
    assert n("sqlite+aiosqlite:///./x.db") == "sqlite+aiosqlite:///./x.db"
    assert n("postgresql+asyncpg://u:p@h/db?ssl=require") == "postgresql+asyncpg://u:p@h/db?ssl=require"
