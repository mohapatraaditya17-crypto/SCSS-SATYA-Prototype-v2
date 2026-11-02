from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def run_migrations():
    """
    Auto-migrates SQLite database schema non-destructively to add any missing SATYA v2 columns
    without altering or destroying historical examination records.
    """
    try:
        with engine.connect() as conn:
            # Check existing columns in examinations table
            result = conn.execute(text("PRAGMA table_info(examinations)"))
            existing_cols = {row[1] for row in result.fetchall()}
            if not existing_cols:
                return

            new_columns = [
                ("decision_assessment", "VARCHAR(64) DEFAULT 'INCONCLUSIVE'"),
                ("evidence_strength", "VARCHAR(32) DEFAULT 'NONE'"),
                ("decision_confidence", "INTEGER DEFAULT NULL"),
                ("decision_data", "JSON DEFAULT '{}'"),
                ("detector_results", "JSON DEFAULT '[]'"),
                ("image_characterization", "JSON DEFAULT '{}'"),
                ("model_versions", "JSON DEFAULT '{}'"),
                ("detector_versions", "JSON DEFAULT '{}'"),
            ]

            # Legacy release wrote a synthetic default of 50 despite having no
            # empirical calibrator. Clear only these default values when no
            # decision payload exists; preserve all other recorded values.
            if "decision_confidence" in existing_cols:
                conn.execute(text(
                    "UPDATE examinations SET decision_confidence = NULL "
                    "WHERE decision_confidence = 50 AND "
                    "(decision_data IS NULL OR decision_data = '{}' OR decision_data = 'null')"
                ))
                conn.commit()
            for col_name, col_def in new_columns:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE examinations ADD COLUMN {col_name} {col_def}"))
                    conn.commit()
    except Exception:
        pass


def get_db():
    """FastAPI database dependency yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
