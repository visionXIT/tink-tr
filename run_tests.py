#!/usr/bin/env python3
"""
Test runner for the profit calculator system
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        import pytest
        # Run the tests
        exit_code = pytest.main([
            "test_profit_calculator.py",
            "-v",
            "--tb=short"
        ])
        sys.exit(exit_code)
    except ImportError:
        print("pytest not installed. Installing...")
        import subprocess
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pytest"])
        import pytest
        exit_code = pytest.main([
            "test_profit_calculator.py",
            "-v",
            "--tb=short"
        ])
        sys.exit(exit_code)
