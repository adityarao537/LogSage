#!/usr/bin/env python3
"""
LogSage Dependency Validation Script

Validates that installed Python packages match requirements and checks for
known incompatible version combinations.

Usage:
    python scripts/validate_dependencies.py
    
Exit codes:
    0 - All validations passed
    1 - Validation failures detected
"""

import sys
import pkg_resources
from packaging import version
import subprocess


# Expected versions from requirements.txt
EXPECTED_VERSIONS = {
    'flask': '2.3.3',
    'flask-cors': '4.0.0',
    'gunicorn': '21.2.0',
    'requests': '2.31.0',
    'numpy': '1.24.3',
    'pandas': '2.0.3',
    'scikit-learn': '1.3.0',
    'elasticsearch': '7.10.1',
    'openai': '1.3.0',
}

# Known incompatible combinations
INCOMPATIBLE_COMBINATIONS = [
    {
        'packages': ['elasticsearch', 'numpy'],
        'condition': lambda versions: (
            versions['elasticsearch'].startswith('7.') and 
            version.parse(versions['numpy']) >= version.parse('2.0.0')
        ),
        'error': "Elasticsearch 7.x is incompatible with NumPy 2.0+. Use numpy<2.0",
        'fix': "pip install 'numpy<2.0'"
    },
    {
        'packages': ['pandas', 'numpy'],
        'condition': lambda versions: (
            version.parse(versions['pandas']) >= version.parse('2.2.0') and
            version.parse(versions['numpy']) < version.parse('1.23.0')
        ),
        'error': "Pandas 2.2+ requires NumPy 1.23+",
        'fix': "pip install 'numpy>=1.23' 'pandas>=2.2'"
    },
    {
        'packages': ['scikit-learn', 'numpy'],
        'condition': lambda versions: (
            version.parse(versions['scikit-learn']) >= version.parse('1.4.0') and
            version.parse(versions['numpy']) < version.parse('1.23.0')
        ),
        'error': "Scikit-learn 1.4+ requires NumPy 1.23+",
        'fix': "pip install 'numpy>=1.23' 'scikit-learn>=1.4'"
    },
]


def get_installed_version(package_name):
    """Get installed version of a package."""
    try:
        return pkg_resources.get_distribution(package_name).version
    except pkg_resources.DistributionNotFound:
        return None


def check_python_version():
    """Validate Python version."""
    print("=" * 70)
    print("Python Version Check")
    print("=" * 70)
    
    current = sys.version_info
    print(f"Current Python: {current.major}.{current.minor}.{current.micro}")
    
    if current.major < 3 or (current.major == 3 and current.minor < 9):
        print("❌ FAIL: Python 3.9+ required")
        return False
    
    if current.minor >= 12:
        print("⚠️  WARNING: Python 3.12+ may have compatibility issues with some packages")
    
    print("✅ PASS: Python version is compatible\n")
    return True


def check_package_versions():
    """Check if installed packages match expected versions."""
    print("=" * 70)
    print("Package Version Check")
    print("=" * 70)
    
    all_match = True
    installed_versions = {}
    
    for package, expected in EXPECTED_VERSIONS.items():
        installed = get_installed_version(package)
        installed_versions[package] = installed
        
        if installed is None:
            print(f"❌ {package:20s} - NOT INSTALLED (expected: {expected})")
            all_match = False
        elif installed == expected:
            print(f"✅ {package:20s} - {installed:10s} (matches)")
        else:
            print(f"⚠️  {package:20s} - {installed:10s} (expected: {expected})")
            all_match = False
    
    print()
    return all_match, installed_versions


