"""Run Camber in dev mode (API only, no Qt)."""
from camber.storage.db import init_db
from camber.extension_api.api import serve

if __name__ == "__main__":
    engine = init_db("camber.db")
    print("Local API on http://127.0.0.1:8765")
    serve(engine)
