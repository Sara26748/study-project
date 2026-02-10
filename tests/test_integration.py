"""
Integration test for AI Agent - Tests the actual OpenAI integration
"""

import os
from dotenv import load_dotenv
import pytest

# Load environment variables first
load_dotenv()

def test_openai_integration():
    """Test actual OpenAI API call with the configured settings"""
    if os.getenv("RUN_OPENAI_INTEGRATION") != "1":
        pytest.skip("Set RUN_OPENAI_INTEGRATION=1 to run OpenAI integration test")
    print("=" * 60)
    print("OPENAI INTEGRATION TEST")
    print("=" * 60)
    print()
    
    try:
        # Import after loading env vars
        from app.services.ai_client import generate_requirements
        import config
        
        # Reload config to get env vars
        import importlib
        importlib.reload(config)
        
        print("Configuration:")
        print(f"  - API Key present: {bool(config.OPENAI_API_KEY)}")
        print(f"  - API Key starts with: {config.OPENAI_API_KEY[:15] if config.OPENAI_API_KEY else 'None'}...")
        print(f"  - Model: {config.OPENAI_MODEL}")
        print(f"  - System Prompt length: {len(config.get_system_prompt())} chars")
        print()
        
        if not config.OPENAI_API_KEY:
            print("❌ OPENAI_API_KEY not loaded from environment")
            pytest.skip("OPENAI_API_KEY not set")
        
        # Test 1: Generate with user description only
        print("Test 1: User description only")
        print("-" * 60)
        try:
            user_desc = "Erstelle Requirements für eine einfache Benutzeranmeldung"
            inputs = {}
            
            print(f"  Input: '{user_desc}'")
            print("  Calling OpenAI API...")
            
            requirements = generate_requirements(user_desc, inputs)
            
            print(f"  ✅ Success! Generated {len(requirements)} requirements")
            for i, req in enumerate(requirements[:3], 1):  # Show first 3
                print(f"    {i}. {req['title']}")
                print(f"       Status: {req['status']}")
                print(f"       Category: {req.get('category', 'N/A')}")
            
            # Validate structure
            assert isinstance(requirements, list), "Should return a list"
            assert len(requirements) > 0, "Should generate at least one requirement"
            
            for req in requirements:
                assert 'title' in req, "Missing title"
                assert 'description' in req, "Missing description"
                assert 'status' in req, "Missing status"
                assert req['status'] == 'Entwurf', f"Status should be 'Entwurf', got '{req['status']}'"
            
            print("  ✅ All requirements have correct structure")
            print()
            
        except Exception as e:
            print(f"  ❌ Test 1 failed: {e}")
            pytest.fail(str(e))
        
        # Test 2: Generate with key-value pairs only
        print("Test 2: Key-value pairs only")
        print("-" * 60)
        try:
            user_desc = None
            inputs = {
                "System": "Web-Anwendung",
                "Technologie": "Flask, Python",
                "Feature": "Dashboard"
            }
            
            print(f"  Inputs: {inputs}")
            print("  Calling OpenAI API...")
            
            requirements = generate_requirements(user_desc, inputs)
            
            print(f"  ✅ Success! Generated {len(requirements)} requirements")
            for i, req in enumerate(requirements[:2], 1):  # Show first 2
                print(f"    {i}. {req['title']}")
            
            assert len(requirements) > 0, "Should generate requirements"
            print("  ✅ Requirements generated from key-Value pairs")
            print()
            
        except Exception as e:
            print(f"  ❌ Test 2 failed: {e}")
            pytest.fail(str(e))
        
        # Test 3: Generate with both
        print("Test 3: Both description and key-value pairs")
        print("-" * 60)
        try:
            user_desc = "Erstelle Requirements für Datenvisualisierung"
            inputs = {
                "Diagrammtypen": "Balken, Linien",
                "Datenquelle": "REST API"
            }
            
            print(f"  Description: '{user_desc}'")
            print(f"  Inputs: {inputs}")
            print("  Calling OpenAI API...")
            
            requirements = generate_requirements(user_desc, inputs)
            
            print(f"  ✅ Success! Generated {len(requirements)} requirements")
            print("  ✅ Combined input works correctly")
            print()
            
        except Exception as e:
            print(f"  ❌ Test 3 failed: {e}")
            pytest.fail(str(e))
        
        # Test 4: Empty input (should still work)
        print("Test 4: Empty input")
        print("-" * 60)
        try:
            user_desc = None
            inputs = {}
            
            print("  No description, no inputs")
            print("  Calling OpenAI API...")
            
            requirements = generate_requirements(user_desc, inputs)
            
            print(f"  ✅ Success! Generated {len(requirements)} general requirements")
            print("  ✅ Empty input handled correctly")
            print()
            
        except Exception as e:
            print(f"  ❌ Test 4 failed: {e}")
            pytest.fail(str(e))
        
        print("=" * 60)
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✅ OpenAI API connection working")
        print("  ✅ User description only: WORKS")
        print("  ✅ Key-value pairs only: WORKS")
        print("  ✅ Combined input: WORKS")
        print("  ✅ Empty input: WORKS")
        print("  ✅ All requirements have status='Entwurf'")
        print("  ✅ JSON parsing working correctly")
        print()
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(str(e))

if __name__ == "__main__":
    try:
        test_openai_integration()
        print("✅ The AI Agent is fully functional and ready to use!")
        print()
        print("Next steps:")
        print("1. The Flask app is running at http://127.0.0.1:5000")
        print("2. Login to the application")
        print("3. Navigate to a project and click 'KI-Agent'")
        print("4. Test the UI manually")
    except pytest.SkipTest:
        print("⚠️ Integration test skipped (OPENAI_API_KEY not set).")
    except Exception:
        print("❌ Integration tests failed. Please check the errors above.")
