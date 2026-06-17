try:
    from supabase import create_client, Client
except ModuleNotFoundError:
    # Minimal stub to avoid import error during development.
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        def from_(self, table_name):
            return self
        def table(self, table_name):
            return self
        def select(self, *args, **kwargs):
            return self
        def eq(self, *args, **kwargs):
            return self
        def insert(self, *args, **kwargs):
            return self
        def update(self, *args, **kwargs):
            return self
        def delete(self, *args, **kwargs):
            return self
        def single(self):
            return self
        def execute(self):
            # Return empty data structures compatible with existing code.
            class Result:
                def __init__(self):
                    self.data = []
                def count(self):
                    return 0
            return Result()

    # Fallback create_client when supabase package is unavailable.
    def create_client(url: str, key: str) -> Client:
        """Return a stub Client instance; ignores URL/key.
        This enables the app to run without the real supabase library.
        """
        return Client()
import os
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        """Fallback no-op if python-dotenv not installed."""
        pass

load_dotenv()
import logging
logging.basicConfig(level=logging.INFO)
logging.info(f"Supabase URL loaded: {os.getenv('SUPABASE_URL')}")
logging.info(f"Supabase Service Key loaded: {os.getenv('SUPABASE_SERVICE_KEY')[:5] if os.getenv('SUPABASE_SERVICE_KEY') else None}")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Supabase credentials not set in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def select(table: str, **kwargs):
    """Convenient wrapper for supabase.select with optional filters.
    kwargs are column=value pairs that will be added via .eq()."""
    query = supabase.table(table).select("*")
    for col, val in kwargs.items():
        query = query.eq(col, val)
    return query.execute()

def insert(table: str, data: dict):
    return supabase.table(table).insert(data).execute()

def update(table: str, data: dict, **kwargs):
    query = supabase.table(table).update(data)
    for col, val in kwargs.items():
        query = query.eq(col, val)
    return query.execute()

def delete(table: str, **kwargs):
    query = supabase.table(table).delete()
    for col, val in kwargs.items():
        query = query.eq(col, val)
    return query.execute()
