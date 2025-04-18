"""Todo CLI."""

import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

import dateparser
import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.text import Text
from dateutil import parser

app = typer.Typer()
console = Console()

# Define valid task types
TASK_TYPES = ["feature", "bugfix", "docs", "test", "refactor", "chore"]

# Define task type colors
TASK_TYPE_COLORS = {
    "feature": "green",
    "bugfix": "red",
    "docs": "blue",
    "test": "yellow",
    "refactor": "magenta",
    "chore": "cyan",
}


def get_todo_file() -> Path:
    """Get the todo file path from either the current directory or user's home directory"""
    local_todo = Path("todo.yaml")
    if local_todo.exists():
        print("Found local todo file. Using that...")
        return local_todo

    # If no local todo file, use one in the user's home directory
    home_todo = Path.home() / ".todo.yaml"
    if home_todo.exists():
        print(f"Found home todo file. Using that...{home_todo}")
        return home_todo

    print("No todo file found. Creating one...")
    return local_todo


TODO_FILE = get_todo_file()


def load_todos() -> Dict:
    """Load todos from the todo file"""
    if not TODO_FILE.exists():
        return {
            "project": {
                "name": "",
                "description": "",
                "prefix": "",
                "next_task_number": 1,
            },
            "tasks": [],
        }
    with open(TODO_FILE, "r") as f:
        return yaml.safe_load(f) or {
            "project": {
                "name": "",
                "description": "",
                "prefix": "",
                "next_task_number": 1,
            },
            "tasks": [],
        }


def save_todos(todos: Dict):
    """Save todos to the todo file"""
    # Ensure the directory exists for the todo file
    TODO_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TODO_FILE, "w") as f:
        yaml.dump(todos, f, sort_keys=False)


def parse_due_date(date_str: str) -> Optional[datetime]:
    """Parse a due date string into a datetime object"""
    if not date_str:
        return None

    parsed_date = dateparser.parse(date_str)
    if parsed_date:
        # Set time to end of day (23:59:59) for due dates
        parsed_date = parsed_date.replace(hour=23, minute=59, second=59)
    return parsed_date


def format_due_date(due_date: Optional[datetime]) -> str:
    """Format a due date for display"""
    if not due_date:
        return "-"

    now = datetime.now()
    days_until = (due_date - now).days

    if days_until < 0:
        return f"Overdue by {abs(days_until)} days"
    elif days_until == 0:
        return "Due today"
    elif days_until == 1:
        return "Due tomorrow"
    else:
        return f"Due in {days_until} days"


def format_duration(minutes: int) -> str:
    """Format duration in minutes to a human-readable string"""
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def get_total_worked_time(work_sessions: List[Dict]) -> int:
    """Calculate total worked time in minutes from work sessions"""
    return sum(session["duration"] for session in work_sessions)


@app.command()
def init():
    """
    Initialize a new todo list with project details.

    This command will:
    - Create a new todo.yaml file in the current directory
    - Prompt for project name, description, and task prefix
    - Reset any existing todo list if confirmed

    If a todo list already exists, you will be asked for confirmation before resetting.
    """
    if TODO_FILE.exists():
        if not Confirm.ask("A todo list already exists. Do you want to reset it?"):
            raise typer.Abort()

    project_name = Prompt.ask("Project name")
    project_description = Prompt.ask("Project description")
    project_prefix = Prompt.ask("Task prefix (e.g. 'PROJ' for PROJ-001)")

    todos = {
        "project": {
            "name": project_name,
            "description": project_description,
            "prefix": project_prefix,
            "next_task_number": 1,
        },
        "tasks": [],
    }
    save_todos(todos)
    console.print("[green]✓[/green] Initialized new todo list!")
    console.print(f"Project: [bold]{project_name}[/bold]")
    console.print(f"Description: {project_description}")
    console.print(f"Todo file location: {TODO_FILE}")


