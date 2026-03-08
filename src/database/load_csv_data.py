#!/usr/bin/env python3
"""
Data migration script: Load CSV data into SQL Server tables
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
from connection import DatabaseConnection


def get_csv_path() -> Path:
    """Get path to CSV data directory"""
    return Path(__file__).parent.parent / "data" / "sample"


def load_collateral_movement_data() -> None:
    """Load data from collateral_movement.csv into SQL Server table"""
    db = DatabaseConnection(database="EM")
    csv_file = get_csv_path() / "collateral_movement.csv"

    if not csv_file.exists():
        print(f"⚠ CSV file not found: {csv_file}")
        return

    print(f"Loading data from {csv_file.name}...")

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows_inserted = 0

        for row in reader:
            # Skip empty rows
            if not row.get('collateral_movement_id'):
                continue

            insert_query = """
            INSERT INTO dbo.ci_collateral_movement (
                collateral_movement_id,
                collateral_balance_id,
                workflow_task_id,
                delivery_or_return,
                nominal,
                settlement_status_id,
                transaction_date,
                expected_settlement_date,
                arts_reference,
                input_user,
                input_date,
                last_updated_user,
                last_updated_date,
                failed_flag,
                failed_reason_code_id,
                failed_comment_id,
                reversal_movement_flag,
                valuation_percentage,
                is_gmi_adjustment,
                is_manual_flag
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                int(row['collateral_movement_id']),
                int(row['collateral_balance_id']),
                int(row['workflow_task_id']) if row.get('workflow_task_id') else None,
                row.get('delivery_or_return'),
                float(row['nominal']) if row.get('nominal') else None,
                int(row['settlement_status_id']) if row.get('settlement_status_id') else None,
                row.get('transaction_date'),
                row.get('expected_settlement_date'),
                row.get('arts_reference'),
                row.get('input_user'),
                row.get('input_date'),
                row.get('last_updated_user'),
                row.get('last_updated_date'),
                row.get('failed_flag'),
                int(row['failed_reason_code_id']) if row.get('failed_reason_code_id') else None,
                int(row['failed_comment_id']) if row.get('failed_comment_id') else None,
                int(row['reversal_movement_flag']) if row.get('reversal_movement_flag') else 0,
                float(row['valuation_percentage']) if row.get('valuation_percentage') else None,
                int(row['is_gmi_adjustment']) if row.get('is_gmi_adjustment') else 0,
                int(row['is_manual_flag']) if row.get('is_manual_flag') else 0
            )

            try:
                db.execute_non_query(insert_query, params)
                rows_inserted += 1
            except Exception as e:
                print(f"  ⚠ Error inserting row {row['collateral_movement_id']}: {e}")

    print(f"✓ Inserted {rows_inserted} rows into ci_collateral_movement")


def load_arrangement_clearing_dra_data() -> None:
    """Load data from arrangement_clearing_dra.csv into SQL Server table"""
    db = DatabaseConnection(database="EM")
    csv_file = get_csv_path() / "arrangement_clearing_dra.csv"

    if not csv_file.exists():
        print(f"⚠ CSV file not found: {csv_file}")
        return

    print(f"Loading data from {csv_file.name}...")

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows_inserted = 0

        for row in reader:
            # Skip empty rows
            if not row.get('id'):
                continue

            insert_query = """
            INSERT INTO dbo.arrangement_clearing_dra (
                id,
                arrangement_id,
                generation_id,
                calculation_date,
                cashflow_dra,
                interest_dra,
                ulu,
                dlu
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                int(row['id']),
                int(row['arrangement_id']),
                int(row['generation_id']),
                row.get('calculation_date'),
                float(row['cashflow_dra']) if row.get('cashflow_dra') else None,
                float(row['interest_dra']) if row.get('interest_dra') else None,
                row.get('ulu'),
                row.get('dlu')
            )

            try:
                db.execute_non_query(insert_query, params)
                rows_inserted += 1
            except Exception as e:
                print(f"  ⚠ Error inserting row {row['id']}: {e}")

    print(f"✓ Inserted {rows_inserted} rows into arrangement_clearing_dra")


def verify_data() -> None:
    """Verify data was loaded correctly"""
    db = DatabaseConnection(database="EM")

    print("\n=== Data Verification ===")

    # Count collateral_movement records
    result = db.execute_query("SELECT COUNT(*) as count FROM dbo.ci_collateral_movement")
    print(f"ci_collateral_movement: {result[0]['count']} records")

    # Count arrangement_clearing_dra records
    result = db.execute_query("SELECT COUNT(*) as count FROM dbo.arrangement_clearing_dra")
    print(f"arrangement_clearing_dra: {result[0]['count']} records")

    # Show sample collateral_movement data
    print("\n=== Sample Data: ci_collateral_movement (first 3 rows) ===")
    result = db.execute_query("""
        SELECT TOP 3
            collateral_movement_id,
            collateral_balance_id,
            delivery_or_return,
            nominal,
            transaction_date
        FROM dbo.ci_collateral_movement
        ORDER BY collateral_movement_id
    """)
    for row in result:
        print(f"  ID: {row['collateral_movement_id']}, Balance: {row['collateral_balance_id']}, "
              f"Type: {row['delivery_or_return']}, Amount: {row['nominal']}, Date: {row['transaction_date']}")

    # Show sample arrangement_clearing_dra data
    print("\n=== Sample Data: arrangement_clearing_dra (first 3 rows) ===")
    result = db.execute_query("""
        SELECT TOP 3
            id,
            arrangement_id,
            generation_id,
            calculation_date,
            cashflow_dra
        FROM dbo.arrangement_clearing_dra
        ORDER BY id
    """)
    for row in result:
        print(f"  ID: {row['id']}, Arrangement: {row['arrangement_id']}, "
              f"Generation: {row['generation_id']}, Date: {row['calculation_date']}, "
              f"Cashflow DRA: {row['cashflow_dra']}")


def main():
    """Main data loading function"""
    print("=== EM Database Data Loading ===\n")

    try:
        # Load collateral movement data
        load_collateral_movement_data()

        # Load arrangement clearing DRA data
        load_arrangement_clearing_dra_data()

        # Verify data
        verify_data()

        print("\n✓ Data loading completed successfully!")

    except Exception as e:
        print(f"\n✗ Error during data loading: {e}")
        raise


if __name__ == "__main__":
    main()
