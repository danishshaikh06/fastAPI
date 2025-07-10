import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

def get_env_var(var_name: str, default: Optional[str] = None) -> str:
    """Get environment variable with validation"""
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Environment variable '{var_name}' is not set")
    return value

# Database configuration
try:
    DB_NAME = get_env_var("DB_NAME")
    HOST_NAME = get_env_var("HOST_NAME")
    DB_USERNAME = get_env_var("DB_USERNAME")
    DB_PASSWORD = get_env_var("DB_PASSWORD")
    MSSQL_DRIVER = get_env_var("MSSQL_DRIVER")
    TABLE_NAME = get_env_var("TABLE_NAME")
    
    # Build connection string
    CONNECTION_STRING = (
        f"DRIVER={MSSQL_DRIVER};"
        f"SERVER={HOST_NAME};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USERNAME};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )
    
    print("✓ Database configuration loaded successfully")
    print(f"✓ Database: {DB_NAME}")
    print(f"✓ Server: {HOST_NAME}")
    print(f"✓ Table: {TABLE_NAME}")
    
except ValueError as e:
    print(f"❌ Configuration Error: {e}")
    print("❌ Please check your .env file and ensure all required variables are set")
    raise

# Optional: Add validation for database connection parameters
def validate_config():
    """Validate configuration parameters"""
    errors = []
    
    if not DB_NAME:
        errors.append("DB_NAME cannot be empty")
    
    if not HOST_NAME:
        errors.append("HOST_NAME cannot be empty")
    
    if not DB_USERNAME:
        errors.append("DB_USERNAME cannot be empty")
    
    if not DB_PASSWORD:
        errors.append("DB_PASSWORD cannot be empty")
    
    if not MSSQL_DRIVER:
        errors.append("MSSQL_DRIVER cannot be empty")
    
    if not TABLE_NAME:
        errors.append("TABLE_NAME cannot be empty")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    return True

# Run validation
validate_config()