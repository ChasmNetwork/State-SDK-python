#!/bin/bash
# State of Mika SDK Test Runner
# 
# This script runs the test suite for the State of Mika SDK

# Set to exit on error
set -e

echo "State of Mika SDK Test Runner"
echo "============================"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Ensure we're in the project root
if [ -d "state_of_mika" ]; then
    echo "Running tests from project root..."
else
    echo "Error: Please run this script from the project root directory."
    exit 1
fi

# Make sure the tests directory exists
if [ ! -d "tests" ]; then
    echo "Creating tests directory..."
    mkdir -p tests
fi

# Make the test script executable
chmod +x tests/run_tests.py

# Run the tests
echo "Running test suite..."
python tests/run_tests.py

# Exit with success
echo "Test runner completed." 