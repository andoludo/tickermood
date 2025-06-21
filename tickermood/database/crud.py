from functools import cached_property
from pathlib import Path
from typing import Any, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, create_engine, insert
from sqlmodel import Session, select


from tickermood.database.scripts.upgrade import upgrade

if TYPE_CHECKING:
    from tickermood.subject import Subject


class TickerMoodDb(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    database_path: Path
    no_migration: bool = False

    @cached_property
    def _engine(self) -> Engine:
        database_url = f"sqlite:///{Path(self.database_path)}"
        upgrade(database_url, no_migration=self.no_migration)
        engine = create_engine(database_url)
        return engine

    def model_post_init(self, __context: Any) -> None:
        self._engine  # noqa: B018

    def write(self, subject: "Subject") -> None:
        from tickermood.database.schemas import SubjectORM

        with Session(self._engine) as session:
            stmt = (
                insert(SubjectORM)
                .prefix_with("OR REPLACE")
                .values([subject.model_dump()])
            )
            session.exec(stmt)  # type: ignore
            session.commit()

    def load(self, subject: "Subject") -> "Subject":
        from tickermood.database.schemas import SubjectORM
        from tickermood.subject import Subject

        with Session(self._engine) as session:
            stmt = (
                select(SubjectORM)
                .where(SubjectORM.symbol == subject.symbol)
                .order_by(SubjectORM.date.desc())  # type: ignore
                .limit(1)
            )
            result = session.exec(stmt).first()
            if result is None:
                raise ValueError(f"No data found for symbol: {subject.symbol}")
            return Subject.model_validate(result.model_dump())
