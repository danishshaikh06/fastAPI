# test_integration.py - Integration tests for main.py FastAPI application
"""
Integration tests to verify main.py is working properly
"""

import pytest
import tempfile
import os
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, authenticate_user

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

class TestMainFunctionality:
    """Test main.py functionality"""
    
    def test_basic_endpoints_work(self):
        """Test that basic endpoints are working"""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CSV Upload API is running"
        
        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        print("✓ Basic endpoints are working")
    
    def test_authentication_function(self):
        """Test authentication function"""
        assert authenticate_user("InsuranceHead", "insurance@123") == True
        assert authenticate_user("wrong", "password") == False
        assert authenticate_user("sa", "wrong") == False
        assert authenticate_user("", "") == False
        print("✓ Authentication function is working")
    
    def test_csv_upload_endpoint_validation(self):
        """Test CSV upload endpoint validation"""
        # Test missing file
        headers = get_auth_headers()
        response = client.post("/upload-csv/", headers=headers)
        assert response.status_code == 422
        print("✓ CSV upload validation is working")
    
    def test_csv_upload_with_real_file(self):
        """Test CSV upload with actual file"""
        # Create a temporary CSV file
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n1,101,Provider1,P001\n2,102,Provider2,P002"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            # Open the file and upload it
            with open(temp_file_path, 'rb') as f:
                headers = get_auth_headers()
                response = client.post(
                    "/upload-csv/",
                    files={"file": ("test.csv", f, "text/csv")},
                    headers=headers,
                    params={"save_to_db": "false"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "test.csv"
            assert data["total_records"] == 2
            assert "BusInformationId" in data["columns"]
            print("✓ CSV upload with real file is working")
            
        finally:
            # Clean up
            os.unlink(temp_file_path)
    
    def test_csv_upload_with_wrong_file_type(self):
        """Test CSV upload with wrong file type"""
        # Create a temporary text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a CSV file")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                headers = get_auth_headers()
                response = client.post(
                    "/upload-csv/",
                    files={"file": ("test.txt", f, "text/plain")},
                    headers=headers
                )
            
            assert response.status_code == 400
            assert "Only CSV files are allowed" in response.json()["detail"]
            print("✓ File type validation is working")
            
        finally:
            os.unlink(temp_file_path)
    
    def test_csv_upload_with_invalid_auth(self):
        """Test CSV upload with invalid authentication"""
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n1,101,Provider1,P001"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                headers = {"Authorization": "Bearer invalid_token"}
                response = client.post(
                    "/upload-csv/",
                    files={"file": ("test.csv", f, "text/csv")},
                    headers=headers,
                    params={"save_to_db": "true"}
                )
            
            assert response.status_code == 401
            assert "Invalid or expired token" in response.json()["detail"]
            print("✓ Authentication validation is working")
            
        finally:
            os.unlink(temp_file_path)
    
    def test_get_csv_without_data(self):
        """Test GET CSV endpoint without uploaded data"""
        with patch('main.uploaded_data', None):
            headers = get_auth_headers()
            response = client.get("/upload-csv", params={"company_id": 101}, headers=headers)
            assert response.status_code == 404
            assert "No CSV data found" in response.json()["detail"]
            print("✓ GET CSV validation is working")
    
    def test_get_csv_with_data(self):
        """Test GET CSV endpoint with uploaded data"""
        import pandas as pd
        
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
            print("✓ GET CSV with data is working")
    
    def test_large_csv_handling(self):
        """Test handling of large CSV files"""
        # Create a large CSV file
        header = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n"
        rows = [f"{i},{i % 10 + 100},Provider{i},P{i:03d}" for i in range(1, 501)]  # 500 rows
        csv_content = header + "\n".join(rows)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name

        try:
            with open(temp_file_path, 'rb') as f:
                headers = get_auth_headers()
                response = client.post(
                    "/upload-csv/",
                    files={"file": ("large.csv", f, "text/csv")},
                    headers=headers,
                    params={"save_to_db": "false"}
                )

            assert response.status_code == 200
            data = response.json()
            assert data["total_records"] == 500
            assert "BusInformationId" in data["columns"]
            print("✓ Large CSV handling is working")

        finally:
            os.unlink(temp_file_path)
    
    def test_empty_csv_handling(self):
        """Test handling of empty CSV files"""
        csv_content = "BusInformationId,CompanyId,InsuranceProvider,PolicyNumber\n"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                headers = get_auth_headers()
                response = client.post(
                    "/upload-csv/",
                    files={"file": ("empty.csv", f, "text/csv")},
                    headers=headers,
                    params={"save_to_db": "false"}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_records"] == 0
            assert len(data["data"]) == 0
            print("✓ Empty CSV handling is working")
            
        finally:
            os.unlink(temp_file_path)

def test_main_application_startup():
    """Test that the main application starts up correctly"""
    # This test ensures the FastAPI app can be created and basic routes work
    response = client.get("/")
    assert response.status_code == 200
    print("✓ Main application startup is working")

def test_error_handling():
    """Test error handling in the application"""
    # Test invalid endpoint
    response = client.get("/nonexistent")
    assert response.status_code == 404
    
    # Test missing required parameters
    headers = get_auth_headers()
    response = client.get("/upload-csv", headers=headers)
    assert response.status_code == 422
    
    print("✓ Error handling is working")

if __name__ == "__main__":
    # Run the tests
    test_main_application_startup()
    
    test_instance = TestMainFunctionality()
    test_instance.test_basic_endpoints_work()
    test_instance.test_authentication_function()
    test_instance.test_csv_upload_endpoint_validation()
    test_instance.test_csv_upload_with_real_file()
    test_instance.test_csv_upload_with_wrong_file_type()
    test_instance.test_csv_upload_with_invalid_auth()
    test_instance.test_get_csv_without_data()
    test_instance.test_get_csv_with_data()
    test_instance.test_large_csv_handling()
    test_instance.test_empty_csv_handling()
    
    test_error_handling()
    
    print("\n🎉 All tests passed! The main.py application is working properly.")
