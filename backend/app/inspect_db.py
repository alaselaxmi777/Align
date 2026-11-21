"""Database inspection utility for ALIGN."""
import argparse
import sys
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

def inspect_database(target_table: str | None = None, limit: int = 10):
    db_url = settings.database_url
    print(f"\n Connecting to database at: {db_url}")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if not tables:
                print("Connected successfully, but no tables were found. Have migrations been applied?")
                return
            
            print(f" Successfully connected! Found {len(tables)} table(s):\n")
            
            table_counts = {}
            for table in sorted(tables):
                count_res = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
                table_counts[table] = count_res
                print(f"  - {table:<25} : {count_res} row(s)")
            
            if target_table:
                tables_to_show = [t for t in tables if t.lower() == target_table.lower()]
                if not tables_to_show:
                    print(f"\nTable '{target_table}' not found.")
                    return
            else:
                tables_to_show = [t for t in ["users", "communities", "events", "places", "profiles"] if t in tables]
            
            for table in tables_to_show:
                print(f"\n{'='*60}")
                print(f" Table: {table} (showing up to {limit} rows)")
                print(f"{'='*60}")
                
                columns = [c["name"] for c in inspector.get_columns(table)]
                # Filter out heavy vector embedding columns for concise display
                display_cols = [c for c in columns if c != "embedding"]
                
                rows = conn.execute(
                    text(f'SELECT {", ".join([f"{c}" for c in display_cols])} FROM "{table}" LIMIT {limit}')
                ).mappings().all()
                
                if not rows:
                    print("  (Empty table)")
                    continue
                
                for idx, row in enumerate(rows, start=1):
                    print(f"\n  [Row {idx}]")
                    for col in display_cols:
                        val = row[col]
                        print(f"    {col:<22}: {val}")
                        
    except Exception as e:
        print(f"\n Error connecting to the database: {e}")
        print("\nTroubleshooting tips:")
        print("  1. Ensure Docker Desktop is running.")
        print("  2. Ensure the PostgreSQL container is started: docker compose up -d db")
        print("  3. Check that port 5433 is open and not blocked.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect ALIGN Database Data")
    parser.add_argument("--table", type=str, default=None, help="Specific table to display")
    parser.add_argument("--limit", type=int, default=10, help="Maximum number of rows to show")
    args = parser.parse_args()
    
    inspect_database(target_table=args.table, limit=args.limit)