@app.command()
def add():
    """
    Add a new task interactively.

    You will be prompted for:
    - Task title (required)
    - Description (optional)
    - Type (feature/bugfix/docs/test/refactor/chore)
    - Priority (low/medium/high)
    - Due date (optional, supports natural language)
    - Initial note (optional)

    The task will be automatically tagged using the project prefix.
    Example: For project prefix 'PROJ', first task will be 'PROJ-001'
    """
    todos = load_todos()

    if not todos["project"]["prefix"]:
        console.print(
            "[red]Error:[/red] Project not initialized. Please run 'todo init' first."
        )
        return

    title = Prompt.ask("Task title")
    description = Prompt.ask("Description (optional)", default="")
    task_type = Prompt.ask("Type", choices=TASK_TYPES, default="feature")
    priority = Prompt.ask(
        "Priority", choices=["low", "medium", "high"], default="medium"
    )
    due_date_str = Prompt.ask(
        "Due date (optional, e.g., 'tomorrow', 'next friday', '2025-04-20')", default=""
    )
    notes = Prompt.ask("Initial note (optional)", default="")

    due_date = parse_due_date(due_date_str)
    if due_date_str and not due_date:
        console.print(
            "[yellow]Warning:[/yellow] Could not parse due date, task will be created without one."
        )

    # Generate task tag
    task_number = todos["project"]["next_task_number"]
    task_tag = f"{todos['project']['prefix']}-{task_number:03d}"
    todos["project"]["next_task_number"] += 1

    task = {
        "tag": task_tag,
        "title": title,
        "description": description,
        "type": task_type,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "completed": False,
        "work_sessions": [],
        "notes": [notes] if notes else [],
    }

    todos["tasks"].append(task)
    save_todos(todos)
    console.print(f"[green]✓[/green] Task [bold]{task_tag}[/bold] added successfully!")


@app.command()
def list():
    """
    List all tasks with project information.

    Displays a table with:
    - Task tag (e.g., PROJ-001)
    - Type (feature/bugfix/etc.)
    - Title
    - Priority (color-coded)
    - Due date
    - Time worked
    - Status
    - Notes count
    """
    todos = load_todos()

    # Show project info
    if todos["project"]["name"]:
        console.print(f"\n[bold]Project:[/bold] {todos['project']['name']}")
        console.print(f"[bold]Description:[/bold] {todos['project']['description']}\n")

    if not todos["tasks"]:
        console.print("[yellow]No tasks found![/yellow]")
        return

    table = Table(
        "Tag",
        "Type",
        "Title",
        "Priority",
        "Due Date",
        "Time Worked",
        "Status",
        "Notes",
        title="Tasks",
        expand=True,
    )

    # Sort tasks by due date and completion status
    def sort_key(task):
        if "due_date" not in task:
            task["due_date"] = None
        due_date = (
            datetime.fromisoformat(task["due_date"])
            if task["due_date"]
            else datetime.max
        )
        return (task["completed"], due_date)

    sorted_tasks = sorted(todos["tasks"], key=sort_key)

    for task in sorted_tasks:
        status = "[green]✓[/green]" if task["completed"] else "[red]✗[/red]"
        priority_color = {"low": "blue", "medium": "yellow", "high": "red"}[
            task["priority"]
        ]

        due_date_str = ""
        due_date_style = ""
        if task.get("due_date"):
            due_date = parser.parse(task["due_date"])
            now = datetime.now()
            due_date_str = format_due_date(due_date)

            if due_date < now:
                due_date_style = "red"
            elif due_date < now + timedelta(days=2):
                due_date_style = "yellow"
            else:
                due_date_style = "green"

        # Calculate total time worked
        total_time = "0m"
        if "work_sessions" in task:
            minutes = get_total_worked_time(task["work_sessions"])
            total_time = format_duration(minutes)

        # Format notes count if they exist
        notes_text = ""
        if task.get("notes"):
            note_count = len(task["notes"])
            notes_text = f"[dim]{note_count} note{'s' if note_count != 1 else ''}[/dim]"

        # Format task type with color
        type_color = TASK_TYPE_COLORS[task["type"]]

        table.add_row(
            task["tag"],
            Text(task["type"], style=type_color),
            Text(task["title"], style="bold"),
            Text(task["priority"], style=priority_color),
            Text(due_date_str, style=due_date_style) if due_date_str else "",
            total_time,
            status,
            notes_text,
        )

    console.print(table)


