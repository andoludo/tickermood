from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "tickermood.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
