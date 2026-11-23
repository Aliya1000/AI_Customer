
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = f"sqlite:///{(Path(__file__).resolve().parent.parent / 'sessions.db').as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database():
    Base.metadata.create_all(bind=engine)

    # Add new columns to an existing database without deleting old data.
    inspector = inspect(engine)

    if "sessions" in inspector.get_table_names():
        existing_columns = {
            column["name"]
            for column in inspector.get_columns("sessions")
        }

        migrations = {
            "emotional_progression": "JSON",
            "replay_transcript": "JSON",
            "updated_at": "DATETIME"
        }

        with engine.begin() as connection:
            for column_name, column_type in migrations.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE sessions ADD COLUMN "
                            f"{column_name} {column_type}"
                        )
                    )
