from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Header, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pandas as pd
import io
from typing import Dict, Any, List, Optional
import pyodbc
import os
from contextlib import contextmanager
import requests
import jwt
from datetime import datetime
import sys

# Import configuration with error handling
try:
    from config import (
        DB_NAME, HOST_NAME, DB_USERNAME, DB_PASSWORD, 
        MSSQL_DRIVER, TABLE_NAME, CONNECTION_STRING
    )
    print("✓ Configuration imported successfully")
except ImportError as e:
    print(f"❌ Failed to import configuration: {e}")
    print("❌ Please ensure config.py exists and is properly configured")
    sys.exit(1)
except Exception as e:
    print(f"❌ Configuration error: {e}")
    print("❌ Please check your .env file and config.py")
    sys.exit(1)

app = FastAPI(
    title="CSV Upload API",
    description="API for uploading CSV files and managing vehicle insurance data",
    version="1.0.0"
)

# External authentication API configuration
LOGIN_API_URL = "https://dev-tims.transvolt.org/rest-api/auth/login/"

# Global variable to store the uploaded CSV data (keeping for backward compatibility)
uploaded_data = None

# Security scheme for Bearer token
security = HTTPBearer()

@contextmanager
def get_db_connection():
    """Context manager for MS SQL Server database connections"""
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        conn.autocommit = False  # Ensure manual commit control
        try:
            yield conn
        except Exception:
            conn.rollback()  # Rollback on error
            raise
        finally:
            conn.close()
    except pyodbc.Error as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def init_database():
    """Check database connection and initialize if needed"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Test connection
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            print("✓ Database connection successful!")
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
            """, (TABLE_NAME,))
            
            table_exists = cursor.fetchone()[0] > 0
            
            if table_exists:
                print(f"✓ Table '{TABLE_NAME}' exists in database")
            else:
                print(f"⚠️  Table '{TABLE_NAME}' does not exist in database")
                
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("⚠️  API will start but database operations will fail")

def verify_token(token: str) -> bool:
    try:
        if not token or len(token) < 10:
            return False
        
        try:
            # Decode with signature verification using the same secret key
            payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
            
            # Check expiration
            if 'exp' in payload:
                exp_timestamp = payload['exp']
                if datetime.utcnow().timestamp() > exp_timestamp:
                    print(f"Token expired: {exp_timestamp} < {datetime.utcnow().timestamp()}")
                    return False
            
            # Validate the username in the token payload (case-sensitive)
            if 'name' in payload:
                # Check if the username matches expected format/value (case-sensitive)
                username = payload['name']
                print(f"Token username: {username}")  # Debug log
                
                # Define allowed usernames with exact case
                allowed_usernames = ['InsuranceHead']  # Only exact case allowed
                
                if username not in allowed_usernames:
                    print(f"Username {username} not in allowed list")
                    return False
            else:
                print("No username found in token payload")
                return False
            
            print("Token verification successful")
            return True
            
        except jwt.InvalidTokenError as e:
            print(f"Invalid token error: {e}")
            return False
            
    except Exception as e:
        print(f"Token verification error: {e}")
        return False
    
