"""
Setup script for Backup Manager Pro
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), 'r', encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt', 'r', encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="backup-manager-pro",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A professional backup solution with GUI for local and cloud backups",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/backup-manager-pro",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "backup-manager=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.json"],
    },
    keywords="backup, sync, cloud, google-drive, file-management, gui",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/backup-manager-pro/issues",
        "Source": "https://github.com/yourusername/backup-manager-pro",
        "Documentation": "https://github.com/yourusername/backup-manager-pro/wiki",
    },
)