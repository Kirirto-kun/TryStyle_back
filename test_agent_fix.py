#!/usr/bin/env python3
"""
Simple test script to verify the agent system is working correctly.
Run this to test the outfit agent functionality.
"""

import os
import asyncio
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from src.database import SessionLocal
from src.agent.sub_agents.outfit_agent import recommend_outfit, WardrobeManager

async def test_wardrobe_access():
    """Test wardrobe access for a specific user."""
    print("🧥 Testing wardrobe access...")
    
    # Test user_id 3 (from the error logs)
    user_id = 3
    
    try:
        # Test direct wardrobe access
        print(f"Testing wardrobe access for user_id: {user_id}")
        wardrobe_manager = WardrobeManager(user_id)
        wardrobe_result = wardrobe_manager.get_user_wardrobe()
        print(f"Wardrobe result: {wardrobe_result}")
        
        # Test the full outfit recommendation
        print(f"\nTesting outfit recommendation for user_id: {user_id}")
        outfit_result = await recommend_outfit(user_id, "What should I wear today?")
        print(f"Outfit result: {outfit_result}")
        print(f"Outfit type: {type(outfit_result)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in wardrobe test: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

async def test_environment():
    """Test environment configuration."""
    print("🔧 Testing environment configuration...")
    
    required_vars = [
        "AZURE_API_KEY",
        "AZURE_API_BASE", 
        "AZURE_DEPLOYMENT_NAME",
        "AZURE_API_VERSION"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

async def test_database():
    """Test database connection."""
    print("🗄️ Testing database connection...")
    
    try:
        db = SessionLocal()
        # Try a simple query
        result = db.execute("SELECT 1")
        db.close()
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🔄 Starting agent system tests...\n")
    
    tests = [
        ("Environment", test_environment),
        ("Database", test_database), 
        ("Wardrobe", test_wardrobe_access)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} test...")
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
        print(f"{'='*50}")
    
    print(f"\n📊 Test Results:")
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    if all(results.values()):
        print("\n🎉 All tests passed! The agent system should be working correctly.")
    else:
        print("\n⚠️ Some tests failed. Please check the issues above.")

if __name__ == "__main__":
    asyncio.run(main()) 