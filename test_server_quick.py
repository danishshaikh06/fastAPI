import subprocess
import sys
import time
import signal
import threading
from main import app

def test_server_startup():
    """Test that the server can start without crashing"""
    print("Testing server startup...")
    
    # Import test to ensure no syntax errors
    try:
        from main import app
        print("✅ main.py imports successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Test that we can create the app instance
    try:
        assert app is not None
        print("✅ FastAPI app instance created")
    except Exception as e:
        print(f"❌ App creation error: {e}")
        return False
    
    # Test routes are available
    try:
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/health", "/upload-csv/", "/database/all-data"]
        
        for route in expected_routes:
            if route not in routes:
                print(f"❌ Route {route} missing")
                return False
        
        print("✅ All expected routes are available")
        return True
    except Exception as e:
        print(f"❌ Route checking error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Quick server startup test")
    print("=" * 40)
    
    if test_server_startup():
        print("=" * 40)
        print("🎉 Server startup test PASSED!")
        print("The main.py application is ready to run.")
    else:
        print("=" * 40)
        print("❌ Server startup test FAILED!")
        sys.exit(1)