def authenticate_with_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """
    Authenticate user using Bearer token from Authorization header
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header missing or invalid",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    if not verify_token(token):
        raise HTTPException(
            status_code=401, 
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return True

def authenticate_user(username: str, password: str) -> bool:
    """Simple authentication function - keeping for backward compatibility in other endpoints"""
    # Case-sensitive authentication - only "InsuranceHead" is allowed, not "insurancehead"
    ALLOWED_USERNAME = "InsuranceHead"  # Exact case required
    ALLOWED_PASSWORD = "insurance@123"  # API password (different from DB_PASSWORD)
    
    # Check both username and password with case sensitivity
    return username == ALLOWED_USERNAME and password == ALLOWED_PASSWORD

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    init_database()

@app.get("/")
async def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "CSV Upload API is running",
        "version": "1.0.0",
        "database": {
            "name": DB_NAME,
            "server": HOST_NAME,
            "table": TABLE_NAME
        },
        "endpoints": {
            "upload_csv": "/upload-csv/ (POST) - Requires Authorization: Bearer <token>",
            "get_csv": "/upload-csv?company_id=X (GET) - Requires Authorization: Bearer <token>",
            "login": "/auth/login (POST) - Get token for authentication",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        # Test database connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy",
        "database": db_status,
        "configuration": {
            "db_name": DB_NAME,
            "host": HOST_NAME,
            "table": TABLE_NAME
        }
    }

@app.post("/upload-csv/")
async def upload_csv(
    file: UploadFile = File(...),
    save_to_db: bool = Query(False, description="Save data to database"),
    authenticated: bool = Depends(authenticate_with_token)
):
    """
    Upload a CSV file with token-based authentication and optionally save to database.
    
    Headers:
    - Authorization: Bearer <token>
    
    Parameters:
    - file: CSV file to upload
    - save_to_db: Whether to save data to database (default: False)
    """
    global uploaded_data
    
    # Enhanced file validation - check both filename and content type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    # Additional MIME type check
    if file.content_type and not file.content_type.startswith('text/'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        # Read the uploaded file content
        content = await file.read()
        
        # Handle empty files
        if not content or len(content.strip()) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Create a StringIO object to read the CSV content
        csv_data = io.StringIO(content.decode('utf-8'))
        
        # Read CSV using pandas with better error handling and special character support
        try:
            df = pd.read_csv(csv_data, 
                           quotechar='"',  # Handle quoted values
                           escapechar='\\',  # Handle escape characters
                           skipinitialspace=True,  # Skip initial spaces
                           na_values=['NULL', 'null'],  # Handle null values but not empty strings
                           keep_default_na=False,  # Don't convert empty strings to NaN
                           dtype=str)  # Read all as string initially
        except pd.errors.EmptyDataError:
            # Handle empty CSV files gracefully
            df = pd.DataFrame()
        except pd.errors.ParserError as e:
            # Handle malformed CSV files
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")
        
        # Store the data globally for filtering (backward compatibility)
        uploaded_data = df
        print(f"✓ CSV uploaded successfully: {len(df)} rows, {len(df.columns)} columns")
        
        # Save to database if requested
        if save_to_db:
            print("→ Saving data to database...")
            save_result = save_data_to_database(df)
            print(f"✓ Database save completed: {save_result}")
        
        # Convert DataFrame to JSON - handle empty DataFrames
        if df.empty:
            json_data = []
        else:
            json_data = df.to_dict(orient='records')
        
        response = {
            "filename": file.filename,
            "total_records": len(json_data),
            "columns": list(df.columns),
            "data": json_data
        }
        
        if save_to_db:
            response["database_status"] = "Data saved to database successfully"
            response["database_result"] = save_result
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File encoding not supported. Please use UTF-8 encoded CSV files.")
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def save_data_to_database(df: pd.DataFrame):
    """Save DataFrame to MS SQL Server database - ALLOW DUPLICATE BusInformationId VALUES"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get existing table schema with column details
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, 
                   COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') as IsIdentity
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo'
            ORDER BY ORDINAL_POSITION
        """, (TABLE_NAME,))
        
        table_schema = cursor.fetchall()
        
        if not table_schema:
            raise Exception(f"Table {TABLE_NAME} not found in database")
        
        # Create mapping of database columns (excluding identity and system columns)
        db_columns = {}
        insertable_columns = []
        identity_column = None
        
        for col_info in table_schema:
            col_name = col_info[0]
            is_identity = col_info[4] == 1
            
            if is_identity:
                identity_column = col_name
                print(f"Identity column detected: {col_name}")
            elif col_name.lower() not in ['createdat', 'updatedat', 'createdby', 'updatedby']:
                # Skip system audit columns for CSV import
                db_columns[col_name.lower()] = col_name
                insertable_columns.append(col_name)
        
        print(f"Available columns for insert: {insertable_columns}")
        
        # Map CSV columns to database columns
        column_mapping = {}
        unmapped_csv_columns = []
        
        for csv_col in df.columns:
            # Try exact match first
            if csv_col.lower() in db_columns:
                column_mapping[csv_col] = db_columns[csv_col.lower()]
            # Try cleaned match
            else:
                clean_col = csv_col.replace(' ', '').replace('-', '').replace('_', '').lower()
                found = False
                for db_col_lower, db_col_actual in db_columns.items():
                    if clean_col == db_col_lower.replace('_', ''):
                        column_mapping[csv_col] = db_col_actual
                        found = True
                        break
                
                if not found:
                    unmapped_csv_columns.append(csv_col)
        
        print(f"Column mapping: {column_mapping}")
        
        if unmapped_csv_columns:
            print(f"Warning: These CSV columns could not be mapped to database columns: {unmapped_csv_columns}")
        
        if not column_mapping:
            raise Exception("No CSV columns could be mapped to database columns")
        
        # Validate foreign key constraint - Check if BusInformationId values exist in MTN_BusInformation
        bus_info_column = None
        for csv_col, db_col in column_mapping.items():
            if 'businformationid' in db_col.lower():
                bus_info_column = csv_col
                break
        
        existing_bus_ids = set()
        if bus_info_column:
            print(f"Found BusInformationId column: {bus_info_column}")
            
            # Get unique BusInformationId values from CSV
            unique_bus_ids = df[bus_info_column].dropna().unique()
            
            if len(unique_bus_ids) > 0:
                # Check which BusInformationId values exist in MTN_BusInformation table
                placeholders = ','.join(['?' for _ in unique_bus_ids])
                cursor.execute(f"""
                    SELECT BusInformationId FROM MTN_BusInformation 
                    WHERE BusInformationId IN ({placeholders})
                """, tuple(unique_bus_ids))
                
                existing_bus_ids = set([row[0] for row in cursor.fetchall()])
                missing_bus_ids = set(unique_bus_ids) - existing_bus_ids
                
                if missing_bus_ids:
                    print(f"Warning: These BusInformationId values don't exist in MTN_BusInformation: {missing_bus_ids}")
                    print("Records with these IDs will be skipped to maintain foreign key integrity")
                
                print(f"Valid BusInformationId values: {existing_bus_ids}")
        
        # Prepare insert statement
        mapped_db_columns = list(column_mapping.values())
        csv_columns_to_use = [col for col in df.columns if col in column_mapping]
        
        placeholders = ', '.join(['?' for _ in mapped_db_columns])
        column_names = ', '.join([f'[{col}]' for col in mapped_db_columns])
        insert_sql = f"INSERT INTO [{TABLE_NAME}] ({column_names}) VALUES ({placeholders})"
        
        print(f"Insert SQL: {insert_sql}")
        
        # Insert data row by row - ALLOW DUPLICATE BusInformationId VALUES
        inserted_count = 0
        failed_count = 0
        skipped_foreign_key_count = 0
        
        for index, row in df.iterrows():
            try:
                # Check foreign key constraint if BusInformationId column exists
                if bus_info_column and bus_info_column in row:
                    bus_id = row[bus_info_column]
                    if pd.notna(bus_id) and bus_id not in existing_bus_ids:
                        print(f"Skipping row {index + 1}: BusInformationId {bus_id} doesn't exist in MTN_BusInformation")
                        skipped_foreign_key_count += 1
                        continue
                
                # Extract and convert values for mapped columns only
                values = []
                for csv_col in csv_columns_to_use:
                    val = row[csv_col]
                    db_col = column_mapping[csv_col]
                    
                    # Handle None/NaN values
                    if pd.isna(val) or val is None or val == '':
                        values.append(None)
                    else:
                        # Convert based on database column type
                        target_col_info = next((col for col in table_schema if col[0] == db_col), None)
                        if target_col_info:
                            data_type = target_col_info[1].lower()
                            
                            # Convert based on SQL Server data types
                            if data_type in ['int', 'bigint', 'smallint', 'tinyint']:
                                try:
                                    values.append(int(float(val)) if val != '' else None)
                                except (ValueError, TypeError):
                                    values.append(None)
                            elif data_type in ['decimal', 'numeric', 'float', 'real']:
                                try:
                                    values.append(float(val) if val != '' else None)
                                except (ValueError, TypeError):
                                    values.append(None)
                            elif data_type in ['date', 'datetime', 'datetime2']:
                                try:
                                    if isinstance(val, str) and val.strip():
                                        parsed_date = pd.to_datetime(val, errors='coerce')
                                        values.append(parsed_date if not pd.isna(parsed_date) else None)
                                    else:
                                        values.append(None)
                                except:
                                    values.append(None)
                            else:
                                values.append(str(val) if val is not None else None)
                        else:
                            values.append(str(val) if val is not None else None)
                
                # INSERT THE RECORD - No duplicate checking for BusInformationId
                try:
                    cursor.execute(insert_sql, tuple(values))
                    inserted_count += 1
                    
                    # Commit every 50 rows for better performance
                    if inserted_count % 50 == 0:
                        conn.commit()
                        print(f"Inserted {inserted_count} rows so far...")
                        
                except Exception as insert_error:
                    # Only handle actual constraint violations or database errors
                    print(f"Error inserting row {index + 1}: {insert_error}")
                    failed_count += 1
                    # Continue to next row
                    continue
                    
            except Exception as row_error:
                print(f"Error processing row {index + 1}: {row_error}")
                print(f"Row data: {dict(zip(csv_columns_to_use, [row[col] for col in csv_columns_to_use]))}")
                failed_count += 1
                # Continue to next row
                continue
        
        # Final commit
        conn.commit()
        
        print(f"Data insertion completed!")
        print(f"Successfully inserted: {inserted_count} rows")
        print(f"Skipped due to foreign key constraint: {skipped_foreign_key_count} rows")
        print(f"Failed insertions: {failed_count} rows")
        
        # Show some statistics about the inserted data
        if bus_info_column and inserted_count > 0:
            cursor.execute(f"""
                SELECT [{column_mapping[bus_info_column]}], COUNT(*) as count 
                FROM [{TABLE_NAME}] 
                GROUP BY [{column_mapping[bus_info_column]}] 
                ORDER BY count DESC
            """)
            bus_id_counts = cursor.fetchall()
            print(f"BusInformationId distribution after insert (top 10):")
            for i, (bus_id, count) in enumerate(bus_id_counts[:10]):
                print(f"  BusInformationId {bus_id}: {count} records")
        
        return {
            "inserted_count": inserted_count,
            "skipped_foreign_key_count": skipped_foreign_key_count,
            "failed_count": failed_count,
            "total_processed": len(df),
            "column_mapping": column_mapping,
            "unmapped_columns": unmapped_csv_columns
        }

@app.get("/upload-csv")
async def get_csv_by_company(
    company_id: int = Query(..., description="Company ID to filter data"),
    from_database: bool = Query(False, description="Fetch data from database"),
    authenticated: bool = Depends(authenticate_with_token)
):
    """
    Get CSV data filtered by company_id from memory or database with token authentication
    """
    global uploaded_data
    
    if from_database:
        return get_data_from_database(company_id)
    else:
        # Use existing in-memory logic
        if uploaded_data is None:
            raise HTTPException(status_code=404, detail="No CSV data found. Please upload a CSV file first using POST /upload-csv/")
        
        try:
            # Check if company_id column exists (case insensitive)
            company_col = None
            for col in uploaded_data.columns:
                if 'company' in col.lower() and 'id' in col.lower():
                    company_col = col
                    break
            
            if company_col is None:
                raise HTTPException(status_code=400, detail="No company_id column found in the uploaded data")
            
            # Filter data by company_id
            filtered_df = uploaded_data[uploaded_data[company_col] == company_id]
            
            if filtered_df.empty:
                return {
                    "company_id": company_id,
                    "total_records": 0,
                    "message": f"No records found for company_id: {company_id}",
                    "data": []
                }
            
            # Convert filtered data to JSON
            json_data = filtered_df.to_dict(orient='records')
            
            return {
                "company_id": company_id,
                "total_records": len(json_data),
                "columns": list(filtered_df.columns),
                "data": json_data
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error filtering data: {str(e)}")

def get_data_from_database(company_id: int):
    """Fetch data from MS SQL Server database filtered by company_id"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = ?
            """, (TABLE_NAME,))
            
            if cursor.fetchone()[0] == 0:
                raise HTTPException(status_code=404, detail=f"Table '{TABLE_NAME}' not found in database")
            
            # Get column names
            cursor.execute("""
                SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ?
            """, (TABLE_NAME,))
            
            columns = [row[0] for row in cursor.fetchall()]
            
            company_col = None
            for col in columns:
                if 'company' in col.lower() and 'id' in col.lower():
                    company_col = col
                    break
            
            if company_col is None:
                raise HTTPException(status_code=400, detail="No company_id column found in the database table")
            
            # Fetch filtered data
            cursor.execute(f"""
                SELECT * FROM [{TABLE_NAME}] 
                WHERE [{company_col}] = ?
            """, (company_id,))
            
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    "company_id": company_id,
                    "total_records": 0,
                    "message": f"No records found for company_id: {company_id}",
                    "data": [],
                    "source": "database"
                }
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    row_dict[col] = row[i]
                data.append(row_dict)
            
            return {
                "company_id": company_id,
                "total_records": len(data),
                "columns": columns,
                "data": data,
                "source": "database"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# Login endpoint with local case-sensitive authentication
@app.post("/auth/login")
async def login_for_token(
    username: str = Query(..., description="Username"),
    password: str = Query(..., description="Password")
):
    """
    Login endpoint with case-sensitive authentication
    Only accepts exact username: 'InsuranceHead' (case-sensitive)
    """
    # Use local case-sensitive authentication
    if not authenticate_user(username, password):
        raise HTTPException(
            status_code=401, 
            detail="Invalid credentials. Username and password are case-sensitive."
        )
    
    # Generate a simple token (in production, use proper JWT with secret)
    import time
    token_payload = {
        "name": username,
        "exp": int(time.time()) + 3600,  # Token expires in 1 hour
        "iat": int(time.time())
    }
    
    # Create a simple JWT token (for development - use proper secret in production)
    token = jwt.encode(token_payload, "your-secret-key", algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600,
        "username": username
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)