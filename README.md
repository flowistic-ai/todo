# Todo CLI

A powerful command-line interface todo application with project management features, time tracking, and rich terminal output.

## Features

### Project Management
- Project-based task organization with custom prefixes
- Automatic task numbering (e.g., PROJ-001)
- Local or global todo lists (per directory or user-wide)

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

## Installation

```bash
pip install todo-cli
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
- Task tag (e.g., PROJ-001)
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
- Task title and tag
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
todo update due PROJ-001               # Interactive promp- Update task properties after creationt

# Update title
todo update title PROJ-001 "New title" # Set title directly
todo update title PROJ-001             # Interactive prompt

# Update description
todo update description PROJ-001 "New description" # Set description directly
todo update description PROJ-001                   # Interactive prompt
```

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
- Local project: `todo.yaml` in the current directory
- Global fallback: `.todo.yaml` in your home directory

## Task Storage Format

```yaml
project:
  name: "My Project"
  description: "Project description"
  prefix: "PROJ"
  next_task_number: 1
tasks:
  - tag: "PROJ-001"
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

## Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the CLI:
```bash
python -m flowistic_todo.cli
```

## License

MIT License