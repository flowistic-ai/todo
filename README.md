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
- Set and track the status of tasks with full history.
- Update status via CLI (`todo update status <task_id> <status>`).
- **Repeatable Tasks:** You can make tasks repeat automatically by specifying a repeat rule in natural language (e.g., "every day", "every week"). When a repeatable task is completed, it is automatically reopened with a new due date based on the rule.

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

**New:**
- The board now features interactive filter controls at the top for **Status**, **Type**, and **Due Date**. You can select multiple options in each filter to dynamically filter the displayed tasks. The filters are styled for clarity and compactness, making it easy to focus on specific subsets of your tasks.

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
- Repeat rule (optional, e.g., "every week")

### Add a Repeatable Task
```bash
todo add
# You will be prompted for repeat rule (e.g., every week)
```

### Update Repeat Rule
```bash
todo update repeat <task_id> "every month"
```

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

# Update status
todo update status PROJ-001 pending    # Set status directly
todo update status PROJ-001            # Interactive prompt
```

### Evolve Task Status

You can move a task to the next workflow status using the `evolve` command:

```bash
todo evolve <task_id>
```

- Workflow order: `pending` → `doing` → `completed` → `cancelled`
- If the task is already at the last status (`cancelled`), it will remain there and you will be notified.
- The command updates the task status, marks as completed if appropriate, and appends to the status history.

**Example:**

```bash
todo evolve PROJ-001
```

This will move the task `PROJ-001` to the next status in the workflow.

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

### Add and Remove Tags

You can add or remove tags from a task using the following commands:

#### Add a Tag

```bash
todo add-tag <task_id> <tag>
```
- Adds the specified tag to the task if not already present.
- Example:
  ```bash
  todo add-tag PROJ-001 urgent
  ```

#### Remove a Tag

```bash
todo remove-tag <task_id> <tag>
```
- Removes the specified tag from the task if it exists.
- Example:
  ```bash
  todo remove-tag PROJ-001 urgent
  ```

## Commands

- `add`: Add a new task
- `add-tag <task_id> <tag>`: Add a tag to a task
- `board`: Visualize tasks in a Trello-like web board
- `cancel <task_id>`: Mark a task as cancelled
- `complete <task_id>`: Mark a task as completed
- `delete <task_id>`: Permanently remove a task from your todo list
- `evolve <task_id>`: Move a task to the next workflow status (pending → doing → completed → cancelled)
- `help`: Show all commands or detailed help for a specific command
- `init`: Initialize a new project
- `list`: List all tasks
- `note add <task_id> [note]`: Add a new note to a task
- `note reset <task_id>`: Clear all notes from a task
- `remove-tag <task_id> <tag>`: Remove a tag from a task
- `show <task_id>`: Show detailed information about a task
- `status`: Show project status
- `update description <task_id> [description]`: Update the description of a task
- `update due <task_id> [due_date]`: Update the due date of a task
- `update priority <task_id> [priority]`: Update the priority of a task
- `update repeat <task_id> [repeat_rule]`: Update the repeat rule of a task
- `update status <task_id> [status]`: Update the status of a task
- `update title <task_id> [title]`: Update the title of a task
- `update type <task_id> [type]`: Update the type of a task
- `workon <task_id> [-d duration]`: Start a work session on a task

## Changelog

### v0.2.0 (2025-05-03)
- Feature: You can now set the status of a task (pending, doing, completed, cancelled).
- All status changes are tracked in a per-task history (visible with `todo show <task_id>`).
- **Repeatable tasks**: Add a repeat rule in natural language ("every week", "every month"). When completed, task is automatically reopened with next due date.

### v0.2.1 (2025-05-04)
- Added **repeatable task** feature: tasks can be set to repeat automatically based on a natural language rule.

## Configuration

The app stores tasks in YAML format:
- `todo.yaml` is **always** created in the directory where the `todo init` command is run.
- There is **no fallback** to a user-level `.todo.yaml` in the home directory; all data is project-local.
- If in a git repository, `todo.yaml` is automatically added to `.gitignore` (the file is created if it doesn't exist).

## Task Storage Format

```yaml
project:
  name: "My Project"
  description: "Project description"
  prefix: "PROJ"
  next_task_number: 1

tasks:
  - task_id: "PROJ-001"
    title: "Task title"
    status: "pending"
    status_history:
      - status: "pending"
        timestamp: "2025-05-03T10:00:00"
    repeat: "every week"  # Optional, natural language
    due_date: "2025-05-10T23:59:59"
    ...
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