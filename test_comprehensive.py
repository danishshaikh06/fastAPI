# test_comprehensive.py - Comprehensive tests for FastAPI endpoints
"""
Comprehensive tests for FastAPI application endpoints and functionality
"""

import pytest
import pandas as pd
import io
from unittest.mock import patch, MagicMock, mock_open
from fastapi.testclient import TestClient
from main import app, authenticate_user, save_data_to_database, get_data_from_database

client = TestClient(app)

# Helper function to get authentication token
def get_auth_token():
    """Get authentication token for testing"""
    response = client.post("/auth/login", params={
        "username": "InsuranceHead",
        "password": "insurance@123"
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

# Helper function to get authorization headers
def get_auth_headers():
    """Get authorization headers for testing"""
    token = get_auth_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

class TestFastAPIEndpoints:
    """Test FastAPI endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CSV Upload API is running"
        assert "endpoints" in data
        assert "upload_csv" in data["endpoints"]
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_upload_csv_without_file(self):
        """Test upload CSV endpoint without file"""
        headers = get_auth_headers()
        response = client.post("/upload-csv/", headers=headers)
        assert response.status_code == 422  # Validation error
    
    def test_upload_csv_with_wrong_file_type(self):
        """Test upload CSV endpoint with wrong file type"""
        # Create a fake text file using BytesIO
        fake_content = b"This is not a CSV file"
        fake_file = io.BytesIO(fake_content)
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("test.txt", fake_file, "text/plain")},
            headers=headers
        )
        assert response.status_code == 400
        assert "Only CSV files are allowed" in response.json()["detail"]
    
    @patch('main.uploaded_data', None)
    def test_upload_csv_with_valid_csv(self):
        """Test upload CSV endpoint with valid CSV file"""
        # Create a valid CSV content using BytesIO
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n1,101,Provider1,P001\n2,102,Provider2,P002"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("test.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.csv"
        assert data["total_records"] == 2
        assert "BusInformationId" in data["columns"]
        assert len(data["data"]) == 2
    
    def test_upload_csv_with_invalid_auth(self):
        """Test upload CSV with invalid authentication"""
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n1,101,Provider1,P001"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        # Use invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post(
            "/upload-csv/",
            files={"file": ("test.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "true"}
        )
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]
    
    def test_get_csv_without_uploaded_data(self):
        """Test GET CSV endpoint without uploaded data"""
        with patch('main.uploaded_data', None):
            headers = get_auth_headers()
            response = client.get("/upload-csv", params={"company_id": 101}, headers=headers)
            assert response.status_code == 404
            assert "No CSV data found" in response.json()["detail"]
    
    def test_get_csv_with_uploaded_data(self):
        """Test GET CSV endpoint with uploaded data"""
        # Mock uploaded data
        mock_data = pd.DataFrame({
            'BusInformationId': [1, 2, 3],
            'CompanyId': [101, 101, 102],
            'InsuranceProvider': ['Provider1', 'Provider2', 'Provider3'],
            'PolicyNumber': ['P001', 'P002', 'P003']
        })
        
        with patch('main.uploaded_data', mock_data):
            headers = get_auth_headers()
            response = client.get("/upload-csv", params={"company_id": 101}, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["company_id"] == 101
            assert data["total_records"] == 2  # Only 2 records with CompanyId 101
            assert len(data["data"]) == 2
    
    def test_get_csv_with_invalid_company_id(self):
        """Test GET CSV endpoint with invalid company ID"""
        mock_data = pd.DataFrame({
            'BusInformationId': [1, 2, 3],
            'CompanyId': [101, 101, 102],
            'InsuranceProvider': ['Provider1', 'Provider2', 'Provider3'],
            'PolicyNumber': ['P001', 'P002', 'P003']
        })
        
        with patch('main.uploaded_data', mock_data):
            headers = get_auth_headers()
            response = client.get("/upload-csv", params={"company_id": 999}, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["company_id"] == 999
            assert data["total_records"] == 0
            assert "No records found" in data["message"]
    
    def test_login_endpoint(self):
        """Test login endpoint for token generation"""
        # Test successful login
        response = client.post("/auth/login", params={
            "username": "InsuranceHead",
            "password": "insurance@123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        
        # Test failed login
        response = client.post("/auth/login", params={
            "username": "wrong",
            "password": "wrong"
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

class TestDataProcessing:
    """Test data processing functions"""
    
    def test_authenticate_user_edge_cases(self):
        """Test authentication with edge cases"""
        assert authenticate_user("InsuranceHead", "insurance@123") == True
        assert authenticate_user("insurancehead", "insurance@123") == False  # Case sensitive
        assert authenticate_user("InsuranceHead", "INSURANCE@123") == False  # Case sensitive
        assert authenticate_user(None, None) == False
        assert authenticate_user("", "") == False
        assert authenticate_user("InsuranceHead", "") == False
        assert authenticate_user("", "insurance@123") == False
    
    def test_csv_file_processing(self):
        """Test CSV file processing functionality"""
        # Test with different CSV formats
        csv_content = "BusInformationId,Company Id,Insurance-Provider,Policy_Number\n1,101,Provider1,P001\n2,102,Provider2,P002"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("test.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 2
        assert "BusInformationId" in data["columns"]
        assert "Company Id" in data["columns"]
        assert "Insurance-Provider" in data["columns"]
        assert "Policy_Number" in data["columns"]
    
    def test_empty_csv_file(self):
        """Test processing of empty CSV file"""
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("empty.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 0
        assert "BusInformationId" in data["columns"]
        assert len(data["data"]) == 0
    
    def test_csv_with_special_characters(self):
        """Test CSV processing with special characters"""
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n1,101,\"Provider, Inc.\",P001\n2,102,\"Provider with quotes\",P002"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("special.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 2
        assert "BusInformationId" in data["columns"]
        # Check that special characters are handled properly
        assert "Provider, Inc." in str(data["data"])
        assert "Provider with quotes" in str(data["data"])

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_invalid_csv_format(self):
        """Test handling of invalid CSV format"""
        # Invalid CSV content
        csv_content = "This is not a valid CSV format\nJust some random text"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("invalid.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "false"}
        )
        # Should still process but with unexpected columns
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 1
    
    def test_large_file_handling(self):
        """Test handling of large CSV files"""
        # Create a CSV with many rows
        header = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n"
        rows = [f"{i},{i % 10 + 100},Provider{i},P{i:03d}" for i in range(1, 1001)]
        csv_content = header + "\n".join(rows)
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        headers = get_auth_headers()
        response = client.post(
            "/upload-csv/",
            files={"file": ("large.csv", csv_file, "text/csv")},
            headers=headers,
            params={"save_to_db": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_records"] == 1000
        assert len(data["data"]) == 1000
    
    def test_missing_required_parameters(self):
        """Test handling of missing required parameters"""
        headers = get_auth_headers()
        response = client.get("/upload-csv", headers=headers)
        assert response.status_code == 422  # Validation error for missing company_id

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
