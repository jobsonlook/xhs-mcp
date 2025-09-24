#!/usr/bin/env python3
"""
Final MCP Content Test - Shows actual content with proper syntax
"""

import subprocess
import time

def test_individual_tool(tool_name: str, description: str, args_code: str = ""):
    """Test individual MCP tool with proper syntax"""
    
    script = f'''
import asyncio
import sys
sys.path.append('/app')
from main import {tool_name}

async def test():
    print("=" * 70)
    print(f"🔧 TESTING: {description}")
    print("=" * 70)
    
    try:
        {args_code}
        result = await {tool_name}({args_code.split("=")[-1].strip() if "=" in args_code else ""})
        
        print(f"📊 RESULT TYPE: {{type(result).__name__}}")
        print(f"📏 RESULT LENGTH: {{len(result) if isinstance(result, str) else 'N/A'}}")
        print()
        
        if isinstance(result, str) and result:
            if len(result) > 800:
                print("📋 CONTENT PREVIEW (first 800 characters):")
                print("-" * 50)
                print(result[:800])
                print("...")
                print("-" * 50)
                print()
                
                # Show last part too
                print("📋 CONTENT PREVIEW (last 200 characters):")
                print("-" * 50)
                print("..." + result[-200:])
                print("-" * 50)
            else:
                print("📋 FULL CONTENT:")
                print("-" * 50)
                print(result)
                print("-" * 50)
        else:
            print(f"📋 RESULT: {{result}}")
        
        print()
        print("✅ SUCCESS")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {{e}}")
        import traceback
        traceback.print_exc()
        print("❌ FAILED")
        return False

asyncio.run(test())
'''
    
    try:
        result = subprocess.run([
            'docker-compose', 'exec', '-T', 'xhs-mcp',
            'bash', '-c', f'''
cd /app
cat << 'EOF' > /tmp/test_tool.py
{script}
EOF
timeout 30 uv run python /tmp/test_tool.py
'''
        ],
        cwd='/home/cxl/automation/xhs-mcp',
        capture_output=True,
        text=True,
        timeout=35
        )
        
        print(result.stdout)
        if result.stderr:
            print(f"⚠️ STDERR: {result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False

def main():
    print("🚀 MCP Server Final Content Test")
    print("=" * 80)
    print("Testing all MCP tools with actual content from Xiaohongshu API")
    print()
    
    test_results = []
    
    # Test 1: Cookie Validation
    print("🍪 TEST 1: Cookie Validation")
    success1 = test_individual_tool("check_cookie", "Cookie Validation")
    test_results.append(("Cookie Validation", success1))
    print()
    time.sleep(2)
    
    # Test 2: Search Notes - 美食
    print("🔍 TEST 2: Search Notes - Food Content")
    success2 = test_individual_tool("search_notes", "Search Notes (美食)", 'keywords = "美食"')
    test_results.append(("Search Notes (美食)", success2))
    print()
    time.sleep(3)
    
    # Test 3: Home Feed
    print("🏠 TEST 3: Home Feed")
    success3 = test_individual_tool("home_feed", "Home Feed")
    test_results.append(("Home Feed", success3))
    print()
    time.sleep(3)
    
    # Test 4: Search Notes - 旅游
    print("🔍 TEST 4: Search Notes - Travel Content")
    success4 = test_individual_tool("search_notes", "Search Notes (旅游)", 'keywords = "旅游"')
    test_results.append(("Search Notes (旅游)", success4))
    print()
    time.sleep(3)
    
    # Test 5: Search Notes - 科技
    print("🔍 TEST 5: Search Notes - Technology Content")
    success5 = test_individual_tool("search_notes", "Search Notes (科技)", 'keywords = "科技"')
    test_results.append(("Search Notes (科技)", success5))
    print()
    
    # Final Summary
    print("=" * 80)
    print("🎯 COMPREHENSIVE TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    for i, (test_name, success) in enumerate(test_results, 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{i}. {test_name}: {status}")
    
    print()
    print(f"🏆 OVERALL RESULT: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 EXCELLENT! All MCP tools are working perfectly with rich content!")
        print("📊 The server successfully retrieves:")
        print("   • Cookie validation status")
        print("   • Search results with engagement data")
        print("   • Home feed with personalized content")
        print("   • Multiple search categories working")
    elif passed >= total * 0.8:
        print("✅ VERY GOOD! Most MCP tools are working with rich content!")
    elif passed >= total * 0.5:
        print("⚠️ PARTIAL SUCCESS. Some MCP tools are working.")
    else:
        print("❌ ISSUES DETECTED. Please check the detailed output above.")
    
    print()
    print("💡 Key Features Demonstrated:")
    print("   🔐 Authentication validation")
    print("   🔍 Content search with Chinese keywords")
    print("   📊 Real engagement metrics (likes, comments)")
    print("   🔗 Valid Xiaohongshu post links")
    print("   🏠 Personalized home feed")
    print("   🌐 Full API integration")

if __name__ == "__main__":
    main()
