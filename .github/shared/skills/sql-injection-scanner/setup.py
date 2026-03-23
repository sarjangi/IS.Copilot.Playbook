"""
SQL Injection Scanner - Setup Configuration
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="vancity-sql-injection-scanner",
    version="1.0.0",
    author="Vancity Platform Engineering",
    author_email="platform-engineering@vancity.com",
    description="Automated SQL injection vulnerability scanner for Python, JavaScript, C#, Java, PHP, and SQL files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook",
    packages=find_packages(exclude=["tests", "evals", "examples"]),
    py_modules=["cli"],
    python_requires=">=3.8",
    install_requires=[
        "aiofiles>=23.1.0",
        "GitPython>=3.1.0",
        "requests>=2.28.0",
        "bandit>=1.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "sql-scanner=cli:cli_main",
            "sql-injection-scanner=cli:cli_main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    keywords="security sql-injection scanner static-analysis vulnerability-detection azure-devops",
    project_urls={
        "Documentation": "https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook?path=/.github/shared/skills/sql-injection-scanner",
        "Source": "https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook",
        "Tracker": "https://dev.azure.com/Vancity/Vancity/_git/IS.Copilot.Playbook/issues",
    },
    include_package_data=True,
    zip_safe=False,
)
