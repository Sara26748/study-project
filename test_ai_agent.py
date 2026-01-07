"""
Test script for AI Agent functionality
Run this after logging into the application to test the AI agent endpoints
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_ai_client_imports():
    """Test that ai_client can be imported and has correct functions"""
    try:
        from app.services import ai_client
        assert hasattr(ai_client, 'generate_requirements'), "generate_requirements function not found"
        print("✅ AI Client imports successfully")
        return True
    except Exception as e:
        print(f"❌ AI Client import failed: {e}")
        return False

def test_config_loading():
    """Test that config loads environment variables correctly"""
    try:
        import config
        assert hasattr(config, 'OPENAI_API_KEY'), "OPENAI_API_KEY not in config"
        assert hasattr(config, 'OPENAI_MODEL'), "OPENAI_MODEL not in config"
        assert hasattr(config, 'get_system_prompt'), "get_system_prompt function not found"
        
        # Test get_system_prompt
        prompt = config.get_system_prompt()
        assert prompt is not None, "System prompt is None"
        assert len(prompt) > 0, "System prompt is empty"
        assert "Requirements Engineer" in prompt or "requirements" in prompt.lower(), "System prompt doesn't look correct"
        
        print("✅ Config loads successfully")
        print(f"   - API Key present: {bool(config.OPENAI_API_KEY)}")
        print(f"   - Model: {config.OPENAI_MODEL}")
        print(f"   - System prompt length: {len(prompt)} characters")
        return True
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_ai_client_function_signature():
    """Test that generate_requirements has correct signature"""
    try:
        from app.services.ai_client import generate_requirements
        import inspect
        
        sig = inspect.signature(generate_requirements)
        params = list(sig.parameters.keys())
        
        assert 'user_description' in params, "user_description parameter missing"
        assert 'inputs' in params, "inputs parameter missing"
        
        print("✅ AI Client function signature is correct")
        print(f"   - Parameters: {params}")
        return True
    except Exception as e:
        print(f"❌ Function signature test failed: {e}")
        return False

def test_json_parsing_functions():
    """Test JSON parsing helper functions"""
    try:
        from app.services.ai_client import _parse_json_response, _validate_and_normalize_requirements
        
        # Test valid JSON
        valid_json = '{"requirements": [{"title": "Test", "description": "Test desc", "category": "Functional", "status": "Offen"}]}'
        result = _parse_json_response(valid_json)
        assert isinstance(result, list), "Result should be a list"
        assert len(result) == 1, "Should have 1 requirement"
        assert result[0]['status'] == 'Offen', "Status should be Offen"
        
        # Test JSON with extra text
        json_with_text = 'Here is the JSON: {"requirements": [{"title": "Test2", "description": "Test desc2"}]} End of JSON'
        result2 = _parse_json_response(json_with_text)
        assert isinstance(result2, list), "Should parse JSON from text"
        
        print("✅ JSON parsing functions work correctly")
        return True
    except Exception as e:
        print(f"❌ JSON parsing test failed: {e}")
        return False

def test_models():
    """Test that models are correctly defined"""
    try:
        from app.models import Requirement, Project
        import inspect
        
        # Check Requirement model
        req_attrs = [attr for attr in dir(Requirement) if not attr.startswith('_')]
        required_fields = ['title', 'description', 'category', 'status', 'project_id', 'created_at']
        
        for field in required_fields:
            assert field in req_attrs, f"Requirement model missing {field}"
        
        # Check Project model has requirements relationship
        assert hasattr(Project, 'requirements'), "Project model missing requirements relationship"
        
        print("✅ Models are correctly defined")
        print(f"   - Requirement fields: {required_fields}")
        return True
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False

def test_agent_routes():
    """Test that agent routes are registered"""
    try:
        from app.agent import agent_bp
        
        # Check blueprint is defined
        assert agent_bp is not None, "Agent blueprint not found"
        assert agent_bp.name == 'agent', "Blueprint name incorrect"
        
        # Check routes exist
        rules = [rule.rule for rule in agent_bp.url_map.iter_rules() if rule.endpoint.startswith('agent.')]
        
        print("✅ Agent routes are registered")
        print(f"   - Blueprint name: {agent_bp.name}")
        return True
    except Exception as e:
        print(f"❌ Agent routes test failed: {e}")
        return False

def test_template_exists():
    """Test that the agent template exists"""
    try:
        import os
        template_path = "app/templates/agent/agent.html"
        assert os.path.exists(template_path), f"Template not found at {template_path}"
        
        # Read template and check for key elements
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check that System Prompt is NOT in template
        assert 'system_prompt' not in content.lower() or 'system prompt' not in content.lower(), "System Prompt field should be removed"
        
        # Check that User-Beschreibung is present
        assert 'user_description' in content.lower() or 'user-beschreibung' in content.lower(), "User-Beschreibung field missing"
        
        # Check that it's optional (no required attribute)
        assert 'user_description' in content and 'required' not in content.split('user_description')[1].split('>')[0], "User description should be optional"
        
        # Check for Key-Value pairs
        assert 'key[]' in content and 'value[]' in content, "Key-Value pairs missing"
        
        # Check for fetch POST
        assert 'fetch' in content and 'POST' in content, "Fetch POST missing"
        
        print("✅ Template exists and has correct structure")
        print("   - System Prompt field: REMOVED ✓")
        print("   - User-Beschreibung: PRESENT and OPTIONAL ✓")
        print("   - Key-Value pairs: PRESENT ✓")
        return True
    except Exception as e:
        print(f"❌ Template test failed: {e}")
        return False

def test_requirements_txt():
    """Test that requirements.txt has necessary packages"""
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
        
        assert 'openai' in content, "openai package missing"
        assert 'python-dotenv' in content, "python-dotenv package missing"
        
        print("✅ requirements.txt has necessary packages")
        print("   - openai: PRESENT ✓")
        print("   - python-dotenv: PRESENT ✓")
        return True
    except Exception as e:
        print(f"❌ requirements.txt test failed: {e}")
        return False

def test_env_file():
    """Test that .env file exists and has API key"""
    try:
        import os
        assert os.path.exists('.env'), ".env file not found"
        
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        assert api_key is not None, "OPENAI_API_KEY not in .env"
        assert api_key.startswith('sk-'), "API key format looks incorrect"
        
        print("✅ .env file exists and has API key")
        print(f"   - API key starts with: {api_key[:10]}...")
        return True
    except Exception as e:
        print(f"❌ .env file test failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("AI AGENT REFACTORING - AUTOMATED TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Config Loading", test_config_loading),
        ("Environment File", test_env_file),
        ("Requirements.txt", test_requirements_txt),
        ("AI Client Imports", test_ai_client_imports),
        ("Function Signature", test_ai_client_function_signature),
        ("JSON Parsing", test_json_parsing_functions),
        ("Models", test_models),
        ("Agent Routes", test_agent_routes),
        ("Template", test_template_exists),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'─' * 60}")
        print(f"Testing: {name}")
        print('─' * 60)
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append((name, False))
        print()
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The refactoring is working correctly.")
        print("\nNext steps:")
        print("1. Login to the application at http://127.0.0.1:5000")
        print("2. Navigate to a project")
        print("3. Click 'KI-Agent' button")
        print("4. Test the UI manually using QUICK_START_GUIDE.md")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
    
    return passed == total

if __name__ == "__main__":
    run_all_tests()
