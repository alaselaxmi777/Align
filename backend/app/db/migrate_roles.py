from app.db.session import engine
from sqlalchemy import create_engine, text

def run_migration():
    targets = [
        (engine, "primary database"),
        (create_engine("postgresql+psycopg://align_user:align_dev_password@db:5432/align_test_db"), "test database"),
    ]
    for eng, desc in targets:
        try:
            with eng.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';"))
                conn.execute(text("UPDATE users SET role = 'admin' WHERE is_admin = true;"))
            print(f"Migration completed on {desc}.")
        except Exception as e:
            print(f"Migration note for {desc}: {e}")

if __name__ == "__main__":
    run_migration()
