import os

# Force an in-memory SQLite database for the test run before `main` (and the
# `database` module it imports) build their engine. `database.py` reads
# DATABASE_URL via load_dotenv(override=False), so setting it here takes
# precedence over any value in a local .env and keeps the suite independent of
# the developer's real database (e.g. Postgres, which would require psycopg2).
os.environ["DATABASE_URL"] = "sqlite://"
