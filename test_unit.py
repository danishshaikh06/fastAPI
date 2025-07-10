# 1. test_unit.py - Unit tests for individual functions
"""
Unit tests for core functions and components
"""

import pytest
import pandas as pd
import io
from unittest.mock import patch, MagicMock, mock_open
from fastapi.testclient import TestClient
from main import app, authenticate_user, save_data_to_database, get_data_from_database

client = TestClient(app)

class TestUnitFunctions:
    """Test individual functions in isolation"""
    
    def test_authenticate_user_valid(self):
        """Test authentication with valid credentials"""
        assert authenticate_user("InsuranceHead", "insurance@123") == True
    
    def test_authenticate_user_invalid(self):
        """Test authentication with invalid credentials"""
        assert authenticate_user("wrong", "password") == False
        assert authenticate_user("sa", "wrong") == False
        assert authenticate_user("", "") == False
    
    def test_database_connection_context_manager(self):
        """Test database connection context manager"""
        with patch('main.pyodbc.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            from main import get_db_connection
            
            with get_db_connection() as conn:
                assert conn == mock_conn
            
            mock_conn.close.assert_called_once()
    
    def test_save_data_to_database_column_mapping(self):
        """Test column mapping logic in save_data_to_database"""
        df = pd.DataFrame({
            'BusInformationId': [1, 2, 3],
            'Company Id': [101, 102, 103],
            'Insurance-Provider': ['Provider1', 'Provider2', 'Provider3'],
            'Policy_Number': ['P001', 'P002', 'P003']
        })

        with patch('main.get_db_connection') as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            # Mock all the database calls in sequence
            mock_cursor.fetchall.side_effect = [
                # First call: get table schema
                [
                    ('BusInformationId', 'int', 'NO', None, 0),
                    ('CompanyId', 'int', 'NO', None, 0),
                    ('InsuranceProvider', 'varchar', 'YES', None, 0),
                    ('PolicyNumber', 'varchar', 'YES', None, 0)
                ],
                # Second call: check for existing BusInformationIds
                [(1,), (2,), (3,)],  # simulate that all 3 BusInformationIds exist
                # Third call: final statistics query
                [(1, 1), (2, 1), (3, 1)]  # bus_id_counts for statistics
            ]

            result = save_data_to_database(df)

            assert result['inserted_count'] == 3  # All should insert
            assert 'BusInformationId' in result['column_mapping'].values()
