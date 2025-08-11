#!/usr/bin/env python3
"""
NeuroBridge EDU Test Runner

Comprehensive test runner for the open source version of NeuroBridge EDU.
Provides different test suites and reporting options.

Usage:
    python run_tests.py [options]

Options:
    --suite <name>      Run specific test suite (unit, integration, performance, security, all)
    --coverage          Run tests with coverage reporting
    --verbose           Verbose output
    --report            Generate HTML test report
    --no-cleanup        Don't cleanup test files after run
    --markers           Show available test markers
    --parallel          Run tests in parallel (when possible)
"""

import subprocess
import sys
import argparse
from pathlib import Path
import os


class NeuroBridgeTestRunner:
    """Comprehensive test runner for NeuroBridge EDU"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent / "tests"
        
    def run_command(self, cmd, description=None):
        """Run command and handle output"""
        if description:
            print(f"\n{'='*60}")
            print(f"RUNNING: {description}")
            print(f"{'='*60}")
            print(f"Command: {' '.join(cmd)}")
            print()
        
        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=False, text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"Error running command: {e}")
            return False
    
    def check_dependencies(self):
        """Check that required test dependencies are installed"""
        required_packages = [
            "pytest",
            "pytest-asyncio", 
            "pytest-cov",
            "httpx",
            "pytest-xdist"  # For parallel testing
        ]
        
        missing = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing.append(package)
        
        if missing:
            print("Missing required test dependencies:")
            for pkg in missing:
                print(f"  - {pkg}")
            print("\nInstall with: pip install " + " ".join(missing))
            return False
        
        return True
    
    def run_unit_tests(self, coverage=False, verbose=False, parallel=False):
        """Run unit tests"""
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        
        if coverage:
            cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])
        
        if verbose:
            cmd.append("-v")
        
        if parallel:
            cmd.extend(["-n", "auto"])
        
        return self.run_command(cmd, "Unit Tests")
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests"""
        cmd = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
        
        if verbose:
            cmd.append("-v")
        
        return self.run_command(cmd, "Integration Tests")
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests"""
        cmd = ["python", "-m", "pytest", "tests/performance/", "-m", "performance"]
        
        if verbose:
            cmd.append("-v")
        
        return self.run_command(cmd, "Performance Tests")
    
    def run_security_tests(self, verbose=False):
        """Run security-focused tests"""
        cmd = ["python", "-m", "pytest", "-m", "security"]
        
        if verbose:
            cmd.append("-v")
        
        return self.run_command(cmd, "Security Tests")
    
    def run_all_tests(self, coverage=False, verbose=False, parallel=False):
        """Run all tests"""
        cmd = ["python", "-m", "pytest"]
        
        if coverage:
            cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term-missing"])
        
        if verbose:
            cmd.append("-v")
        
        if parallel:
            cmd.extend(["-n", "auto"])
        
        # Exclude performance tests from "all" by default (they're slow)
        cmd.extend(["-m", "not performance"])
        
        return self.run_command(cmd, "All Tests (excluding performance)")
    
    def run_quick_tests(self, verbose=False):
        """Run quick smoke tests"""
        cmd = ["python", "-m", "pytest", "-m", "not slow and not performance", "--tb=short"]
        
        if verbose:
            cmd.append("-v")
        
        return self.run_command(cmd, "Quick Tests")
    
    def show_markers(self):
        """Show available pytest markers"""
        cmd = ["python", "-m", "pytest", "--markers"]
        return self.run_command(cmd, "Available Test Markers")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        cmd = [
            "python", "-m", "pytest", 
            "--html=test-report.html", 
            "--self-contained-html",
            "--cov=.",
            "--cov-report=html",
            "-m", "not performance"  # Exclude performance tests from report
        ]
        
        return self.run_command(cmd, "Generating Test Report")
    
    def cleanup_test_files(self):
        """Clean up test artifacts"""
        cleanup_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/.pytest_cache",
            "**/htmlcov",
            "test-report.html",
            "**/test_*.db",
            "**/backup_*"
        ]
        
        print("\nCleaning up test artifacts...")
        for pattern in cleanup_patterns:
            for path in self.project_root.glob(pattern):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path, ignore_errors=True)
        
        print("Cleanup completed.")


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="NeuroBridge EDU Test Runner")
    
    parser.add_argument("--suite", choices=["unit", "integration", "performance", "security", "all", "quick"], 
                       default="quick", help="Test suite to run")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage reporting")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--report", action="store_true", help="Generate HTML test report")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't cleanup test files")
    parser.add_argument("--markers", action="store_true", help="Show available test markers")
    parser.add_argument("--parallel", "-n", action="store_true", help="Run tests in parallel")
    
    args = parser.parse_args()
    
    runner = NeuroBridgeTestRunner()
    
    # Show markers if requested
    if args.markers:
        runner.show_markers()
        return
    
    # Check dependencies
    if not runner.check_dependencies():
        sys.exit(1)
    
    print("NeuroBridge EDU Test Suite")
    print("=" * 50)
    print(f"Running: {args.suite} tests")
    print(f"Coverage: {'Yes' if args.coverage else 'No'}")
    print(f"Verbose: {'Yes' if args.verbose else 'No'}")
    print(f"Parallel: {'Yes' if args.parallel else 'No'}")
    print()
    
    # Run selected test suite
    success = True
    
    if args.suite == "unit":
        success = runner.run_unit_tests(args.coverage, args.verbose, args.parallel)
    elif args.suite == "integration":
        success = runner.run_integration_tests(args.verbose)
    elif args.suite == "performance":
        success = runner.run_performance_tests(args.verbose)
    elif args.suite == "security":
        success = runner.run_security_tests(args.verbose)
    elif args.suite == "all":
        success = runner.run_all_tests(args.coverage, args.verbose, args.parallel)
    elif args.suite == "quick":
        success = runner.run_quick_tests(args.verbose)
    
    # Generate report if requested
    if args.report:
        print("\nGenerating test report...")
        runner.generate_report()
        print("Test report generated: test-report.html")
    
    # Cleanup unless disabled
    if not args.no_cleanup:
        runner.cleanup_test_files()
    
    # Summary
    print("\n" + "="*60)
    if success:
        print("✅ All tests completed successfully!")
    else:
        print("❌ Some tests failed. Check output above for details.")
    print("="*60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()