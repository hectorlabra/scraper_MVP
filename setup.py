from setuptools import setup, find_packages

setup(
    name="leadscraper-latam",
    version="0.1.0",
    description="A tool for scraping business leads from multiple sources in LATAM",
    author="Héctor Labra",
    author_email="hector.labra@example.com",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        line.strip() for line in open("requirements.txt")
        if not line.startswith("#") and line.strip()
    ],
    entry_points={
        "console_scripts": [
            "leadscraper=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Business/Marketing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
