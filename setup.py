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
    ],
    entry_points={
        "console_scripts": [
            "todo=todo_cli.cli:app",
        ],
    },
    author="Your Name",
    description="A rich CLI todo app with project management and task tagging",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="todo, cli, project management",
    python_requires=">=3.7",
)
