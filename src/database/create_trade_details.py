#!/usr/bin/env python3
"""
Create trade_details table and insert sample data with anomalies
"""

from connection import DatabaseConnection
from datetime import datetime, timedelta


def create_trade_details_table() -> None:
    """Create trade table"""
    db = DatabaseConnection(database="EM")

    create_table_script = """
    IF OBJECT_ID('dbo.trade', 'U') IS NOT NULL
        DROP TABLE dbo.trade;
    GO

    CREATE TABLE dbo.trade (
        generation_id INT NOT NULL,
        arrangement_id INT NOT NULL,
        feed_id INT,
        src_trade_ref VARCHAR(50),
        book_code VARCHAR(50),
        buy_sell VARCHAR(10),
        component_use_pv DECIMAL(18, 2),
        component_used_pv_last_updated DATETIME,
        counterparty_id INT,
        currency_1 VARCHAR(10),
        currency_2 VARCHAR(10),
        date_created DATETIME,
        effective_date DATETIME,
        end_date DATETIME,
        exposure DECIMAL(18, 2),
        exposure_in_usd DECIMAL(18, 2),
        fed_pv DECIMAL(18, 2),
        fed_pv_currency VARCHAR(10),
        fed_pv_last_updated DATETIME,
        maturity_date DATETIME,
        notional_1 DECIMAL(18, 2),
        notional_2 DECIMAL(18, 2),
        prev_used_pv DECIMAL(18, 2),
        principal_id INT,
        rule_group_id INT,
        status INT,
        status_last_updated DATETIME,
        strike_effective_date DATETIME,
        trade_date DATETIME,
        trade_type_id INT,
        trade_subtype_id INT,
        used_asset_desc VARCHAR(255),
        used_pv DECIMAL(18, 2),
        used_pv_in_usd DECIMAL(18, 2),
        valuation_date DATETIME,

        INDEX idx_generation_arrangement (generation_id, arrangement_id),
        INDEX idx_src_trade_ref (src_trade_ref),
        INDEX idx_trade_date (trade_date),
        INDEX idx_counterparty (counterparty_id),
        INDEX idx_status (status)
    );
    GO
    """

    print("Creating trade table...")
    db.execute_script(create_table_script)
    print("✓ trade table created successfully")


