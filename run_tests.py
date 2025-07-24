#!/usr/bin/env python3
"""Test runner script for SSH Tunnel Manager."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_tests() -> int:
    """Run the test suite with pytest."""
    project_root = Path(__file__).parent

    # Change to project directory
    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(project_root)

        # Run pytest with various options
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--strict-markers",
            "--strict-config",
        ]

        print("Running SSH Tunnel Manager tests...")
        print(f"Command: {' '.join(cmd)}")
        print("-" * 60)

        result = subprocess.run(cmd, check=False)
        return result.returncode

    finally:
        os.chdir(original_cwd)


def run_coverage() -> int:
    """Run tests with coverage reporting."""
    project_root = Path(__file__).parent

    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(project_root)

        # Check if coverage is available
        try:
            subprocess.run(
                [sys.executable, "-m", "coverage", "--version"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            print("Coverage not available. Install with: pip install coverage")
            return 1

        # Run tests with coverage
        cmd = [
            sys.executable,
            "-m",
            "coverage",
            "run",
            "-m",
            "pytest",
            "tests/",
        ]

        print("Running tests with coverage...")
        print(f"Command: {' '.join(cmd)}")
        print("-" * 60)

        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            # Show coverage report
            print("\nCoverage Report:")
            print("-" * 60)
            subprocess.run([sys.executable, "-m", "coverage", "report"], check=False)

            # Generate HTML report
            subprocess.run(
                [sys.executable, "-m", "coverage", "html", "--directory", "htmlcov"],
                check=False,
            )
            print("\nHTML coverage report generated in htmlcov/")

        return result.returncode

    finally:
        os.chdir(original_cwd)


def main() -> int:
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--coverage", "-c"):
            return run_coverage()
        if sys.argv[1] in ("--help", "-h"):
            print("Usage: python run_tests.py [--coverage|-c] [--help|-h]")
            print()
            print("Options:")
            print("  --coverage, -c    Run tests with coverage reporting")
            print("  --help, -h        Show this help message")
            return 0
        print(f"Unknown option: {sys.argv[1]}")
        print("Use --help for available options")
        return 1

    return run_tests()


if __name__ == "__main__":
    sys.exit(main())
