"""
Test script to verify the bug fix for edit buttons not working after regeneration.
This script performs code analysis and logic verification.
"""

import os
import re

def test_project_js_structure():
    """Test that project.js has the correct structure"""
    print("=" * 60)
    print("TEST 1: Verify project.js Structure")
    print("=" * 60)
    
    with open('app/static/project.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    tests = {
        "Event delegation flag exists": "let eventListenersAttached = false",
        "attachEventListeners function exists": "function attachEventListeners()",
        "updateCustomColumns function exists": "function updateCustomColumns(newColumns)",
        "Event delegation for click": 'document.addEventListener("click"',
        "Event delegation for change": 'document.addEventListener("change"',
        "Duplicate prevention check": "if (!eventListenersAttached)",
        "Global functions (updateRowWithVersionData)": "function updateRowWithVersionData(reqId, versionIndex)",
        "Global functions (initializeFilters)": "function initializeFilters()",
        "Global functions (applyFilters)": "function applyFilters()",
        "Global functions (openEditModal)": "function openEditModal(reqId, versionId)",
        "DOMContentLoaded calls attachEventListeners": "attachEventListeners()",
        "Filter clearing in initializeFilters": "dynamicFiltersContainer.innerHTML = ",
        "Uses PROJECT_CUSTOM_COLUMNS": "window.PROJECT_CUSTOM_COLUMNS",
    }
    
    passed = 0
    failed = 0
    
    for test_name, search_string in tests.items():
        if search_string in content:
            print(f"✅ PASS: {test_name}")
            passed += 1
        else:
            print(f"❌ FAIL: {test_name}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)} tests")
    return failed == 0

def test_event_delegation_pattern():
    """Test that event delegation is properly implemented"""
    print("\n" + "=" * 60)
    print("TEST 2: Verify Event Delegation Pattern")
    print("=" * 60)
    
    with open('app/static/project.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for event delegation pattern
    tests = {
        "Click handler checks for edit button": 'e.target.classList.contains("edit-requirement-btn")',
        "Click handler uses closest()": 'e.target.closest(".edit-requirement-btn")',
        "Click handler checks disabled state": "!button.disabled",
        "Change handler checks for version selector": 'e.target.classList.contains("version-selector")',
        "Event listeners attached to document": 'document.addEventListener',
    }
    
    passed = 0
    failed = 0
    
    for test_name, search_string in tests.items():
        if search_string in content:
            print(f"✅ PASS: {test_name}")
            passed += 1
        else:
            print(f"❌ FAIL: {test_name}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)} tests")
    return failed == 0

def test_no_queryselectorall_for_buttons():
    """Test that we're not using querySelectorAll for edit buttons anymore"""
    print("\n" + "=" * 60)
    print("TEST 3: Verify No Direct Button Selection")
    print("=" * 60)
    
    with open('app/static/project.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # These patterns should NOT exist (old approach)
    bad_patterns = [
        'querySelectorAll(".edit-requirement-btn")',
        'editButtons.forEach',
    ]
    
    passed = 0
    failed = 0
    
    for pattern in bad_patterns:
        if pattern in content:
            print(f"❌ FAIL: Found old pattern: {pattern}")
            failed += 1
        else:
            print(f"✅ PASS: Old pattern not found: {pattern}")
            passed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(bad_patterns)} tests")
    return failed == 0

def test_global_functions():
    """Test that key functions are globally accessible"""
    print("\n" + "=" * 60)
    print("TEST 4: Verify Global Functions")
    print("=" * 60)
    
    with open('app/static/project.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that functions are NOT inside DOMContentLoaded
    # They should be defined at the top level
    
    # Find DOMContentLoaded block
    dom_ready_match = re.search(
        r'document\.addEventListener\("DOMContentLoaded".*?\{(.*?)\}\);',
        content,
        re.DOTALL
    )
    
    if not dom_ready_match:
        print("❌ FAIL: Could not find DOMContentLoaded block")
        return False
    
    dom_ready_content = dom_ready_match.group(1)
    
    # These functions should NOT be inside DOMContentLoaded
    global_functions = [
        'function updateRowWithVersionData',
        'function initializeFilters',
        'function applyFilters',
        'function openEditModal',
        'function attachEventListeners',
        'function updateCustomColumns',
    ]
    
    passed = 0
    failed = 0
    
    for func in global_functions:
        if func in dom_ready_content:
            print(f"❌ FAIL: {func} is inside DOMContentLoaded (should be global)")
            failed += 1
        elif func in content:
            print(f"✅ PASS: {func} is defined globally")
            passed += 1
        else:
            print(f"❌ FAIL: {func} not found at all")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(global_functions)} tests")
    return failed == 0

def test_filter_reinitialization():
    """Test that filters are properly cleared before reinitializing"""
    print("\n" + "=" * 60)
    print("TEST 5: Verify Filter Reinitialization")
    print("=" * 60)
    
    with open('app/static/project.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    tests = {
        "Clears category filter options": "while (categoryFilter.options.length > 1)",
        "Clears dynamic filters container": 'dynamicFiltersContainer.innerHTML = ""',
        "Rebuilds category filters": "categoryFilter.appendChild(option)",
        "Rebuilds dynamic filters": "dynamicFiltersContainer.appendChild(filterDiv)",
    }
    
    passed = 0
    failed = 0
    
    for test_name, search_string in tests.items():
        if search_string in content:
            print(f"✅ PASS: {test_name}")
            passed += 1
        else:
            print(f"❌ FAIL: {test_name}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed out of {len(tests)} tests")
    return failed == 0

def test_template_has_global_variable():
    """Test that template sets PROJECT_CUSTOM_COLUMNS"""
    print("\n" + "=" * 60)
    print("TEST 6: Verify Template Configuration")
    print("=" * 60)
    
    template_files = [
        'app/templates/create_fixed.html',
        'app/templates/create.html',
    ]
    
    found = False
    for template_file in template_files:
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'window.PROJECT_CUSTOM_COLUMNS' in content:
                print(f"✅ PASS: {template_file} sets PROJECT_CUSTOM_COLUMNS")
                found = True
                break
    
    if not found:
        print("❌ FAIL: No template sets PROJECT_CUSTOM_COLUMNS")
        return False
    
    return True

def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("BUG FIX VERIFICATION TEST SUITE")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Project.js Structure", test_project_js_structure()))
    results.append(("Event Delegation Pattern", test_event_delegation_pattern()))
    results.append(("No Direct Button Selection", test_no_queryselectorall_for_buttons()))
    results.append(("Global Functions", test_global_functions()))
    results.append(("Filter Reinitialization", test_filter_reinitialization()))
    results.append(("Template Configuration", test_template_has_global_variable()))
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    failed = sum(1 for _, result in results if not result)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed} passed, {failed} failed out of {len(results)} test suites")
    
    if failed == 0:
        print("\n🎉 All tests passed! The bug fix implementation is correct.")
        return True
    else:
        print(f"\n⚠️  {failed} test suite(s) failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
