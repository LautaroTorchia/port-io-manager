from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="port_io_manager",
    version="0.1.0",
    description="A tool for managing Port.io resources through Infrastructure as Code",
    author="Craftech",
    author_email="info@craftech.io",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/craftech-io/port-io-manager",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "deepdiff>=6.7.1",
        "python-dotenv>=1.0.0",
        "colorama>=0.4.6",
        "PyYAML>=6.0",
    ],
    entry_points={
        'console_scripts': [
            'port-io-manager=port_io_manager.cli.commands:main',
        ],
    },
)
