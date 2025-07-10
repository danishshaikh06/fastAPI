# CSV Upload API

This is a FastAPI-based application designed to manage vehicle insurance data via CSV file uploads. It provides token-based authentication, data processing, and integration with an MS SQL Server database.

## Features

- **CSV Upload & Validation**: Upload CSV files with strict validation for content type and structure.
- **Authentication**: Token-based authentication to ensure secure access to endpoints.
- **Data Processing**: Map CSV columns to match the database schema, with additional handling for special characters and edge cases.
- **Database Integration**: Utilize parameterized queries to interact securely with an MS SQL Server database.
- **API Endpoints**: Comprehensive REST APIs for data upload, retrieval, and health checks.

## Getting Started

### Prerequisites

- **Python 3.9+**
- **FastAPI**
- **MS SQL Server with pyodbc**

### Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd dummy_testing
pip install -r requirements-test.txt
```

### Environment Setup

Ensure you have the following environment variables set in a `.env` file:

```
DB_NAME=<Your DB Name>
HOST_NAME=<Your Host Name>
DB_USERNAME=<Your DB Username>
DB_PASSWORD=<Your DB Password>
MSSQL_DRIVER=<Your MSSQL Driver>
TABLE_NAME=<Your Table Name>
```

### Running the Application

#### Development Mode

```bash
python main.py
```

#### Production Mode

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Testing

Run tests using `pytest`:

```bash
pytest
```

## Test Results

- **Authentication**: Validated case-sensitive user credentials.
- **CSV Upload**: Fully functional file processing and database insertion.
- **Error Handling**: Comprehensive testing for invalid operations.
- **Deployment Readiness**: Confirmed compatibility with FastAPI and Uvicorn.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