@app.command()
def complete(tag: str):
    """
    Mark a task as complete by its tag.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)

    Example:
        todo complete PROJ-001
    """
    todos = load_todos()

    for task in todos["tasks"]:
        if task["tag"].lower() == tag.lower():
            task["completed"] = True
            save_todos(todos)
            console.print(
                f"[green]✓[/green] Task [bold]{tag}[/bold] marked as complete!"
            )
            return

    console.print(f"[red]Error:[/red] Task with tag [bold]{tag}[/bold] not found!")


@app.command()
def workon(
    tag: str,
    duration: Optional[int] = typer.Option(
        25, "--duration", "-d", help="Duration in minutes"
    ),
):
    """
    Work on a specific task with an interactive timer.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        duration: Work session duration in minutes (default: 25)

    Features:
    - Interactive progress bar with time tracking
    - Records work sessions in task history
    - Handles interruptions gracefully (Ctrl+C)

    Example:
        todo workon PROJ-001
        todo workon PROJ-001 --duration 45
    """
    todos = load_todos()

    # Find the task
    task = None
    for t in todos["tasks"]:
        if t["tag"].lower() == tag.lower():
            task = t
            break

    if not task:
        console.print(f"[red]Error:[/red] Task with tag [bold]{tag}[/bold] not found!")
        return

    # Initialize work_sessions if it doesn't exist
    if "work_sessions" not in task:
        task["work_sessions"] = []

    # Show task info
    console.print(f"\n[bold]Working on:[/bold] {task['title']} ({task['tag']})")
    if task["work_sessions"]:
        total_time = get_total_worked_time(task["work_sessions"])
        console.print(f"[dim]Total time worked: {format_duration(total_time)}[/dim]")

    # Create progress bar
    total_seconds = duration * 60

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            work_task = progress.add_task(
                f"[cyan]Working on {task['tag']}...",
                total=total_seconds,
            )

            start_time = datetime.now()

            # Setup signal handler for clean exit
            def handle_interrupt(signum, frame):
                progress.stop()
                console.print("\n[yellow]Work session interrupted![/yellow]")
                actual_duration = int(
                    (datetime.now() - start_time).total_seconds() / 60
                )
                if actual_duration > 0:
                    save_work_session(todos, task, actual_duration, interrupted=True)
                sys.exit(0)

            signal.signal(signal.SIGINT, handle_interrupt)

            while not progress.finished:
                progress.update(work_task, advance=1)
                time.sleep(1)

            # Save the work session
            save_work_session(todos, task, duration)

            console.print(
                f"\n[green]✓[/green] Completed {format_duration(duration)} work session!"
            )

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        console.print("\n[yellow]Work session interrupted![/yellow]")
        actual_duration = int((datetime.now() - start_time).total_seconds() / 60)
        if actual_duration > 0:
            save_work_session(todos, task, actual_duration, interrupted=True)


def save_work_session(
    todos: Dict, task: Dict, duration: int, interrupted: bool = False
):
    """Save a work session to the task"""
    session = {
        "started_at": datetime.now().isoformat(),
        "duration": duration,
        "interrupted": interrupted,
    }
    task["work_sessions"].append(session)
    save_todos(todos)


# Create a note command group
notes_app = typer.Typer(help="Manage task notes")
app.add_typer(notes_app, name="note")


@notes_app.command("add")
def add_note(
    tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)"),
    text: Optional[str] = typer.Argument(
        None, help="Note text. If not provided, will prompt for input."
    ),
):
    """
    Add a new note to a task. Notes are stored as a chronological list.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        text: Note text (optional). If not provided, will prompt for input.

    Example:
        todo note add PROJ-001 "Remember to update documentation"
        todo note add PROJ-001  # Will prompt for note text
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Initialize notes list if it doesn't exist
    if "notes" not in task:
        task["notes"] = []

    # If no text provided, show existing notes and prompt for new one
    if text is None:
        if task["notes"]:
            console.print("\nExisting notes:")
            for i, note in enumerate(task["notes"], 1):
                console.print(f"[dim]{i}.[/dim] {note}")
            console.print()
        text = Prompt.ask("Enter new note")

    # Add the new note to the list
    if text:
        task["notes"].append(text)
        save_todos(todos)
        console.print(f"[green]✓[/green] Added new note to task {tag}")


@notes_app.command("reset")
def reset_notes(tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)")):
    """
    Reset (clear) all notes from a task.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)

    Example:
        todo note reset PROJ-001
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Check if task has any notes
    if not task.get("notes"):
        console.print("[yellow]Task has no notes to reset.[/yellow]")
        return

    # Show current notes
    console.print("\nCurrent notes:")
    for i, note in enumerate(task["notes"], 1):
        console.print(f"[dim]{i}.[/dim] {note}")

    # Confirm reset
    if Confirm.ask("\nAre you sure you want to reset all notes?", default=False):
        task["notes"] = []
        save_todos(todos)
        console.print("[green]✓[/green] All notes have been cleared.")
    else:
        console.print("Operation cancelled.")


