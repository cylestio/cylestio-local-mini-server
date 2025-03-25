from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f.readlines() if not line.startswith("#")]

# Read README for long description
with open("README.md", "r") as f:
    long_description = f.read()

# Get version (create a VERSION file for easier updates)
version = "0.1.0"  # Default version
if os.path.exists("VERSION"):
    with open("VERSION", "r") as f:
        version = f.read().strip()

setup(
    name="cylestio-local-mini-server",
    version=version,
    description="A lightweight telemetry processing server for AI agents",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cylestio",
    author_email="info@cylestio.com",
    url="https://github.com/cylestio/cylestio-local-mini-server",
    packages=find_packages(exclude=["tests*", "*.tests", "*.tests.*"]),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cylestio-server=app.main:run_server",
        ],
    },
) 