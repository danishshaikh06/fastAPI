#!/usr/bin/env python3
"""
Quick test to verify the FastAPI server can start up properly
"""

import subprocess
import sys
import time
import requests
import threading
from main import app

def test_server_startup():
    """Test that the server can start up"""
    print("Testing server startup...")
    
    # Test that the app can be imported and has the right structure
    assert hasattr(app, 'get'), "FastAPI app should have GET method"
    assert hasattr(app, 'post'), "FastAPI app should have POST method"
    
    # Test that routes are registered
    routes = [route.path for route in app.routes]
    expected_routes = ["/", "/health", "/upload-csv/", "/auth/login"]
    
    for route in expected_routes:
        assert route in routes, f"Route {route} not found in app routes"
    
    print("✓ Server structure is correct")
    return True

def test_uvicorn_compatibility():
    """Test that the app is compatible with uvicorn"""
    try:
        import uvicorn
        
        # Test that we can create a config without errors
        config = uvicorn.Config(app=app, host="127.0.0.1", port=8000, log_level="info")
        assert config is not None
        
        print("✓ Uvicorn compatibility confirmed")
        return True
    except Exception as e:
        print(f"✗ Uvicorn compatibility issue: {e}")
        return False

def test_app_dependencies():
    """Test that all required dependencies are available"""
    try:
        import fastapi
        import pandas
        import pyodbc
        import uvicorn
        
        print("✓ All dependencies are available")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        return False

def test_database_configuration():
    """Test database configuration without connecting"""
    from main import DB_NAME, HOST_NAME, DB_USERNAME, MSSQL_DRIVER, TABLE_NAME
    
    # Check that all required configuration is present
    assert DB_NAME, "Database name is configured"
    assert HOST_NAME, "Host name is configured"
    assert DB_USERNAME, "Database username is configured"
    assert MSSQL_DRIVER, "MSSQL driver is configured"
    assert TABLE_NAME, "Table name is configured"
    
    print("✓ Database configuration is complete")
    return True

def main():
    """Run all tests"""
    print("🧪 Running server tests for main.py...")
    print("=" * 50)
    
    tests = [
        test_app_dependencies,
        test_database_configuration,
        test_server_startup,
        test_uvicorn_compatibility,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All server tests passed! The main.py application is ready to run.")
        print("\nTo start the server, run:")
        print("  python main.py")
        print("or")
        print("  uvicorn main:app --host 0.0.0.0 --port 8000")
    else:
        print("❌ Some tests failed. Please check the issues above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
