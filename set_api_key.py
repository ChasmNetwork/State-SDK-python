#!/usr/bin/env python3
import os
import sys
import subprocess

if len(sys.argv) < 2:
    print("Please provide your AccuWeather API key as an argument")
    print("Example: python set_api_key.py YOUR_ACTUAL_API_KEY")
    sys.exit(1)

api_key = sys.argv[1]
print(f"Setting API key (first 4 chars): {api_key[:4]}{'*' * (len(api_key) - 4)}")

# Create a command that will set the env var and run the test
cmd = f'ACCUWEATHER_API_KEY="{api_key}" python test_accuweather.py'
print(f"Running: {cmd}")

# Execute the command
os.system(cmd) 