@app.command()
def show(tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)")):
    """
    Show detailed information about a specific task.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)

    Example:
        todo show PROJ-001
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Create a panel to display task information
    console.print(
        f"\n[bold blue]{task['tag']}[/bold blue]: [bold]{task['title']}[/bold]"
    )

    # Type and Priority
    type_color = TASK_TYPE_COLORS[task["type"]]
    console.print(f"Type: [{type_color}]{task['type']}[/{type_color}]")
    status = (
        "[green]✓ Completed[/green]"
        if task["completed"]
        else "[yellow]⧖ In Progress[/yellow]"
    )
    priority_colors = {"high": "red", "medium": "yellow", "low": "blue"}
    priority = f"[{priority_colors[task['priority']]}]{task['priority']}[/{priority_colors[task['priority']]}]"
    console.print(f"Status: {status}")
    console.print(f"Priority: {priority}")

    # Description
    if task.get("description"):
        console.print("\n[bold]Description:[/bold]")
        console.print(task["description"])

    # Notes
    if task.get("notes"):
        console.print("\n[bold]Notes:[/bold]")
        for i, note in enumerate(task["notes"], 1):
            console.print(f"[dim]{i}.[/dim] {note}")

    # Due Date
    if task.get("due_date"):
        due_date = parser.parse(task["due_date"])
        now = datetime.now()
        due_date_str = format_due_date(due_date)

        if due_date < now:
            due_style = "red"
        elif due_date < now + timedelta(days=2):
            due_style = "yellow"
        else:
            due_style = "green"

        console.print(
            f"\n[bold]Due Date:[/bold] [{due_style}]{due_date_str}[/{due_style}]"
        )

    # Work Sessions
    if task.get("work_sessions"):
        console.print("\n[bold]Work Sessions:[/bold]")
        total_time = get_total_worked_time(task["work_sessions"])

        table = Table("Date", "Duration", "Status", show_header=True, box=None)
        for session in sorted(task["work_sessions"], key=lambda x: x["started_at"]):
            start_time = parser.parse(session["started_at"])
            duration = format_duration(session["duration"])
            status = (
                "[yellow]Interrupted[/yellow]"
                if session.get("interrupted")
                else "[green]Completed[/green]"
            )

            table.add_row(start_time.strftime("%Y-%m-%d %H:%M"), duration, status)

        console.print(table)
        console.print(
            f"\nTotal time worked: [bold]{format_duration(total_time)}[/bold]"
        )

    # Created Date
    created_at = parser.parse(task["created_at"])
    console.print(f"\nCreated: {created_at.strftime('%Y-%m-%d %H:%M')}")


def calculate_project_stats(todos: Dict) -> Dict:
    """Calculate comprehensive project statistics"""
    stats = {
        "total_tasks": len(todos["tasks"]),
        "completed_tasks": 0,
        "pending_tasks": 0,
        "high_priority": 0,
        "medium_priority": 0,
        "low_priority": 0,
        "overdue_tasks": 0,
        "due_today": 0,
        "no_due_date": 0,
        "total_work_time": 0,
        "completed_work_time": 0,
        "pending_work_time": 0,
        "interrupted_sessions": 0,
        "total_sessions": 0,
    }

    now = datetime.now()

    for task in todos["tasks"]:
        # Task completion stats
        if task["completed"]:
            stats["completed_tasks"] += 1
        else:
            stats["pending_tasks"] += 1

        # Priority stats
        stats[f"{task['priority']}_priority"] += 1

        # Due date stats
        if task.get("due_date"):
            due_date = datetime.fromisoformat(task["due_date"])
            if due_date.date() == now.date():
                stats["due_today"] += 1
            elif due_date < now:
                stats["overdue_tasks"] += 1
        else:
            stats["no_due_date"] += 1

        # Work session stats
        if "work_sessions" in task:
            task_work_time = get_total_worked_time(task["work_sessions"])
            stats["total_work_time"] += task_work_time
            if task["completed"]:
                stats["completed_work_time"] += task_work_time
            else:
                stats["pending_work_time"] += task_work_time

            stats["total_sessions"] += len(task["work_sessions"])
            stats["interrupted_sessions"] += sum(
                1
                for session in task["work_sessions"]
                if session.get("interrupted", False)
            )

    return stats


@app.command()
def status():
    """
    Show detailed project status and statistics.

    Displays:
    - Project information
    - Task completion status
    - Priority distribution
    - Due date statistics
    - Work session analytics
    - Time tracking summary
    """
    todos = load_todos()

    if not todos["project"]["name"]:
        console.print("[yellow]No project initialized. Run 'todo init' first.[/yellow]")
        return

    stats = calculate_project_stats(todos)

    # Project Header
    console.print("\n[bold blue]Project Status[/bold blue]")
    console.print("═" * 50)
    console.print(f"[bold]Project:[/bold] {todos['project']['name']}")
    console.print(f"[bold]Description:[/bold] {todos['project']['description']}")
    console.print(f"[bold]Task Prefix:[/bold] {todos['project']['prefix']}")

    # Task Progress
    console.print("\n[bold]Task Progress[/bold]")
    console.print("─" * 30)
    progress_table = Table(show_header=False, box=None)
    progress_table.add_column("Metric", style="bold")
    progress_table.add_column("Value")

    completion_rate = (
        (stats["completed_tasks"] / stats["total_tasks"] * 100)
        if stats["total_tasks"] > 0
        else 0
    )
    progress_table.add_row(
        "Completion Rate",
        f"{completion_rate:.1f}% ({stats['completed_tasks']}/{stats['total_tasks']} tasks)",
    )
    progress_table.add_row("Pending Tasks", str(stats["pending_tasks"]))
    console.print(progress_table)

    # Priority Distribution
    console.print("\n[bold]Priority Distribution[/bold]")
    console.print("─" * 30)
    priority_table = Table(show_header=False, box=None)
    priority_table.add_column("Priority", style="bold")
    priority_table.add_column("Count")
    priority_table.add_row("High Priority", f"[red]{stats['high_priority']}[/red]")
    priority_table.add_row(
        "Medium Priority", f"[yellow]{stats['medium_priority']}[/yellow]"
    )
    priority_table.add_row("Low Priority", f"[blue]{stats['low_priority']}[/blue]")
    console.print(priority_table)

    # Due Date Status
    console.print("\n[bold]Due Date Status[/bold]")
    console.print("─" * 30)
    due_table = Table(show_header=False, box=None)
    due_table.add_column("Status", style="bold")
    due_table.add_column("Count")
    due_table.add_row("Overdue", f"[red]{stats['overdue_tasks']}[/red]")
    due_table.add_row("Due Today", f"[yellow]{stats['due_today']}[/yellow]")
    due_table.add_row("No Due Date", str(stats["no_due_date"]))
    console.print(due_table)

    # Work Sessions
    if stats["total_sessions"] > 0:
        console.print("\n[bold]Work Sessions[/bold]")
        console.print("─" * 30)
        sessions_table = Table(show_header=False, box=None)
        sessions_table.add_column("Metric", style="bold")
        sessions_table.add_column("Value")

        total_time = format_duration(stats["total_work_time"])
        completed_time = format_duration(stats["completed_work_time"])
        pending_time = format_duration(stats["pending_work_time"])

        completion_rate = stats["total_sessions"] - stats["interrupted_sessions"]
        completion_percentage = (
            (completion_rate / stats["total_sessions"] * 100)
            if stats["total_sessions"] > 0
            else 0
        )

        sessions_table.add_row("Total Sessions", str(stats["total_sessions"]))
        sessions_table.add_row(
            "Completed Sessions", f"{completion_rate} ({completion_percentage:.1f}%)"
        )
        sessions_table.add_row(
            "Interrupted Sessions", str(stats["interrupted_sessions"])
        )
        sessions_table.add_row("Total Time Worked", total_time)
        sessions_table.add_row("Time on Completed Tasks", completed_time)
        sessions_table.add_row("Time on Pending Tasks", pending_time)
        console.print(sessions_table)

    console.print("\n[dim]Use 'todo list' for detailed task information[/dim]")


# Create an update command group
update_app = typer.Typer(help="Update task properties")
app.add_typer(update_app, name="update")


@update_app.command("type")
def update_type(
    tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)"),
    new_type: Optional[str] = typer.Argument(
        None, help="New task type. If not provided, will prompt for input."
    ),
):
    """
    Update a task's type.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        new_type: New task type. If not provided, will prompt for input.

    Example:
        todo update type PROJ-001 feature
        todo update type PROJ-001  # Will prompt for type
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Show current type and get new one
    current_type = task["type"]
    console.print(
        f"\nCurrent type: [{TASK_TYPE_COLORS[current_type]}]{current_type}[/{TASK_TYPE_COLORS[current_type]}]"
    )

    if new_type is None:
        new_type = Prompt.ask("New type", choices=TASK_TYPES, default=current_type)
    elif new_type not in TASK_TYPES:
        console.print(
            f"[red]Error:[/red] Invalid type. Must be one of: {', '.join(TASK_TYPES)}"
        )
        return

    # Update the type
    task["type"] = new_type
    save_todos(todos)
    console.print(
        f"[green]✓[/green] Updated task type to: [{TASK_TYPE_COLORS[new_type]}]{new_type}[/{TASK_TYPE_COLORS[new_type]}]"
    )


