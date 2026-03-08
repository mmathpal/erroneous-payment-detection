# EM Database Setup

This directory contains scripts for setting up and managing the SQL Server database for the Exposure Manager system.

## Prerequisites

1. **SQL Server Docker Container** (already running):
   ```bash
   docker run -e ACCEPT_EULA=Y -e SA_PASSWORD=StrongPassword123! \
     -p 1433:1433 --name sqlserver -d mcr.microsoft.com/azure-sql-edge
   ```

2. **Python Dependencies**:
   ```bash
   pip install pyodbc
   ```

3. **ODBC Driver**:
   - macOS: `brew install unixodbc msodbcsql18`
   - Linux: Follow [Microsoft's instructions](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)
   - Windows: Usually pre-installed

## Setup Steps

### Step 1: Create Database and Tables

```bash
cd src/database
python setup_database.py
```

This script will:
- Create the `EM` database
- Create `ci_collateral_movement` table (20 columns)
- Create `arrangement_clearing_dra` table (8 columns)
- Add appropriate indexes

### Step 2: Load CSV Data

```bash
python load_csv_data.py
```

This script will:
- Read data from `src/data/sample/collateral_movement.csv`
- Read data from `src/data/sample/arrangement_clearing_dra.csv`
- Insert all records into SQL Server tables
- Display verification summary

## Database Schema

### ci_collateral_movement
- **Primary Key**: `collateral_movement_id`
- **Indexes**: `collateral_balance_id`, `transaction_date`, `delivery_or_return`
- **Purpose**: Track collateral movements with split booking detection

### arrangement_clearing_dra
- **Primary Key**: `id`
- **Indexes**: `arrangement_id`, `generation_id`, `calculation_date`, composite index
- **Purpose**: Track DRA calculations and detect duplicates

## Usage in Code

```python
from database.connection import DatabaseConnection

# Connect to EM database
db = DatabaseConnection(database="EM")

# Query data
results = db.execute_query("""
    SELECT * FROM ci_collateral_movement
    WHERE collateral_balance_id = ?
""", (772493,))

# Insert data
db.execute_non_query("""
    INSERT INTO ci_collateral_movement (...)
    VALUES (?, ?, ...)
""", (values,))
```

## Troubleshooting

### Connection Issues
- Verify container is running: `docker ps`
- Test connection: `python -c "from connection import DatabaseConnection; DatabaseConnection().test_connection()"`

### ODBC Driver Not Found
- Check installed drivers: `odbcinst -q -d`
- Update `driver` parameter in `connection.py` if needed

### Permission Errors
- Ensure SQL Server password matches: `StrongPassword123!`
- Check firewall settings for port 1433
