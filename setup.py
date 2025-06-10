from setuptools import setup, find_packages

setup(
    name="port_io_manager",
    version="0.1.0",
    description="A tool for managing Port.io resources through Infrastructure as Code",
    author="Craftech",
    packages=find_packages(),
    install_requires=[
        'requests>=2.31.0',
        'deepdiff>=6.7.1',
        'python-dotenv>=1.0.0',
    ],
    entry_points={
        'console_scripts': [
            'port-io-manager=port_io_manager.cli.commands:main',
        ],
    },
    python_requires='>=3.8',
)
