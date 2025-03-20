#!/usr/bin/env python
"""
Setup script for the State of Mika SDK.
"""

from setuptools import setup, find_packages
import os
import re

# Read the version from the __init__.py file
def get_version():
    init_file = os.path.join(os.path.dirname(__file__), "state_of_mika", "__init__.py")
    with open(init_file, "r") as f:
        content = f.read()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    raise RuntimeError("Unable to find version string in __init__.py")

# Read the long description from the README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Parse requirements while handling comments and separating git dependencies
requirements = [
    "aiohttp>=3.8.0",
    "anthropic>=0.15.0",
    "pyyaml>=6.0",
]

# Development requirements
dev_requirements = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "mypy>=1.0.0",
]

dependency_links = []

# Try to read from requirements.txt if it exists
try:
    with open("requirements.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("git+"):
                dependency_links.append(line)
            elif not line.startswith("git+") and "=" in line:
                requirements.append(line)
except FileNotFoundError:
    # If requirements.txt doesn't exist, continue with the default requirements
    pass

setup(
    name="state-of-mika",
    version=get_version(),
    author="State of Mika Team",
    author_email="info@stateofmika.com",
    description="State of Mika SDK - Connect LLMs with capability servers using MCP",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/state-of-mika/sdk",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "claude": ["anthropic>=0.5.0"],
    },
    dependency_links=dependency_links,
    entry_points={
        "console_scripts": [
            "som=state_of_mika.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "state_of_mika": ["registry/*.json"],
    },
) 