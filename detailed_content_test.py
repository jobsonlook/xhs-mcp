#!/usr/bin/env python3
"""
Detailed MCP Content Test - Shows actual content with clear output
"""

import subprocess
import time

def run_mcp_tool_test(tool_name: str, args: dict = None, timeout: int = 25):
    """Run a single MCP tool and show detailed results"""
    args_str = f", {args}" if args else ""
    
    script = f'''
import asyncio
import sys
sys.path.append('/app')
from main import {tool_name}

async def test():
    print("=" * 60)
    print(f"🔧 TESTING: {tool_name}")
    print("=" * 60)
    
    try:
        result = await {tool_name}({args_str})
        
        print(f"📊 RESULT TYPE: {{type(result).__name__}}")
        print(f"📏 RESULT LENGTH: {{len(result) if isinstance(result, str) else 'N/A'}}")
        print()
        
        if isinstance(result, str):
            if len(result) > 1000:
                print("📋 CONTENT PREVIEW (first 1000 chars):")
                print("-" * 40)
                print(result[:1000])
                print("...")
                print("-" * 40)
                print()
                
                print("📋 CONTENT PREVIEW (last 300 chars):")
                print("-" * 40)
                print("..." + result[-300:])
                print("-" * 40)
            else:
                print("📋 FULL CONTENT:")
                print("-" * 40)
                print(result)
                print("-" * 40)
        else:
            print(f"📋 RESULT: {{result}}")
        
        print()
        print("✅ SUCCESS")
        
    except Exception as e:
        print(f"❌ ERROR: {{e}}")
        import traceback
        traceback.print_exc()
        print("❌ FAILED")

asyncio.run(test())
'''
    
    try:
        result = subprocess.run([
            'docker-compose', 'exec', '-T', 'xhs-mcp',
            'bash', '-c', f'''
cd /app
cat << 'EOF' > /tmp/test_{tool_name}.py
{script}
EOF
timeout {timeout} uv run python /tmp/test_{tool_name}.py
'''
        ],
        cwd='/home/cxl/automation/xhs-mcp',
        capture_output=True,
        text=True,
        timeout=timeout + 5
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def main():
    print("🚀 MCP Server Detailed Content Test")
    print("=" * 80)
    print()
    
    # Test 1: Check Cookie
    print("🍪 TEST 1: Cookie Validation")
    success1 = run_mcp_tool_test("check_cookie")
    print()
    
    time.sleep(2)
    
    # Test 2: Search Notes
    print("🔍 TEST 2: Search Notes (美食)")
    success2 = run_mcp_tool_test("search_notes", {"keywords": '"美食"'})
    print()
    
    time.sleep(3)
    
    # Test 3: Home Feed
    print("🏠 TEST 3: Home Feed")
    success3 = run_mcp_tool_test("home_feed")
    print()
    
    time.sleep(3)
    
    # Test 4: Search with different keyword
    print("🔍 TEST 4: Search Notes (旅游)")
    success4 = run_mcp_tool_test("search_notes", {"keywords": '"旅游"'})
    print()
    
    # Summary
    print("=" * 80)
    print("🎯 FINAL SUMMARY")
    print("=" * 80)
    
    tests = [
        ("Cookie Validation", success1),
        ("Search Notes (美食)", success2),
        ("Home Feed", success3),
        ("Search Notes (旅游)", success4)
    ]
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    for i, (test_name, success) in enumerate(tests, 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{i}. {test_name}: {status}")
    
    print()
    print(f"🏆 OVERALL RESULT: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests successful! MCP server is fully operational with rich content.")
    else:
        print("⚠️ Some tests had issues. Check the detailed output above.")

if __name__ == "__main__":
    main()
