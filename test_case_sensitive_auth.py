#!/usr/bin/env python3
"""
Test case-sensitive authentication to ensure only "InsuranceHead" works
"""

def test_case_sensitive_authentication():
    """Test that authentication is case-sensitive"""
    from main import authenticate_user
    
    # Should work - correct case
    assert authenticate_user("InsuranceHead", "insurance@123") == True
    print("✓ 'InsuranceHead' with correct password: PASSED")
    
    # Should fail - wrong case
    assert authenticate_user("insurancehead", "insurance@123") == False
    print("✓ 'insurancehead' (lowercase) with correct password: FAILED as expected")
    
    # Should fail - wrong case
    assert authenticate_user("INSURANCEHEAD", "insurance@123") == False
    print("✓ 'INSURANCEHEAD' (uppercase) with correct password: FAILED as expected")
    
    # Should fail - wrong case
    assert authenticate_user("InsuranceHEAD", "insurance@123") == False
    print("✓ 'InsuranceHEAD' (mixed case) with correct password: FAILED as expected")
    
    # Should fail - wrong password
    assert authenticate_user("InsuranceHead", "wrong_password") == False
    print("✓ 'InsuranceHead' with wrong password: FAILED as expected")
    
    # Should fail - both wrong
    assert authenticate_user("insurancehead", "wrong_password") == False
    print("✓ 'insurancehead' with wrong password: FAILED as expected")
    
    print("\n🎉 All case-sensitive authentication tests passed!")

def test_token_authentication():
    """Test that token authentication is also case-sensitive"""
    from main import verify_token
    import jwt
    from datetime import datetime, timedelta
    
    # Create a token with correct username
    correct_payload = {
        'name': 'InsuranceHead',
        'exp': datetime.utcnow() + timedelta(hours=1)  # 1 hour from now
    }
    correct_token = jwt.encode(correct_payload, 'your-secret-key', algorithm='HS256')
    
    # Create a token with incorrect case username
    incorrect_payload = {
        'name': 'insurancehead',  # lowercase
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    incorrect_token = jwt.encode(incorrect_payload, 'your-secret-key', algorithm='HS256')
    
    # Test correct token
    assert verify_token(correct_token) == True
    print("✓ Token with 'InsuranceHead': PASSED")
    
    # Test incorrect case token
    assert verify_token(incorrect_token) == False
    print("✓ Token with 'insurancehead': FAILED as expected")
    
    print("\n🎉 All token authentication tests passed!")

if __name__ == "__main__":
    print("Testing case-sensitive authentication...")
    print("=" * 50)
    
    try:
        test_case_sensitive_authentication()
        print("\n" + "=" * 50)
        test_token_authentication()
        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED: Authentication is now case-sensitive!")
        print("✅ Only 'InsuranceHead' will work, not 'insurancehead'")
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
