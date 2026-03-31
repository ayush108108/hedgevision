"""
Apply the fresh-start TimescaleDB schema to Heroku database.
"""
import psycopg2
from psycopg2.extras import RealDictCursor

# Heroku Stackhero PostgreSQL connection string
DATABASE_URL = "postgresql://admin:Qo2s88aewnH0dVk2Vy5dKaOnt6mw4Tvh@sb6t1t.stackhero-network.com:6391/admin?sslmode=require"

def apply_schema():
    """Apply the schema from schema_fresh_start.sql"""
    try:
        # Read the schema file
        with open('schema_fresh_start.sql', 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Connect to database
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Connected to Heroku TimescaleDB")

        # Execute the entire schema as one statement
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            conn.commit()
            print("✅ Schema applied successfully!")

        # Verify key tables exist
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            tables = cur.fetchall()
            print(f"\n📊 Created tables ({len(tables)}):")
            for table in tables:
                print(f"   - {table['tablename']}")

            # Check hypertables
            cur.execute("""
                SELECT hypertable_name
                FROM timescaledb_information.hypertables
                ORDER BY hypertable_name;
            """)
            hypertables = cur.fetchall()
            print(f"\n🕐 Hypertables ({len(hypertables)}):")
            for ht in hypertables:
                print(f"   - {ht['hypertable_name']}")

        conn.close()
        print("\n🎉 Schema successfully applied to Heroku TimescaleDB!")

    except Exception as e:
        print(f"❌ Schema application failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    apply_schema()
