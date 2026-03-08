#!/usr/bin/env python3
"""
Database connection utilities for SQL Server
"""

import pyodbc
from typing import Optional
from contextlib import contextmanager


class DatabaseConnection:
    """Manages SQL Server database connections"""

    def __init__(
        self,
        server: str = "localhost",
        port: int = 1433,
        database: Optional[str] = None,
        username: str = "sa",
        password: str = "StrongPassword123!",
        driver: str = "FreeTDS"
    ):
        """
        Initialize database connection parameters

        Args:
            server: SQL Server hostname
            port: SQL Server port
            database: Database name (None for no database context)
            username: SQL Server username
            password: SQL Server password
            driver: ODBC driver name
        """
        self.server = server
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver

    def get_connection_string(self) -> str:
        """
        Build SQL Server connection string

        Returns:
            ODBC connection string
        """
        # Use full path for FreeTDS driver
        driver_path = "/opt/homebrew/Cellar/freetds/1.5.14/lib/libtdsodbc.so"

        conn_parts = [
            f"DRIVER={driver_path}",
            f"SERVER={self.server}",
            f"PORT={self.port}",
            f"UID={self.username}",
            f"PWD={self.password}",
            "TDS_Version=7.4"
        ]

        if self.database:
            conn_parts.append(f"DATABASE={self.database}")

        return ";".join(conn_parts)

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections

        Yields:
            pyodbc.Connection object

        Example:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
        """
        conn = None
        try:
            conn = pyodbc.connect(self.get_connection_string())
            yield conn
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        Execute a SELECT query and return results

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            List of rows as dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            columns = [column[0] for column in cursor.description] if cursor.description else []
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            return results

    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query

        Args:
            query: SQL query string
            params: Query parameters (optional)

        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount

    def execute_script(self, script: str, autocommit: bool = False) -> None:
        """
        Execute a SQL script (multiple statements)

        Args:
            script: SQL script with multiple statements
            autocommit: Set autocommit mode (required for CREATE DATABASE)
        """
        with self.get_connection() as conn:
            if autocommit:
                conn.autocommit = True
            cursor = conn.cursor()
            # Split by GO statements and execute each batch
            batches = script.split("GO")
            for batch in batches:
                batch = batch.strip()
                if batch:
                    cursor.execute(batch)
            if not autocommit:
                conn.commit()

    def test_connection(self) -> bool:
        """
        Test database connection

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()
                print(f"Connected to SQL Server: {version[0]}")
                return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False


if __name__ == "__main__":
    # Test connection
    db = DatabaseConnection()
    db.test_connection()
