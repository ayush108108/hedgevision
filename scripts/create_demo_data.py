#!/usr/bin/env python3
"""
Quick demo data populator for HedgeVision.
Inserts minimal correlations for UI testing when no real data is available.
"""

import sqlite3
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "api"))
from utils.config import config

def create_demo_correlations():
    """Insert demo correlation pairs for UI testing."""
    db_path = config.get("DB_PATH", "backend/prices.db")
    
    print(f"📊 Creating demo correlation data in {db_path}")
    
    conn = sqlite3.connect(db_path, timeout=10.0)
    cursor = conn.cursor()
    
    # Check if we have assets
    cursor.execute("SELECT COUNT(*) FROM assets")
    count = cursor.fetchone()[0]
    
    if count < 2:
        print("❌ Need at least 2 assets in database. Run data sync first.")
        conn.close()
        return
    
    print(f"✓ Found {count} assets")
    
    # Get some asset pairs
    cursor.execute("""
        SELECT id, symbol FROM assets 
        WHERE symbol IN ('BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'SOL-USD',
                          'MATIC-USD', 'DOT-USD', 'AVAX-USD')
        LIMIT 8
    """)
    assets = cursor.fetchall()
    
    if len(assets) < 2:
        # Fallback: get any 8 assets
        cursor.execute("SELECT id, symbol FROM assets LIMIT 8")
        assets = cursor.fetchall()
    
    print(f"✓ Using {len(assets)} assets for demo pairs")
    
    # Create correlation_screener table if it doesn't exist (for demo)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS correlation_screener (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset1_id INTEGER NOT NULL,
            asset2_id INTEGER NOT NULL,
            correlation REAL NOT NULL,
            p_value REAL,
            method TEXT NOT NULL DEFAULT 'spearman',
            granularity TEXT NOT NULL DEFAULT 'daily',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(asset1_id, asset2_id, method, granularity)
        )
    """)
    
    # Insert some demo pairs with realistic correlations
    demo_pairs = [
        (assets[0][0], assets[1][0], 0.88),  # BTC vs ETH
        (assets[0][0], assets[2][0], 0.75) if len(assets) > 2 else None,
        (assets[1][0], assets[2][0], 0.82) if len(assets) > 2 else None,
        (assets[0][0], assets[3][0], 0.72) if len(assets) > 3 else None,
        (assets[1][0], assets[3][0], 0.79) if len(assets) > 3 else None,
        (assets[2][0], assets[4][0], 0.68) if len(assets) > 4 else None,
        (assets[3][0], assets[4][0], 0.75) if len(assets) > 4 else None,
        (assets[4][0], assets[5][0], 0.71) if len(assets) > 5 else None,
    ]
    
    inserted = 0
    for pair in demo_pairs:
        if pair is None:
            continue
            
        asset1_id, asset2_id, corr = pair
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO correlation_screener
                (asset1_id, asset2_id, correlation, method, granularity)
                VALUES (?, ?, ?, 'spearman', 'daily')
            """, (asset1_id, asset2_id, corr))
            inserted += 1
        except Exception as e:
            print(f"  ⚠️  Error inserting pair: {e}")
    
    conn.commit()
    print(f"✅ Inserted {inserted} demo correlation pairs")
    
    # Show summary
    cursor.execute("""
        SELECT 
            a1.symbol, a2.symbol, cs.correlation
        FROM correlation_screener cs
        JOIN assets a1 ON cs.asset1_id = a1.id
        JOIN assets a2 ON cs.asset2_id = a2.id
        ORDER BY cs.correlation DESC
        LIMIT 5
    """)
    
    print("\n📈 Top Demo Pairs:")
    for row in cursor.fetchall():
        print(f"   {row[0]} ↔ {row[1]}: {row[2]:.3f}")
    
    conn.close()
    print("\n✅ Demo data ready! Refresh the UI.\n")


if __name__ == "__main__":
    create_demo_correlations()
