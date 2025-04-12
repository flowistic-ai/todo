# Todo CLI

A rich command-line interface todo app with project management and task tagging capabilities.

## Features

- Interactive task management with a beautiful terminal interface
- Project-based organization with customizable task tags (e.g., PROJ-001)
- Priority levels (low, medium, high) with color coding
- Local or global todo list storage
- Rich command-line interface with helpful prompts

## Installation

You can install the package directly from the source:

```bash
pip install .
```

## Usage

The `todo` command will be available globally after installation. Here are the available commands:

- `todo init` - Initialize a new todo list with project details
- `todo add` - Add a new task interactively
- `todo list` - List all tasks with project information
- `todo complete <tag>` - Mark a task as complete using its tag (e.g., PROJ-001)
- `todo help` - Show help message and command descriptions

For detailed help on any command, use the `--help` flag:

```bash
todo --help
todo add --help
```

## Todo File Location

The app will look for a `todo.yaml` file in the following locations:
1. Current directory
2. User's home directory (as `.todo.yaml`)

This allows you to have both project-specific and global todo lists.