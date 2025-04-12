from setuptools import setup, find_packages

setup(
    name="todo-cli",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer==0.9.0",
        "rich==13.7.0",
        "pyyaml==6.0.1",
        "dateparser==1.2.0",
    ],
    entry_points={
        "console_scripts": [
            "todo=todo_cli.cli:app",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A rich CLI todo app with project management and task tagging",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="todo, cli, project management",
    python_requires=">=3.7",
    url="https://github.com/yourusername/todo-cli",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
