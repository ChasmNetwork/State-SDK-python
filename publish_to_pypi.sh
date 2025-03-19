#!/bin/bash
# Script to build and publish the State of Mika SDK to PyPI

# Set to exit on error
set -e

echo "Cleaning up previous builds..."
rm -rf build/ dist/ *.egg-info/

echo "Ensuring build tools are up to date..."
pip install --upgrade build twine

echo "Building the package..."
python -m build

echo "Package contents for verification:"
twine check dist/*

echo "------------------------------------"
echo "Ready to upload to PyPI!"
echo "You'll need your PyPI username and password."
echo "This version standardizes on using ANTHROPIC_API_KEY environment variable."
echo "------------------------------------"
echo "Would you like to upload to TestPyPI first for testing? (y/n)"
read test_first

if [ "$test_first" == "y" ]; then
    echo "Uploading to TestPyPI..."
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    
    echo "If successful, you can install from TestPyPI with:"
    echo "pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple state-of-mika==$(python -c "import state_of_mika; print(state_of_mika.__version__)")"
    
    echo "------------------------------------"
    echo "Would you like to proceed with uploading to the real PyPI? (y/n)"
    read proceed
    
    if [ "$proceed" != "y" ]; then
        echo "Upload to real PyPI cancelled."
        exit 0
    fi
fi

echo "Uploading to PyPI..."
twine upload dist/*

echo "------------------------------------"
echo "Package uploaded successfully!"
echo "Users can now install with: pip install state-of-mika==$(python -c "import state_of_mika; print(state_of_mika.__version__)")"
echo "IMPORTANT: Make sure to set the ANTHROPIC_API_KEY environment variable."
echo "------------------------------------" 