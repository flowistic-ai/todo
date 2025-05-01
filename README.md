![Demo](images/todo.gif)

# Todo CLI

A powerful command-line interface todo application with project management features, time tracking, and rich terminal output that plays well with git repos and aims to keep in the flow without the need of juggling between external services.

# Motivation / Executive Summary

Efficient task management is essential for productivity in any project. This tool provides a simple, local, and git-friendly way to track todos directly within your project directory. By keeping your todo list version-controlled and out of your repository with `.gitignore`, you can maintain focus and organization without cluttering your codebase or relying on external services, in line with our spirit to enhance productivity and flow at [Flowistic](https://flowistic.ai).

## Features

### Project Management
- Project-based task organization with custom prefixes
- Automatic task numbering (e.g., PROJ-001)
- Local todo lists (per directory)

### Task Management
- Interactive task creation
- Task types (feature, bugfix, docs, test, refactor, chore) with color coding
- Priority levels (high, medium, low) with color coding
- Due dates with natural language support ("tomorrow", "next friday")
- Task completion tracking
- Rich terminal output with detailed task information
- Task notes with chronological history
- Update task properties after creation

### Time Tracking
- Built-in Pomodoro-style timer (default: 25 minutes)
- Customizable work session durations
- Work session history per task
- Interruption tracking
- Total time worked statistics

### Project Analytics
- Comprehensive project status dashboard
- Task completion rates
- Priority distribution
- Due date statistics
- Work session analytics
- Time tracking summary

### Visual Board (Trello-like)

You can visualize your tasks in a Trello-like web board using Dash:

```bash
todo board
```

This command launches a local Dash web app (requires [Dash 3.x+](https://dash.plotly.com/) and [dash-bootstrap-components]) displaying your tasks as cards in columns by status (Pending, Completed, Cancelled). Each card shows:
- Title (with status badge)
- Task type and priority (color-coded badges)
- Task ID
- Due date
- Tags (as badges)

The board uses modern styling for easy scanning and prioritization. The app opens automatically in your browser at [http://127.0.0.1:8050/](http://127.0.0.1:8050/). The browser tab and header will display "Flowistic Task Board".

> **Note:** If you haven't installed Dash, add it via your environment manager:
> ```sh
> uv pip install dash dash-bootstrap-components dash-mantine-components
> ```

## Installation

```bash
pip install flowistic-todo
```

## Usage

### Initialize a Project
```bash
todo init
```
Follow the prompts to set:
- Project name
- Project description
- Task prefix (e.g., "PROJ" for PROJ-001)

If the current directory is a git repository, `todo.yaml` will be automatically added to `.gitignore`.

### Add a Task
```bash
todo add
```
You'll be prompted for:
- Task title
- Description (optional)
- Type (feature/bugfix/docs/test/refactor/chore)
- Priority (low/medium/high)
- Due date (optional, supports natural language)
- Initial note (optional)

### List Tasks
```bash
todo list
```
Shows a table with:
- Task ID (e.g., PROJ-001)
- Type (color-coded by category)
- Title
- Priority (color-coded)
- Due date status
- Time worked
- Completion status
- Number of notes

### Show Task Details
```bash
todo show PROJ-001
```
Shows detailed information about a specific task:
- Task title and task ID
- Task type
- Status and priority
- Description
- All notes in chronological order
- Due date with status
- Work session history
- Creation date

### Manage Task Notes
```bash
todo note add PROJ-001 "Note text"     # Add a new note
todo note add PROJ-001                 # Add note with interactive prompt
todo note reset PROJ-001               # Clear all notes (with confirmation)
```

### Update Task Properties
```bash
# Update task type
todo update type PROJ-001 feature       # Set type directly
todo update type PROJ-001              # Interactive prompt

# Update task priority
todo update priority PROJ-001 high     # Set priority directly
todo update priority PROJ-001          # Interactive prompt

# Update due date
todo update due PROJ-001 "next friday" # Set due date directly
todo update due PROJ-001 clear         # Remove due date
todo update due PROJ-001               # Interactive prompt

# Update title
todo update title PROJ-001 "New title" # Set title directly
todo update title PROJ-001             # Interactive prompt

# Update description
todo update description PROJ-001 "New description" # Set description directly
todo update description PROJ-001                   # Interactive prompt
```

### Task Cancellation & Deletion

- `todo cancel <task_id>`: Mark a task as cancelled. The task remains in your list but its status is shown as cancelled in both `list` and `show` commands.
    - Example: `todo cancel PROJ-001`
- `todo delete <task_id>`: Permanently remove a task from your todo list. This action cannot be undone.
    - Example: `todo delete PROJ-002`

Cancelled tasks are excluded from project completion statistics and are clearly indicated in task listings.

### Work on a Task
```bash
todo workon PROJ-001              # Start a 25-minute work session
todo workon PROJ-001 -d 45       # Start a 45-minute work session
```
Features:
- Interactive progress bar
- Time tracking
- Session history
- Graceful interruption handling (Ctrl+C)

### View Project Status
```bash
todo status
```
Shows:
- Project information
- Task completion rates
- Priority distribution
- Due date statistics
- Work session analytics
- Time tracking summary

### Complete a Task
```bash
todo complete PROJ-001
```

### Get Help
```bash
todo help                # Show all commands
todo help <command>      # Show detailed help for a specific command
```

## Configuration

The app stores tasks in YAML format:
- `todo.yaml` in the directory where the `todo init` command is run
- If in a git repository, `todo.yaml` is automatically added to `.gitignore`

## Task Storage Format

```yaml
project:
  name: "My Project"
  description: "Project description"
  prefix: "PROJ"
  next_task_number: 1
tasks:
  - task_id: "PROJ-001"
    title: "Example Task"
    description: "Task description"
    type: "feature"
    priority: "high"
    created_at: "2025-04-12T20:00:00"
    due_date: "2025-04-19T23:59:59"
    completed: false
    notes:
      - "Initial task planning complete"
      - "Updated requirements after review"
    work_sessions:
      - started_at: "2025-04-12T20:30:00"
        duration: 25
        interrupted: false
```

## Running Tests

This project uses [pytest](https://docs.pytest.org/) for testing and [uv](https://github.com/astral-sh/uv) for environment management. To run all tests:

```sh
uv pip install -r requirements.txt
uv pytest
```

If you encounter import errors or tests are not discovered:
- Make sure you are in the project root directory.
- Ensure `pytest` is installed in your uv environment.
- If you see import errors related to `todo`, try:
  ```sh
  PYTHONPATH=. uv pytest
  ```

Test files are located in the `tests/` directory and cover both core logic and CLI commands.

## Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the CLI:
```bash
python -m todo.cli
```

## License

MIT License