#!/usr/bin/env python3
"""
Test script to verify project structure and imports are correct.
Run this from the VedioAutoMark directory.
"""
import sys
import os
from pathlib import Path

def test_project_structure():
    """Test if all required directories and files exist."""
    print("Testing project structure...")
    
    base_dir = Path(__file__).parent.parent
    
    required_dirs = [
        "src/video_agent/core",
        "src/video_agent/models", 
        "src/video_agent/utils",
        "data/input",
        "data/output",
        "scripts",
        "tests"
    ]
    
    required_files = [
        "src/video_agent/__init__.py",
        "src/video_agent/main.py",
        "src/video_agent/core/__init__.py",
        "src/video_agent/core/config.py",
        "src/video_agent/core/video_processor.py",
        "src/video_agent/core/ai_analyzer.py",
        "src/video_agent/models/__init__.py",
        "src/video_agent/models/schemas.py",
        "src/video_agent/utils/__init__.py",
        "src/video_agent/utils/mcp_client.py",
        "requirements.txt",
        "README.md",
        ".env.example"
    ]
    
    all_good = True
    
    print("\nChecking directories:")
    for dir_path in required_dirs:
        full_path = base_dir / dir_path
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {dir_path}")
        if not exists:
            all_good = False
            print(f"    ERROR: Directory does not exist: {full_path}")
    
    print("\nChecking files:")
    for file_path in required_files:
        full_path = base_dir / file_path
        exists = full_path.exists()
        status = "✓" if exists else "✗"
        print(f"  {status} {file_path}")
        if not exists:
            all_good = False
            print(f"    ERROR: File does not exist: {full_path}")
    
    return all_good

def test_imports():
    """Test if all imports work correctly."""
    print("\nTesting imports...")
    
    # Add parent directory to path (simulating how main.py does it)
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir.parent))
    
    try:
        print("  Testing: from src.video_agent.core.config import settings")
        from src.video_agent.core.config import settings
        print("    ✓ Config imported successfully")
        print(f"    - Input directory: {settings.input_video_directory}")
        print(f"    - Output directory: {settings.output_json_directory}")
        
        print("\n  Testing: from src.video_agent.core.video_processor import find_video_files")
        from src.video_agent.core.video_processor import find_video_files
        print("    ✓ Video processor imported successfully")
        
        print("\n  Testing: from src.video_agent.core.ai_analyzer import analyze_video_with_ai")
        from src.video_agent.core.ai_analyzer import analyze_video_with_ai
        print("    ✓ AI analyzer imported successfully")
        
        print("\n  Testing: from src.video_agent.models.schemas import VideoAnnotation")
        from src.video_agent.models.schemas import VideoAnnotation
        print("    ✓ Models imported successfully")
        
        print("\n  Testing: from src.video_agent.utils.mcp_client import MCPClient")
        from src.video_agent.utils.mcp_client import MCPClient
        print("    ✓ MCP client imported successfully")
        
        return True
    except Exception as e:
        print(f"    ✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config_paths():
    """Test if config paths are correct."""
    print("\nTesting configuration paths...")
    
    try:
        from src.video_agent.core.config import settings
        
        base_dir = Path(__file__).parent.parent
        
        input_dir = base_dir / settings.input_video_directory
        output_dir = base_dir / settings.output_json_directory
        
        print(f"  Base directory: {base_dir}")
        print(f"  Input directory: {input_dir}")
        print(f"  Output directory: {output_dir}")
        
        input_exists = input_dir.exists()
        output_exists = output_dir.exists()
        
        print(f"\n  Input directory exists: {'✓' if input_exists else '✗'}")
        if not input_exists:
            print(f"    ERROR: Input directory does not exist")
            print(f"    Creating input directory...")
            input_dir.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ Input directory created")
        
        print(f"  Output directory exists: {'✓' if output_exists else '✗'}")
        if not output_exists:
            print(f"    ERROR: Output directory does not exist")
            print(f"    Creating output directory...")
            output_dir.mkdir(parents=True, exist_ok=True)
            print(f"    ✓ Output directory created")
        
        return True
    except Exception as e:
        print(f"    ✗ Config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("VedioAutoMark Setup Verification")
    print("=" * 60)
    
    structure_ok = test_project_structure()
    imports_ok = test_imports()
    config_ok = test_config_paths()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Project Structure: {'✓ PASS' if structure_ok else '✗ FAIL'}")
    print(f"  Imports:          {'✓ PASS' if imports_ok else '✗ FAIL'}")
    print(f"  Configuration:     {'✓ PASS' if config_ok else '✗ FAIL'}")
    print("=" * 60)
    
    if structure_ok and imports_ok and config_ok:
        print("\n✓ All tests passed! Project is ready to use.")
        print("\nNext steps:")
        print("1. Create .env file: cp .env.example .env")
        print("2. Edit .env with your API keys")
        print("3. Run: python src/video_agent/main.py data/input")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
