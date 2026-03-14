"""Configuration management."""
from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "EM- Payment Risk Management System"
    app_version: str = "0.1.0"
    debug: bool = True

    # SQL Server
    sql_server_host: str = "localhost"
    sql_server_port: int = 1433
    sql_server_database: str = "EM"
    sql_server_username: str = "sa"
    sql_server_password: str = "StrongPassword123!"
    sql_server_driver: str = "ODBC Driver 18 for SQL Server"

    # Paths
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "src" / "data" / "sample"
    logs_dir: Path = project_root / "logs"
    models_dir: Path = project_root / "models"

    # ML Models
    isolation_forest_contamination: float = 0.1

    # Thresholds
    fraud_threshold: float = 0.7
    alert_threshold: float = 0.8
    duplicate_time_window_minutes: int = 120  # 2 hours

    # Logging
    log_level: str = "INFO"

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


# Create directories if they don't exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.logs_dir.mkdir(parents=True, exist_ok=True)
settings.models_dir.mkdir(parents=True, exist_ok=True)
