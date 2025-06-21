import os
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine


from tickermood.database.settings import DATABASE_URL


def upgrade(database_url: str, no_migration: Optional[bool] = False) -> None:
    root_folder = Path(__file__).parents[1]
    os.environ.update({"DATABASE_URL": database_url})
    alembic_cfg = Config(root_folder / "alembic" / "alembic.ini")
    alembic_cfg.set_main_option("script_location", str(root_folder / "alembic"))
    if no_migration:
        from tickermood.database.schemas import SubjectORM

        engine = create_engine(database_url, echo=True)
        SubjectORM.__table__.create(engine, checkfirst=True)  # type: ignore
    else:
        command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    upgrade(DATABASE_URL)