def insert_sample_data() -> None:
    """Insert sample data with various anomalies"""
    db = DatabaseConnection(database="EM")

    # Base date for sample data
    base_date = datetime(2026, 2, 1)

    # Sample data with anomalies:
    # 1. Duplicate trades (same src_trade_ref, different arrangement_id)
    # 2. Exposure mismatches (exposure != notional * some factor)
    # 3. Date anomalies (effective_date > maturity_date)
    # 4. Currency mismatches (notional currencies don't match fed_pv_currency)
    # 5. Status inconsistencies (active trades with past maturity dates)
    # 6. Large PV discrepancies (component_use_pv != used_pv)

    sample_records = [
        # Normal trade
        (148393, 439393, 1001, 'TRADE-2026-001', 'BOOK-A', 'BUY', 1000000.00, base_date, 5001,
         'USD', 'EUR', base_date, base_date, base_date + timedelta(days=365), 1000000.00, 1000000.00,
         950000.00, 'USD', base_date, base_date + timedelta(days=365), 1000000.00, 850000.00,
         0.00, 101, 201, 1, base_date, base_date, base_date, 10, 100, 'EUR/USD Swap', 1000000.00,
         1000000.00, base_date),

        # ANOMALY 1: Duplicate trade reference with different arrangement_id
        (148393, 439394, 1001, 'TRADE-2026-001', 'BOOK-A', 'BUY', 1000000.00, base_date, 5001,
         'USD', 'EUR', base_date, base_date, base_date + timedelta(days=365), 1000000.00, 1000000.00,
         950000.00, 'USD', base_date, base_date + timedelta(days=365), 1000000.00, 850000.00,
         0.00, 101, 201, 1, base_date, base_date, base_date, 10, 100, 'EUR/USD Swap', 1000000.00,
         1000000.00, base_date),

        # ANOMALY 2: Exposure mismatch (exposure >> notional)
        (148394, 550121, 1002, 'TRADE-2026-002', 'BOOK-B', 'SELL', 500000.00, base_date + timedelta(days=1),
         5002, 'GBP', 'USD', base_date + timedelta(days=1), base_date + timedelta(days=1),
         base_date + timedelta(days=180), 5000000.00, 6250000.00, 480000.00, 'GBP',
         base_date + timedelta(days=1), base_date + timedelta(days=180), 500000.00, 625000.00,
         0.00, 102, 202, 1, base_date + timedelta(days=1), base_date + timedelta(days=1),
         base_date + timedelta(days=1), 11, 101, 'GBP/USD Forward', 500000.00, 625000.00,
         base_date + timedelta(days=1)),

        # ANOMALY 3: Date anomaly (effective_date > maturity_date)
        (148395, 661234, 1003, 'TRADE-2026-003', 'BOOK-C', 'BUY', 2000000.00, base_date + timedelta(days=2),
         5003, 'JPY', 'USD', base_date + timedelta(days=2), base_date + timedelta(days=100),
         base_date + timedelta(days=90), 2000000.00, 13333.33, 1950000.00, 'JPY',
         base_date + timedelta(days=2), base_date + timedelta(days=50), 2000000.00, 13333.33,
         0.00, 103, 203, 1, base_date + timedelta(days=2), base_date + timedelta(days=100),
         base_date + timedelta(days=2), 12, 102, 'JPY/USD Option', 2000000.00, 13333.33,
         base_date + timedelta(days=2)),

        # ANOMALY 4: Currency mismatch (fed_pv_currency != currency_1 or currency_2)
        (148396, 771001, 1004, 'TRADE-2026-004', 'BOOK-D', 'SELL', 750000.00, base_date + timedelta(days=3),
         5004, 'EUR', 'GBP', base_date + timedelta(days=3), base_date + timedelta(days=3),
         base_date + timedelta(days=270), 750000.00, 900000.00, 720000.00, 'CHF',
         base_date + timedelta(days=3), base_date + timedelta(days=270), 750000.00, 640000.00,
         0.00, 104, 204, 1, base_date + timedelta(days=3), base_date + timedelta(days=3),
         base_date + timedelta(days=3), 13, 103, 'EUR/GBP Cross', 750000.00, 900000.00,
         base_date + timedelta(days=3)),

        # ANOMALY 5: Active trade with past maturity date
        (148397, 881002, 1005, 'TRADE-2025-005', 'BOOK-E', 'BUY', 1500000.00, base_date - timedelta(days=400),
         5005, 'USD', 'CAD', base_date - timedelta(days=400), base_date - timedelta(days=400),
         base_date - timedelta(days=35), 1500000.00, 1500000.00, 1450000.00, 'USD',
         base_date - timedelta(days=400), base_date - timedelta(days=35), 1500000.00, 2000000.00,
         0.00, 105, 205, 1, base_date - timedelta(days=400), base_date - timedelta(days=400),
         base_date - timedelta(days=400), 14, 104, 'USD/CAD Swap', 1500000.00, 1500000.00,
         base_date),

        # ANOMALY 6: Large PV discrepancy (component_use_pv != used_pv)
        (148398, 991003, 1006, 'TRADE-2026-006', 'BOOK-F', 'SELL', 3000000.00, base_date + timedelta(days=5),
         5006, 'AUD', 'USD', base_date + timedelta(days=5), base_date + timedelta(days=5),
         base_date + timedelta(days=365), 800000.00, 533333.33, 750000.00, 'AUD',
         base_date + timedelta(days=5), base_date + timedelta(days=365), 800000.00, 533333.33,
         0.00, 106, 206, 1, base_date + timedelta(days=5), base_date + timedelta(days=5),
         base_date + timedelta(days=5), 15, 105, 'AUD/USD Forward', 800000.00, 533333.33,
         base_date + timedelta(days=5)),

        # ANOMALY 7: Duplicate with same generation_id and arrangement_id (exact duplicate)
        (148399, 101001, 1007, 'TRADE-2026-007', 'BOOK-G', 'BUY', 1200000.00, base_date + timedelta(days=10),
         5007, 'EUR', 'USD', base_date + timedelta(days=10), base_date + timedelta(days=10),
         base_date + timedelta(days=180), 1200000.00, 1440000.00, 1150000.00, 'EUR',
         base_date + timedelta(days=10), base_date + timedelta(days=180), 1200000.00, 1440000.00,
         0.00, 107, 207, 1, base_date + timedelta(days=10), base_date + timedelta(days=10),
         base_date + timedelta(days=10), 16, 106, 'EUR/USD Option', 1200000.00, 1440000.00,
         base_date + timedelta(days=10)),

        (148399, 101001, 1007, 'TRADE-2026-007', 'BOOK-G', 'BUY', 1200000.00, base_date + timedelta(days=10),
         5007, 'EUR', 'USD', base_date + timedelta(days=10), base_date + timedelta(days=10),
         base_date + timedelta(days=180), 1200000.00, 1440000.00, 1150000.00, 'EUR',
         base_date + timedelta(days=10), base_date + timedelta(days=180), 1200000.00, 1440000.00,
         0.00, 107, 207, 1, base_date + timedelta(days=10), base_date + timedelta(days=10),
         base_date + timedelta(days=10), 16, 106, 'EUR/USD Option', 1200000.00, 1440000.00,
         base_date + timedelta(days=10)),

        # ANOMALY 8: Negative exposure (shouldn't happen)
        (148400, 201002, 1008, 'TRADE-2026-008', 'BOOK-H', 'SELL', 900000.00, base_date + timedelta(days=12),
         5008, 'CHF', 'EUR', base_date + timedelta(days=12), base_date + timedelta(days=12),
         base_date + timedelta(days=90), -500000.00, -600000.00, 850000.00, 'CHF',
         base_date + timedelta(days=12), base_date + timedelta(days=90), 900000.00, 1080000.00,
         0.00, 108, 208, 1, base_date + timedelta(days=12), base_date + timedelta(days=12),
         base_date + timedelta(days=12), 17, 107, 'CHF/EUR Swap', 900000.00, 1080000.00,
         base_date + timedelta(days=12)),

        # Normal trade for comparison
        (148401, 301003, 1009, 'TRADE-2026-009', 'BOOK-I', 'BUY', 600000.00, base_date + timedelta(days=15),
         5009, 'USD', 'EUR', base_date + timedelta(days=15), base_date + timedelta(days=15),
         base_date + timedelta(days=365), 600000.00, 600000.00, 580000.00, 'USD',
         base_date + timedelta(days=15), base_date + timedelta(days=365), 600000.00, 510000.00,
         0.00, 109, 209, 1, base_date + timedelta(days=15), base_date + timedelta(days=15),
         base_date + timedelta(days=15), 10, 100, 'EUR/USD Swap', 600000.00, 600000.00,
         base_date + timedelta(days=15)),
    ]

    insert_query = """
    INSERT INTO dbo.trade (
        generation_id, arrangement_id, feed_id, src_trade_ref, book_code, buy_sell,
        component_use_pv, component_used_pv_last_updated, counterparty_id, currency_1,
        currency_2, date_created, effective_date, end_date, exposure, exposure_in_usd,
        fed_pv, fed_pv_currency, fed_pv_last_updated, maturity_date, notional_1, notional_2,
        prev_used_pv, principal_id, rule_group_id, status, status_last_updated,
        strike_effective_date, trade_date, trade_type_id, trade_subtype_id,
        used_asset_desc, used_pv, used_pv_in_usd, valuation_date
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    rows_inserted = 0
    print("Inserting sample data with anomalies...")

    for record in sample_records:
        try:
            db.execute_non_query(insert_query, record)
            rows_inserted += 1
        except Exception as e:
            print(f"  ⚠ Error inserting record: {e}")

    print(f"✓ Inserted {rows_inserted} rows into trade")


def verify_anomalies() -> None:
    """Verify and display detected anomalies"""
    db = DatabaseConnection(database="EM")

    print("\n=== Anomaly Detection Summary ===\n")

    # 1. Duplicate trade references
    print("1. Duplicate Trade References:")
    results = db.execute_query("""
        SELECT src_trade_ref, COUNT(*) as count
        FROM trade
        GROUP BY src_trade_ref
        HAVING COUNT(*) > 1
    """)
    for row in results:
        print(f"   Trade Ref: {row['src_trade_ref']}, Count: {row['count']}")

    # 2. Exposure anomalies (exposure > 5x notional)
    print("\n2. Exposure Anomalies (exposure > 5x notional):")
    results = db.execute_query("""
        SELECT src_trade_ref, notional_1, exposure, exposure/notional_1 as ratio
        FROM trade
        WHERE exposure > notional_1 * 5 AND notional_1 > 0
    """)
    for row in results:
        print(f"   Trade: {row['src_trade_ref']}, Notional: {row['notional_1']}, Exposure: {row['exposure']}, Ratio: {row['ratio']:.2f}")

    # 3. Date anomalies
    print("\n3. Date Anomalies (effective_date > maturity_date):")
    results = db.execute_query("""
        SELECT src_trade_ref, effective_date, maturity_date
        FROM trade
        WHERE effective_date > maturity_date
    """)
    for row in results:
        print(f"   Trade: {row['src_trade_ref']}, Effective: {row['effective_date']}, Maturity: {row['maturity_date']}")

    # 4. Active trades past maturity
    print("\n4. Active Trades Past Maturity:")
    results = db.execute_query("""
        SELECT src_trade_ref, maturity_date, status
        FROM trade
        WHERE status = 1 AND maturity_date < GETDATE()
    """)
    for row in results:
        print(f"   Trade: {row['src_trade_ref']}, Maturity: {row['maturity_date']}, Status: Active")

    # 5. Negative exposure
    print("\n5. Negative Exposure:")
    results = db.execute_query("""
        SELECT src_trade_ref, exposure, exposure_in_usd
        FROM trade
        WHERE exposure < 0 OR exposure_in_usd < 0
    """)
    for row in results:
        print(f"   Trade: {row['src_trade_ref']}, Exposure: {row['exposure']}, USD: {row['exposure_in_usd']}")

    # 6. PV discrepancies
    print("\n6. Large PV Discrepancies (|component_use_pv - used_pv| > 10%):")
    results = db.execute_query("""
        SELECT src_trade_ref, component_use_pv, used_pv,
               ABS(component_use_pv - used_pv) / component_use_pv * 100 as pct_diff
        FROM trade
        WHERE component_use_pv > 0 AND ABS(component_use_pv - used_pv) / component_use_pv > 0.1
    """)
    for row in results:
        print(f"   Trade: {row['src_trade_ref']}, Component PV: {row['component_use_pv']}, Used PV: {row['used_pv']}, Diff: {row['pct_diff']:.2f}%")

    # Total count
    result = db.execute_query("SELECT COUNT(*) as total FROM trade")
    print(f"\n✓ Total records: {result[0]['total']}")


def main():
    """Main function"""
    print("=== Trade Details Table Setup ===\n")

    try:
        # Create table
        create_trade_details_table()

        # Insert sample data
        insert_sample_data()

        # Verify anomalies
        verify_anomalies()

        print("\n✓ Trade details setup completed successfully!")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
