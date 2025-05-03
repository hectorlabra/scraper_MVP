#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Environment Verification Script

This script verifies that the environment is correctly set up for the LeadScraper LATAM project.
It checks for required dependencies, configuration files, and environment variables.
"""

import os
import sys
import importlib
import subprocess
import pkg_resources
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.8 or later."""
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print(f"❌ Error: Python 3.8 or later is required, but you are using {sys.version}")
        return False
    
    print(f"✅ Python version: {sys.version.split()[0]} (OK)")
    return True

def check_required_packages():
    """Check if required packages are installed."""
    required_packages = [
        ('selenium', 'selenium'), 
        ('beautifulsoup4', 'bs4'), 
        ('pandas', 'pandas'), 
        ('gspread', 'gspread'), 
        ('google-auth', 'google.auth'), 
        ('instaloader', 'instaloader'), 
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            importlib.import_module(import_name)
            print(f"✅ Package '{package_name}' is installed (OK)")
        except ImportError:
            print(f"❌ Package '{package_name}' is not installed")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("To install missing packages, run:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists or create one from template."""
    env_file = Path('.env')
    template_file = Path('.env.template')
    
    if env_file.exists():
        print(f"✅ .env file exists (OK)")
        return True
    
    if not template_file.exists():
        print(f"❌ Neither .env nor .env.template file found")
        return False
    
    print(f"❌ .env file not found, but .env.template exists")
    print("Please create a .env file from the template:")
    print(f"cp {template_file} {env_file}")
    return False

def check_project_structure():
    """Check if the required project structure exists."""
    required_dirs = ['scrapers', 'processors', 'integrations', 'utils']
    required_files = ['main.py', 'requirements.txt']
    
    missing_items = []
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"❌ Directory '{dir_name}/' not found")
            missing_items.append(dir_name + '/')
        else:
            print(f"✅ Directory '{dir_name}/' exists (OK)")
    
    for file_name in required_files:
        file_path = Path(file_name)
        if not file_path.exists() or not file_path.is_file():
            print(f"❌ File '{file_name}' not found")
            missing_items.append(file_name)
        else:
            print(f"✅ File '{file_name}' exists (OK)")
    
    if missing_items:
        print(f"\nMissing items in project structure: {', '.join(missing_items)}")
        return False
    
    return True

def check_requirements_file():
    """Check if all packages in requirements.txt are installed."""
    requirements_path = Path('requirements.txt')
    
    if not requirements_path.exists():
        print("❌ requirements.txt file not found")
        return False
    
    try:
        # Read requirements.txt and check each package
        requirements = pkg_resources.parse_requirements(requirements_path.open())
        missing_packages = []
        
        for requirement in requirements:
            req_name = requirement.name
            try:
                pkg_resources.get_distribution(req_name)
                print(f"✅ Required package '{req_name}' is installed (OK)")
            except pkg_resources.DistributionNotFound:
                print(f"❌ Required package '{req_name}' is not installed")
                missing_packages.append(str(requirement))
        
        if missing_packages:
            print(f"\nSome packages from requirements.txt are missing.")
            print("To install all requirements, run:")
            print("pip install -r requirements.txt")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking requirements.txt: {str(e)}")
        return False

def main():
    """Main function to run all checks."""
    print("🔍 Checking LeadScraper LATAM environment...\n")
    
    checks = [
        ("Python version", check_python_version),
        ("Required packages", check_required_packages),
        ("Environment file", check_env_file),
        ("Project structure", check_project_structure),
        ("Requirements file", check_requirements_file)
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n--- Checking {name} ---")
        result = check_func()
        results.append((name, result))
        print()
    
    # Summary of results
    print("\n=== Summary ===")
    all_passed = True
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        if not result:
            all_passed = False
        print(f"{name}: {status}")
    
    print("\nOverall result:", "✅ All checks passed!" if all_passed else "❌ Some checks failed.")
    
    if not all_passed:
        print("\nPlease fix the issues above before continuing.")
        return 1
    
    print("\nYour environment is ready for LeadScraper LATAM development! 🚀")
    return 0

if __name__ == "__main__":
    sys.exit(main())
