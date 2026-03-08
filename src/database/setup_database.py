#!/usr/bin/env python3
"""
Database setup script for EM (Exposure Manager) system
Creates database and tables for collateral_movement and arrangement_clearing_dra
"""

from connection import DatabaseConnection


def create_em_database() -> None:
    """Create EM database if it doesn't exist"""
    # Connect without database context to create database
    db = DatabaseConnection(database=None)

    create_db_script = """
    IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'EM')
    BEGIN
        CREATE DATABASE EM;
    END
    """

    print("Creating EM database...")
    db.execute_script(create_db_script, autocommit=True)
    print("✓ EM database created successfully")


def create_tables() -> None:
    """Create tables in EM database"""
    # Connect to EM database
    db = DatabaseConnection(database="EM")

    # Create ci_collateral_movement table
    create_collateral_movement_table = """
    IF OBJECT_ID('dbo.ci_collateral_movement', 'U') IS NOT NULL
        DROP TABLE dbo.ci_collateral_movement;
    GO

    CREATE TABLE dbo.ci_collateral_movement (
        collateral_movement_id INT PRIMARY KEY,
        collateral_balance_id INT NOT NULL,
        workflow_task_id INT,
        delivery_or_return CHAR(1),
        nominal DECIMAL(18, 2),
        settlement_status_id INT,
        transaction_date DATE,
        expected_settlement_date DATE,
        arts_reference VARCHAR(50),
        input_user VARCHAR(50),
        input_date DATETIME,
        last_updated_user VARCHAR(50),
        last_updated_date DATETIME,
        failed_flag CHAR(1),
        failed_reason_code_id INT,
        failed_comment_id INT,
        reversal_movement_flag BIT,
        valuation_percentage DECIMAL(5, 2),
        is_gmi_adjustment BIT,
        is_manual_flag BIT,

        INDEX idx_collateral_balance_id (collateral_balance_id),
        INDEX idx_transaction_date (transaction_date),
        INDEX idx_delivery_or_return (delivery_or_return)
    );
    GO
    """

    print("Creating ci_collateral_movement table...")
    db.execute_script(create_collateral_movement_table)
    print("✓ ci_collateral_movement table created successfully")

    # Create arrangement_clearing_dra table
    create_arrangement_dra_table = """
    IF OBJECT_ID('dbo.arrangement_clearing_dra', 'U') IS NOT NULL
        DROP TABLE dbo.arrangement_clearing_dra;
    GO

    CREATE TABLE dbo.arrangement_clearing_dra (
        id INT PRIMARY KEY,
        arrangement_id INT NOT NULL,
        generation_id INT NOT NULL,
        calculation_date DATE,
        cashflow_dra DECIMAL(18, 2),
        interest_dra DECIMAL(18, 2),
        ulu VARCHAR(50),
        dlu DATETIME,

        INDEX idx_arrangement_id (arrangement_id),
        INDEX idx_generation_id (generation_id),
        INDEX idx_calculation_date (calculation_date),
        INDEX idx_composite (arrangement_id, generation_id, calculation_date)
    );
    GO
    """

    print("Creating arrangement_clearing_dra table...")
    db.execute_script(create_arrangement_dra_table)
    print("✓ arrangement_clearing_dra table created successfully")


def verify_tables() -> None:
    """Verify that tables were created successfully"""
    db = DatabaseConnection(database="EM")

    query = """
    SELECT
        t.name AS table_name,
        COUNT(c.column_id) AS column_count
    FROM sys.tables t
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    WHERE t.name IN ('ci_collateral_movement', 'arrangement_clearing_dra')
    GROUP BY t.name
    """

    results = db.execute_query(query)

    print("\n=== Database Verification ===")
    for row in results:
        print(f"Table: {row['table_name']}, Columns: {row['column_count']}")


def main():
    """Main setup function"""
    print("=== EM Database Setup ===\n")

    try:
        # Step 1: Create database
        create_em_database()

        # Step 2: Create tables
        create_tables()

        # Step 3: Verify
        verify_tables()

        print("\n✓ Database setup completed successfully!")

    except Exception as e:
        print(f"\n✗ Error during setup: {e}")
        raise


if __name__ == "__main__":
    main()
