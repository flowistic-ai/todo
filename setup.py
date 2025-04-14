from setuptools import setup, find_packages

setup(
    name="flowistic-todo",
    version="0.1.1",
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
            "todo=flowistic_todo.cli:app",
        ],
    },
    author="Fayssal El Mofatiche",
    author_email="fayssal.elmofatiche@flowistic.ai",
    description="A rich CLI todo app with project management and task tagging",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="todo, cli, project management",
    python_requires=">=3.7",
    url="https://github.com/flowistic-ai/todo",
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