@update_app.command("priority")
def update_priority(
    tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)"),
    new_priority: Optional[str] = typer.Argument(
        None, help="New priority. If not provided, will prompt for input."
    ),
):
    """
    Update a task's priority.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        new_priority: New priority. If not provided, will prompt for input.

    Example:
        todo update priority PROJ-001 high
        todo update priority PROJ-001  # Will prompt for priority
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Show current priority and get new one
    priority_colors = {"high": "red", "medium": "yellow", "low": "blue"}
    current_priority = task["priority"]
    console.print(
        f"\nCurrent priority: [{priority_colors[current_priority]}]{current_priority}[/{priority_colors[current_priority]}]"
    )

    if new_priority is None:
        new_priority = Prompt.ask(
            "New priority", choices=["low", "medium", "high"], default=current_priority
        )
    elif new_priority not in ["low", "medium", "high"]:
        console.print(
            "[red]Error:[/red] Invalid priority. Must be one of: low, medium, high"
        )
        return

    # Update the priority
    task["priority"] = new_priority
    save_todos(todos)
    console.print(
        f"[green]✓[/green] Updated task priority to: [{priority_colors[new_priority]}]{new_priority}[/{priority_colors[new_priority]}]"
    )


@update_app.command("due")
def update_due_date(
    tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)"),
    new_date: Optional[str] = typer.Argument(
        None, help="New due date. If not provided, will prompt for input."
    ),
):
    """
    Update a task's due date.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        new_date: New due date. If not provided, will prompt for input.
                 Use 'clear' to remove the due date.

    Example:
        todo update due PROJ-001 "next friday"
        todo update due PROJ-001 clear    # Remove due date
        todo update due PROJ-001          # Will prompt for due date
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Show current due date
    current_due = None
    if task.get("due_date"):
        current_due = parser.parse(task["due_date"])
        console.print(f"\nCurrent due date: {format_due_date(current_due)}")
    else:
        console.print("\nNo current due date")

    if new_date is None:
        new_date = Prompt.ask(
            "New due date (optional, e.g., 'tomorrow', 'next friday', '2025-04-20', or 'clear' to remove)",
            default="",
        )

    # Handle clearing the due date
    if new_date.lower() == "clear":
        task["due_date"] = None
        save_todos(todos)
        console.print("[green]✓[/green] Removed due date")
        return

    # Parse and validate new date
    if new_date:
        new_due = parse_due_date(new_date)
        if not new_due:
            console.print("[red]Error:[/red] Invalid date format")
            return
        task["due_date"] = new_due.isoformat()
        save_todos(todos)
        console.print(
            f"[green]✓[/green] Updated due date to: {format_due_date(new_due)}"
        )