def check_incompatibilities(installed_versions):
    """Check for known incompatible version combinations."""
    print("=" * 70)
    print("Compatibility Check")
    print("=" * 70)
    
    issues_found = False
    
    for incompatibility in INCOMPATIBLE_COMBINATIONS:
        packages = incompatibility['packages']
        
        # Check if all packages in this rule are installed
        versions = {}
        all_installed = True
        for pkg in packages:
            ver = installed_versions.get(pkg)
            if ver is None:
                all_installed = False
                break
            versions[pkg] = ver
        
        if not all_installed:
            continue
        
        # Check if the incompatibility condition is met
        try:
            if incompatibility['condition'](versions):
                print(f"❌ INCOMPATIBILITY DETECTED:")
                print(f"   Packages: {', '.join(packages)}")
                print(f"   Versions: {', '.join([f'{p}=={versions[p]}' for p in packages])}")
                print(f"   Issue: {incompatibility['error']}")
                print(f"   Fix: {incompatibility['fix']}")
                print()
                issues_found = True
        except Exception as e:
            print(f"⚠️  Could not validate {packages}: {e}")
    
    if not issues_found:
        print("✅ PASS: No incompatibilities detected\n")
    
    return not issues_found


def test_imports():
    """Test that all critical imports work."""
    print("=" * 70)
    print("Import Test")
    print("=" * 70)
    
    imports_to_test = [
        ('elasticsearch', 'from elasticsearch import Elasticsearch, helpers'),
        ('numpy', 'import numpy as np'),
        ('pandas', 'import pandas as pd'),
        ('sklearn', 'from sklearn.ensemble import IsolationForest'),
        ('flask', 'from flask import Flask'),
        ('openai', 'from openai import OpenAI'),
    ]
    
    all_passed = True
    for name, import_stmt in imports_to_test:
        try:
            exec(import_stmt)
            print(f"✅ {name:20s} - Import successful")
        except Exception as e:
            print(f"❌ {name:20s} - Import failed: {e}")
            all_passed = False
    
    print()
    return all_passed


def check_elasticsearch_compatibility():
    """Check Elasticsearch client compatibility."""
    print("=" * 70)
    print("Elasticsearch Compatibility Check")
    print("=" * 70)
    
    try:
        import elasticsearch
        es_version = pkg_resources.get_distribution('elasticsearch').version
        
        print(f"Elasticsearch client version: {es_version}")
        
        major_version = int(es_version.split('.')[0])
        
        if major_version == 7:
            print("✅ Client is version 7.x (compatible with ES 7.8.0 server)")
            print("⚠️  Ensure server is ES 7.x and numpy<2.0")
        elif major_version == 6:
            print("⚠️  Client is version 6.x (compatible with ES 6.x servers)")
            print("   If connecting to ES 7.x, upgrade to elasticsearch==7.10.1")
        elif major_version == 8:
            print("⚠️  Client is version 8.x (compatible with ES 8.x servers)")
            print("   If connecting to ES 7.x, downgrade to elasticsearch==7.10.1")
        else:
            print(f"❌ Unknown Elasticsearch version: {es_version}")
            return False
        
        print()
        return True
    except Exception as e:
        print(f"❌ Could not check Elasticsearch: {e}\n")
        return False


def print_summary(results):
    """Print validation summary."""
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    passed = sum(results.values())
    total = len(results)
    
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check}")
    
    print()
    print(f"Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All validations passed! Dependencies are correctly configured.\n")
        return True
    else:
        print("\n⚠️  Some validations failed. Review errors above and fix before deploying.\n")
        print("See DEPENDENCY_MANAGEMENT.md for troubleshooting guidance.")
        return False


def main():
    """Run all validation checks."""
    print("\n" + "="*70)
    print(" LogSage Dependency Validation")
    print("="*70 + "\n")
    
    results = {}
    
    # Run all checks
    results['Python Version'] = check_python_version()
    
    versions_match, installed_versions = check_package_versions()
    results['Package Versions'] = versions_match
    
    results['Compatibility'] = check_incompatibilities(installed_versions)
    results['Imports'] = test_imports()
    results['Elasticsearch'] = check_elasticsearch_compatibility()
    
    # Print summary
    all_passed = print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