@update_app.command("title")
def update_title(
    tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)"),
    new_title: Optional[str] = typer.Argument(
        None, help="New title. If not provided, will prompt for input."
    ),
):
    """
    Update a task's title.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        new_title: New title. If not provided, will prompt for input.

    Example:
        todo update title PROJ-001 "New task title"
        todo update title PROJ-001  # Will prompt for title
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Show current title and get new one
    console.print(f"\nCurrent title: {task['title']}")

    if new_title is None:
        new_title = Prompt.ask("New title", default=task["title"])

    # Update the title
    task["title"] = new_title
    save_todos(todos)
    console.print(f"[green]✓[/green] Updated task title to: {new_title}")


@update_app.command("description")
def update_description(
    tag: str = typer.Argument(..., help="The task's tag (e.g., PROJ-001)"),
    new_description: Optional[str] = typer.Argument(
        None, help="New description. If not provided, will prompt for input."
    ),
):
    """
    Update a task's description.

    Arguments:
        tag: The task's tag (e.g., PROJ-001, case-insensitive)
        new_description: New description. If not provided, will prompt for input.

    Example:
        todo update description PROJ-001 "New task description"
        todo update description PROJ-001  # Will prompt for description
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["tag"].lower() == tag.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{tag}' not found!")
        return

    # Show current description and get new one
    if task.get("description"):
        console.print(f"\nCurrent description: {task['description']}")
    else:
        console.print("\nNo current description")

    if new_description is None:
        new_description = Prompt.ask(
            "New description", default=task.get("description", "")
        )

    # Update the description
    task["description"] = new_description
    save_todos(todos)
    console.print(f"[green]✓[/green] Updated task description")


@app.command()
def help(command: Optional[str] = typer.Argument(None, help="Command to get help for")):
    """
    Show help for all commands or detailed help for a specific command.

    Arguments:
        command: Optional command name to get detailed help for

    Examples:
        todo help          # Show all commands
        todo help workon   # Show detailed help for 'workon' command
        todo help add      # Show detailed help for 'add' command
    """
    if command:
        # Get the command function
        cmd = app.registered_commands.get(command)
        if not cmd:
            console.print(f"[red]Error:[/red] Command '{command}' not found!")
            return

        # Show detailed help for the command
        console.print(f"\n[bold blue]Command:[/bold blue] todo {command}")
        console.print(f"\n[bold]Description:[/bold]")
        console.print(cmd.callback.__doc__ or "No description available.")

        # Show command options if any
        if cmd.params:
            console.print("\n[bold]Options:[/bold]")
            for param in cmd.params:
                if param.default != param.empty:
                    console.print(f"  --{param.name} [{param.type_name}]")
                    if param.help:
                        console.print(f"    {param.help}")
        return

    # Show general help with all commands
    console.print("\n[bold blue]Todo App Commands:[/bold blue]")

    commands = [
        ("init", "Initialize a new todo list with project details"),
        ("add", "Add a new task interactively"),
        ("list", "List all tasks with project information"),
        ("show <tag>", "Show detailed information about a specific task"),
        ("status", "Show detailed project status and statistics"),
        ("complete <tag>", "Mark a task as complete using its tag (e.g., PROJ-001)"),
        (
            "workon <tag>",
            "Work on a specific task for a given duration (default: 25 minutes)",
        ),
        ("note add <tag>", "Add a new note to a task"),
        ("note reset <tag>", "Reset (clear) all notes from a task"),
        ("update type <tag>", "Update a task's type"),
        ("update priority <tag>", "Update a task's priority"),
        ("update due <tag>", "Update a task's due date"),
        ("update title <tag>", "Update a task's title"),
        ("update description <tag>", "Update a task's description"),
        ("help [command]", "Show this help message or detailed help for a command"),
    ]

    table = Table(show_header=False, box=None)
    table.add_column("Command", style="green")
    table.add_column("Description")

    for cmd, desc in commands:
        table.add_row(f"todo {cmd}", desc)

    console.print(table)
    console.print(
        "\n[dim]For detailed help on any command, use: todo help <command>[/dim]"
    )


if __name__ == "__main__":
    app()
