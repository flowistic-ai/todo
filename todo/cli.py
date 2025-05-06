"""Todo CLI."""

import signal
import sys
import time
import os
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
from todo.board import launch_board
import pandas as pd

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
    """Get the todo file path from the current directory"""
    local_todo = Path("todo.yaml")
    if local_todo.exists():
        return local_todo

    # No fallback to home directory anymore
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
    - Add todo.yaml to .gitignore if in a git repository

    If a todo list already exists, you will be asked for confirmation before resetting.
    """
    # Update TODO_FILE to ensure we're always using the local file for init
    global TODO_FILE
    TODO_FILE = Path("todo.yaml")
    
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
    
    # Check if current directory is a git repository
    if Path(".git").is_dir():
        # Check if .gitignore exists
        gitignore_path = Path(".gitignore")
        
        if gitignore_path.exists():
            # Read existing .gitignore content
            with open(gitignore_path, "r") as f:
                gitignore_content = f.read()
            
            # Check if todo.yaml is already in .gitignore
            if "todo.yaml" not in gitignore_content:
                # Add todo.yaml to .gitignore
                with open(gitignore_path, "a") as f:
                    # Add a newline if the file doesn't end with one
                    if gitignore_content and not gitignore_content.endswith("\n"):
                        f.write("\n")
                    f.write("# Todo CLI file\ntodo.yaml\n")
                console.print("[green]✓[/green] Added todo.yaml to .gitignore")
        else:
            # Create new .gitignore file with todo.yaml
            with open(gitignore_path, "w") as f:
                f.write("# Todo CLI file\ntodo.yaml\n")
            console.print("[green]✓[/green] Created .gitignore with todo.yaml")


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
    - Tags (comma-separated, optional)
    - Repeat (optional, natural language)

    The task will be automatically assigned a task id using the project prefix.
    Example: For project prefix 'PROJ', first task will be 'PROJ-001'
    """
    todos = load_todos()

    if not todos["project"]["prefix"]:
        console.print(
            "[red]Error:[/red] Project prefix not set. Run 'todo init' first."
        )
        raise typer.Abort()

    title = Prompt.ask("Task title")
    description = Prompt.ask("Description", default="")
    task_type = Prompt.ask("Type", choices=TASK_TYPES, default="feature")
    priority = Prompt.ask("Priority", choices=["low", "medium", "high"], default="medium")
    due_date_str = Prompt.ask("Due date (optional)", default="")
    due_date = parse_due_date(due_date_str) if due_date_str else None
    notes = Prompt.ask("Initial note (optional)", default="")
    tags_str = Prompt.ask("Tags (comma-separated, optional)", default="")
    tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()] if tags_str else []
    repeat = Prompt.ask("Repeat (e.g., every day, every week, leave blank for none)", default=None)

    task_id = f"{todos['project']['prefix']}-{todos['project']['next_task_number']:03d}"
    todos["project"]["next_task_number"] += 1

    task = {
        "task_id": task_id,
        "title": title,
        "description": description,
        "type": task_type,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "completed": False,
        "work_sessions": [],
        "notes": [notes] if notes else [],
        "tags": tags,
        "status": "pending",
        "status_history": [
            {"status": "pending", "timestamp": datetime.now().isoformat()}
        ],
        "repeat": repeat if repeat else None,
    }

    todos["tasks"].append(task)
    save_todos(todos)
    console.print(f"[green]✓[/green] Task [bold]{task_id}[/bold] added successfully!")


@app.command()
def tags():
    """
    List all unique tags across all tasks, along with the number of tasks for each tag.
    """
    todos = load_todos()
    tag_counts = {}
    for task in todos["tasks"]:
        for tag in (task.get("tags") or []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    if tag_counts:
        console.print("[bold]Tags:[/bold]")
        for t in sorted(tag_counts):
            console.print(f"- {t} [dim]({tag_counts[t]} task{'s' if tag_counts[t] != 1 else ''})[/dim]")
    else:
        console.print("[yellow]No tags found.[/yellow]")


@app.command()
def tag_tasks(tag: str):
    """
    List all tasks associated with a given tag.
    """
    todos = load_todos()
    filtered = [t for t in todos["tasks"] if tag in (t.get("tags") or [])]
    if not filtered:
        console.print(f"[yellow]No tasks found with tag '{tag}'.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task ID")
    table.add_column("Title")
    table.add_column("Type")
    table.add_column("Priority")
    table.add_column("Due Date")
    for task in filtered:
        due_date = format_due_date(parser.parse(task["due_date"])) if task.get("due_date") else "-"
        table.add_row(
            task["task_id"],
            task["title"],
            task["type"],
            task["priority"],
            due_date,
        )
    console.print(table)


@app.command()
def list(
    all: bool = typer.Option(
        False,
        "-a",
        "--all",
        help="Show all tasks, including completed and cancelled"
    ),
    tag: Optional[str] = typer.Option(
        None,
        "--tag",
        help="Filter tasks by tag"
    ),
):
    """
    List all pending tasks with project information.
    By default, only shows pending tasks. Use -a/--all to show all tasks (including completed and cancelled).
    Use --tag to filter tasks by a specific tag.
    Displays tags for each task.
    """
    todos = load_todos()

    # Show project info
    if todos["project"]["name"]:
        console.print(f"\n[bold blue]Project:[/bold blue] {todos['project']['name']}")
        console.print(f"[dim]Prefix:[/dim] {todos['project']['prefix']}\n")

    tasks = todos["tasks"]
    if tag:
        tasks = [t for t in tasks if tag in (t.get("tags") or [])]

    # Filter tasks
    if not all:
        tasks = [t for t in tasks if not t.get("completed", False) and t.get("status", "") != "cancelled"]

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task ID")
    table.add_column("Type")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Due Date")
    table.add_column("Time Worked")
    table.add_column("Status")
    table.add_column("Notes")
    table.add_column("Tags")

    for task in tasks:
        # Ensure tags are sorted for display consistency
        tags_list = sorted(task.get("tags") or [])
        due_date_str = format_due_date(parser.parse(task["due_date"])) if task.get("due_date") else "-"
        total_time = format_duration(sum(ws["duration"] for ws in task.get("work_sessions", [])))
        # Improved status display
        if task.get("status") == "doing":
            status = "[blue]Doing[/blue]"
        elif task.get("status") == "cancelled":
            status = "[yellow]Cancelled[/yellow]"
        elif task.get("completed"):
            status = "[green]Complete[/green]"
        else:
            status = "[cyan]Pending[/cyan]"
        note_count = len(task.get("notes", []))
        notes_text = f"[dim]{note_count} note{'s' if note_count != 1 else ''}[/dim]"
        type_color = TASK_TYPE_COLORS[task["type"]]
        tags_text = ", ".join(tags_list) if tags_list else "-"
        table.add_row(
            task["task_id"],
            Text(task["type"], style=type_color),
            Text(task["title"], style="bold"),
            Text(task["priority"], style="yellow" if task["priority"] == "high" else "white"),
            Text(due_date_str, style="red" if due_date_str.startswith("Overdue") else "white"),
            total_time,
            status,
            notes_text,
            tags_text,
        )
    console.print(table)


@app.command()
def show(task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)")):
    """
    Show detailed information about a specific task.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)

    Example:
        todo show PROJ-001
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return

    # Create a panel to display task information
    console.print(
        f"\n[bold]Working on:[/bold] {task['title']} ({task['task_id']})"
    )

    # Type and Priority
    type_color = TASK_TYPE_COLORS[task["type"]]
    console.print(f"Type: [{type_color}]{task['type']}[/{type_color}]")
    if task.get("status") == "cancelled":
        console.print("[red]Status: Cancelled[/red]")
    elif task.get("completed"):
        console.print("[green]Status: Completed[/green]")
    else:
        console.print("[yellow]Status: Pending[/yellow]")
    priority_colors = {"high": "red", "medium": "yellow", "low": "blue"}
    priority = f"[{priority_colors[task['priority']]}]{task['priority']}[/{priority_colors[task['priority']]}]"
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

    # Repeat
    repeat = task.get("repeat")
    if repeat:
        console.print(f"\n[cyan]Repeat:[/cyan] {repeat}")

    # Tags
    tags_list = sorted(task.get("tags") or [])
    if tags_list:
        console.print(f"\n[bold]Tags:[/bold] {', '.join(tags_list)}")

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

    # Status History
    if task.get("status_history"):
        console.print("\n[bold]Status History:[/bold]")
        for entry in task["status_history"]:
            ts = parser.parse(entry["timestamp"]).strftime('%Y-%m-%d %H:%M')
            console.print(f"- {entry['status']} at [dim]{ts}[/dim]")

    # Created Date
    created_at = parser.parse(task["created_at"])
    console.print(f"\nCreated: {created_at.strftime('%Y-%m-%d %H:%M')}")


@app.command()
def complete(task_id: str):
    """
    Mark a task as complete by its task id.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)

    Example:
        todo complete PROJ-001
    """
    todos = load_todos()

    for task in todos["tasks"]:
        if task["task_id"].lower() == task_id.lower():
            task["completed"] = True
            save_todos(todos)
            console.print(
                f"[green]✓[/green] Task [bold]{task_id}[/bold] marked as complete!"
            )
            return

    console.print(f"[red]Error:[/red] Task with id [bold]{task_id}[/bold] not found!")


@app.command()
def cancel(task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)")):
    """
    Cancel a task by its task id (sets status to cancelled).
    """
    todos = load_todos()
    for task in todos["tasks"]:
        if task["task_id"].lower() == task_id.lower():
            task["status"] = "cancelled"
            save_todos(todos)
            console.print(f"[yellow]Task [bold]{task_id}[/bold] marked as cancelled.[/yellow]")
            return
    console.print(f"[red]Error:[/red] Task with id [bold]{task_id}[/bold] not found!")


@app.command()
def delete(task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)")):
    """
    Delete a task by its task id (completely removes it from the list).
    """
    todos = load_todos()
    initial_count = len(todos["tasks"])
    todos["tasks"] = [t for t in todos["tasks"] if t["task_id"].lower() != task_id.lower()]
    if len(todos["tasks"]) < initial_count:
        save_todos(todos)
        console.print(f"[red]Task [bold]{task_id}[/bold] deleted.[/red]")
    else:
        console.print(f"[red]Error:[/red] Task with id [bold]{task_id}[/bold] not found!")


@app.command()
def workon(
    task_id: str,
    duration: Optional[int] = typer.Option(
        25, "--duration", "-d", help="Duration in minutes"
    ),
):
    """
    Work on a specific task with an interactive timer.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
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
        if t["task_id"].lower() == task_id.lower():
            task = t
            break

    if not task:
        console.print(f"[red]Error:[/red] Task with id [bold]{task_id}[/bold] not found!")
        return

    # Initialize work_sessions if it doesn't exist
    if "work_sessions" not in task:
        task["work_sessions"] = []

    # Show task info
    console.print(f"\n[bold]Working on:[/bold] {task['title']} ({task['task_id']})")
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
                f"[cyan]Working on {task['task_id']}...",
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
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    text: Optional[str] = typer.Argument(
        None, help="Note text. If not provided, will prompt for input."
    ),
):
    """
    Add a new note to a task. Notes are stored as a chronological list.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        text: Note text (optional). If not provided, will prompt for input.

    Example:
        todo note add PROJ-001 "Remember to update documentation"
        todo note add PROJ-001  # Will prompt for note text
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
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
        console.print(f"[green]✓[/green] Added new note to task {task_id}")


@notes_app.command("reset")
def reset_notes(task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)")):
    """
    Reset (clear) all notes from a task.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)

    Example:
        todo note reset PROJ-001
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
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
        if task.get("completed"):
            stats["completed_tasks"] += 1
        elif task.get("status") == "cancelled":
            continue
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
            if task.get("completed"):
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

# Create a tag update sub-group under update
update_tag_app = typer.Typer(help="Add or remove tags from a task")
update_app.add_typer(update_tag_app, name="tag")


@update_tag_app.command("add")
def add_tag(
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    tag: str = typer.Argument(..., help="Tag to add")
):
    """
    Add a tag to a task.

    Example:
        todo update tag add PROJ-001 urgent
    """
    todos = load_todos()
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return
    tags = set(task.get("tags") or [])  # Ensure tags is always a set, even if None
    if tag in tags:
        console.print(f"[yellow]Task already has tag '{tag}'.[/yellow]")
        return
    tags.add(tag)
    # Always store tags as a non-empty list, or remove the field if empty
    task["tags"] = sorted(list(tags)) if tags else []
    save_todos(todos)
    console.print(f"[green]✓[/green] Tag '[bold]{tag}[/bold]' added to task [bold]{task_id}[/bold].")


@update_tag_app.command("remove")
def remove_tag(
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    tag: str = typer.Argument(..., help="Tag to remove")
):
    """
    Remove a tag from a task.

    Example:
        todo update tag remove PROJ-001 urgent
    """
    todos = load_todos()
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return
    tags = set(task.get("tags") or [])  # Ensure tags is always a set, even if None
    if tag not in tags:
        console.print(f"[yellow]Task does not have tag '{tag}'.[/yellow]")
        return
    tags.remove(tag)
    # Always store tags as a non-empty list, or remove the field if empty
    task["tags"] = sorted(list(tags)) if tags else []
    save_todos(todos)
    console.print(f"[green]✓[/green] Tag '[bold]{tag}[/bold]' removed from task [bold]{task_id}[/bold].")


@update_app.command("type")
def update_type(
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    new_type: Optional[str] = typer.Argument(
        None, help="New task type. If not provided, will prompt for input."
    ),
):
    """
    Update a task's type.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        new_type: New task type. If not provided, will prompt for input.

    Example:
        todo update type PROJ-001 feature
        todo update type PROJ-001  # Will prompt for type
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
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
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    new_priority: Optional[str] = typer.Argument(
        None, help="New priority. If not provided, will prompt for input."
    ),
):
    """
    Update a task's priority.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        new_priority: New priority. If not provided, will prompt for input.

    Example:
        todo update priority PROJ-001 high
        todo update priority PROJ-001  # Will prompt for priority
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
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
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    new_date: Optional[str] = typer.Argument(
        None, help="New due date. If not provided, will prompt for input."
    ),
):
    """
    Update a task's due date.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        new_date: New due date. If not provided, will prompt for input.
                 Use 'clear' to remove the due date.

    Example:
        todo update due PROJ-001 "next friday"
        todo update due PROJ-001 clear    # Remove due date
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return

    # Show current due date
    current_due = None
    if task.get("due_date"):
        current_due = datetime.fromisoformat(task["due_date"])
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
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    new_title: Optional[str] = typer.Argument(
        None, help="New title. If not provided, will prompt for input."
    ),
):
    """
    Update a task's title.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        new_title: New title. If not provided, will prompt for input.

    Example:
        todo update title PROJ-001 "New task title"
        todo update title PROJ-001  # Will prompt for title
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
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
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    new_description: Optional[str] = typer.Argument(
        None, help="New description. If not provided, will prompt for input."
    ),
):
    """
    Update a task's description.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        new_description: New description. If not provided, will prompt for input.

    Example:
        todo update description PROJ-001 "New task description"
        todo update description PROJ-001  # Will prompt for description
    """
    todos = load_todos()

    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
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


@update_app.command("status")
def update_status(
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    new_status: Optional[str] = typer.Argument(
        None, help="New status. If not provided, will prompt for input."
    ),
):
    """
    Update a task's status and track status changes.

    Arguments:
        task_id: The task id (e.g., PROJ-001, case-insensitive)
        new_status: New status. If not provided, will prompt for input.

    Example:
        todo update status PROJ-001 doing
        todo update status PROJ-001  # Will prompt for status
    """
    todos = load_todos()
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return
    valid_statuses = ["pending", "doing", "completed", "cancelled"]
    current_status = task.get("status", "pending")
    console.print(f"\nCurrent status: {current_status}")
    if new_status is None:
        new_status = Prompt.ask("New status", choices=valid_statuses, default=current_status)
    elif new_status not in valid_statuses:
        console.print(f"[red]Error:[/red] Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return
    if new_status == current_status:
        console.print(f"[yellow]No change: Status is already '{current_status}'.[/yellow]")
        return
    # Update the status
    task["status"] = new_status
    if "status_history" not in task:
        task["status_history"] = []
    task["status_history"].append({"status": new_status, "timestamp": datetime.now().isoformat()})
    # Optionally sync completed/cancelled fields
    if new_status == "completed":
        task["completed"] = True
        # Auto-reschedule if repeatable
        repeat_rule = task.get("repeat")
        if repeat_rule:
            # Parse the repeat rule as a time delta
            last_due = parser.parse(task["due_date"]) if task.get("due_date") else datetime.now()
            next_due = dateparser.parse(repeat_rule, settings={"RELATIVE_BASE": last_due})
            if next_due:
                task["due_date"] = next_due.isoformat()
                task["completed"] = False
                task["status"] = "pending"
                task["status_history"].append({"status": "pending", "timestamp": datetime.now().isoformat(), "auto_repeat": True})
                console.print(f"[cyan]Task is repeatable. Next due date set to {next_due.strftime('%Y-%m-%d')}.[/cyan]")
            else:
                console.print("[yellow]Warning: Could not parse repeat rule for next due date. Please check the repeat value.[/yellow]")
        else:
            console.print("[yellow]Warning: Task is not repeatable. Please set a repeat rule to enable auto-rescheduling.[/yellow]")
    elif new_status == "cancelled":
        task["completed"] = False
    save_todos(todos)
    console.print(f"[green]✓[/green] Updated task status to: {new_status}")


@update_app.command("repeat")
def update_repeat(
    task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)"),
    repeat: Optional[str] = typer.Argument(None, help="Repeat rule in natural language (e.g., every week)"),
):
    """
    Update a task's repeatability (e.g., every day, every week).
    """
    todos = load_todos()
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return
    current_repeat = task.get("repeat", None)
    console.print(f"\nCurrent repeat: {current_repeat if current_repeat else '[none]'}")
    if repeat is None:
        repeat = Prompt.ask("New repeat rule (e.g., every week, leave blank for none)", default=current_repeat or "")
    task["repeat"] = repeat if repeat else None
    save_todos(todos)
    console.print(f"[green]✓[/green] Updated repeat rule to: {repeat if repeat else '[none]'}")


@app.command()
def search(query: str = typer.Argument(..., help="Search query (matches title, description, or notes)")):
    """
    Search tasks by title, description, or notes and list relevant tasks.
    The search is case-insensitive and matches substrings.
    Displays results in the same table format as the list command.
    """
    todos = load_todos()
    query_lower = query.lower()
    matched_tasks = []
    for task in todos["tasks"]:
        if (
            query_lower in (task.get("title") or "").lower()
            or query_lower in (task.get("description") or "").lower()
            or any(query_lower in (note or "").lower() for note in task.get("notes", []))
        ):
            matched_tasks.append(task)
    if not matched_tasks:
        console.print(f"[yellow]No tasks found matching '{query}'.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Task ID")
    table.add_column("Type")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Due Date")
    table.add_column("Time Worked")
    table.add_column("Status")
    table.add_column("Notes")
    table.add_column("Tags")

    for task in matched_tasks:
        # Ensure tags are sorted for display consistency
        tags_list = sorted(task.get("tags") or [])
        due_date_str = format_due_date(parser.parse(task["due_date"])) if task.get("due_date") else "-"
        total_time = format_duration(sum(ws["duration"] for ws in task.get("work_sessions", [])))
        # Improved status display
        if task.get("status") == "doing":
            status = "[blue]Doing[/blue]"
        elif task.get("status") == "cancelled":
            status = "[yellow]Cancelled[/yellow]"
        elif task.get("completed"):
            status = "[green]Complete[/green]"
        else:
            status = "[cyan]Pending[/cyan]"
        note_count = len(task.get("notes", []))
        notes_text = f"[dim]{note_count} note{'s' if note_count != 1 else ''}[/dim]"
        type_color = TASK_TYPE_COLORS[task["type"]]
        tags_text = ", ".join(tags_list) if tags_list else "-"
        table.add_row(
            task["task_id"],
            Text(task["type"], style=type_color),
            Text(task["title"], style="bold"),
            Text(task["priority"], style="yellow" if task["priority"] == "high" else "white"),
            Text(due_date_str, style="red" if due_date_str.startswith("Overdue") else "white"),
            total_time,
            status,
            notes_text,
            tags_text,
        )
    console.print(table)


@app.command()
def version():
    """
    Show the version of the current CLI.
    """
    try:
        from importlib.metadata import version as pkg_version
    except ImportError:
        from importlib_metadata import version as pkg_version  # For Python <3.8

    try:
        ver = pkg_version("flowistic-todo")
        console.print(f"[bold green]Todo CLI version:[/bold green] {ver}")
    except Exception as e:
        console.print(f"[red]Could not determine version: {e}[/red]")


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
        ("list", "List all pending tasks with project information"),
        ("show <task_id>", "Show detailed information about a specific task"),
        ("status", "Show detailed project status and statistics"),
        ("complete <task_id>", "Mark a task as complete using its task id (e.g., PROJ-001)"),
        ("workon <task_id>", "Work on a specific task for a given duration (default: 25 minutes)"),
        ("note add <task_id>", "Add a new note to a task"),
        ("note reset <task_id>", "Reset (clear) all notes from a task"),
        ("update type <task_id>", "Update a task's type"),
        ("update priority <task_id>", "Update a task's priority"),
        ("update due <task_id>", "Update a task's due date"),
        ("update title <task_id>", "Update a task's title"),
        ("update description <task_id>", "Update a task's description"),
        ("update status <task_id>", "Update a task's status"),
        ("update repeat <task_id>", "Update a task's repeatability"),
        ("update tag add <task_id>", "Add a tag to a task"),
        ("update tag remove <task_id>", "Remove a tag from a task"),
        ("cancel <task_id>", "Cancel a task by its task id (sets status to cancelled)"),
        ("delete <task_id>", "Delete a task by its task id (completely removes it from the list)"),
        ("tags", "List all unique tags across all tasks, along with the number of tasks for each tag"),
        ("tag <tag>", "List all tasks associated with a given tag"),
        ("version", "Show the version of the current CLI"),
        ("search <query>", "Search tasks by title, description, or notes"),
        ("board", "Launch a Dash web app with a Trello-like board showing all tasks grouped by status"),
        ("evolve <task_id>", "Move a task to the next workflow status"),
        ("checklist add <item>", "Add a new checklist item"),
        ("checklist list", "List all checklist items and their status"),
        ("checklist check <index>", "Mark a checklist item as checked"),
        ("checklist uncheck <index>", "Mark a checklist item as unchecked"),
        ("checklist remove <index>", "Remove a checklist item by its number"),
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


@app.command()
def board():
    """
    Launch a Dash web app with a Trello-like board showing all tasks grouped by status.
    """
    todos = load_todos()["tasks"]
    launch_board(todos)


@app.command()
def evolve(task_id: str = typer.Argument(..., help="The task id (e.g., PROJ-001)")):
    """
    Move a task to the next workflow status.

    Workflow order: pending -> doing -> completed -> cancelled
    If already at the last status, stays there.

    Example:
        todo evolve PROJ-001
    """
    todos = load_todos()
    workflow = ["pending", "doing", "completed", "cancelled"]
    # Find the task
    task = next((t for t in todos["tasks"] if t["task_id"].lower() == task_id.lower()), None)
    if not task:
        console.print(f"[red]Error:[/red] Task '{task_id}' not found!")
        return
    current_status = task.get("status", "pending")
    try:
        idx = workflow.index(current_status)
        if idx < len(workflow) - 1:
            new_status = workflow[idx+1]
            task["status"] = new_status
            if new_status == "completed":
                task["completed"] = True
            elif new_status == "pending":
                task["completed"] = False
            if "status_history" not in task:
                task["status_history"] = []
            task["status_history"].append({"status": new_status, "timestamp": datetime.now().isoformat()})
            save_todos(todos)
            console.print(f"[green]✓[/green] Task [bold]{task_id}[/bold] moved to status: [cyan]{new_status}[/cyan]")
        else:
            console.print(f"[yellow]Task [bold]{task_id}[/bold] is already at the last status: [cyan]{current_status}[/cyan]")
    except ValueError:
        console.print(f"[red]Error:[/red] Unknown status '{current_status}' for task '{task_id}'.")


# --- CHECKLIST COMMAND GROUP ---
checklist_app = typer.Typer(help="Manage checklists (create, list, check, uncheck, remove items)")
app.add_typer(checklist_app, name="checklist")

@checklist_app.command("add")
def checklist_add(item: str = typer.Argument(..., help="Checklist item text")):
    """
    Add a new item to the checklist.
    """
    todos = load_todos()
    if "checklist" not in todos:
        todos["checklist"] = []
    todos["checklist"].append({"item": item, "checked": False})
    save_todos(todos)
    console.print(f"[green]✓[/green] Checklist item added: [bold]{item}[/bold]")

@checklist_app.command("list")
def checklist_list():
    """
    List all checklist items with their status.
    """
    todos = load_todos()
    checklist = todos.get("checklist", [])
    if not checklist:
        console.print("[yellow]No checklist items found.[/yellow]")
        return
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Status", width=8)
    table.add_column("Item")
    for idx, entry in enumerate(checklist, 1):
        status = "[green]✔[/green]" if entry.get("checked") else "[red]✗[/red]"
        table.add_row(str(idx), status, entry.get("item", ""))
    console.print(table)

@checklist_app.command("check")
def checklist_check(index: int = typer.Argument(..., help="Checklist item number (see checklist list)")):
    """
    Mark a checklist item as checked (completed).
    """
    todos = load_todos()
    checklist = todos.get("checklist", [])
    if not (1 <= index <= len(checklist)):
        console.print(f"[red]Invalid index:[/red] {index}")
        return
    checklist[index-1]["checked"] = True
    save_todos(todos)
    console.print(f"[green]✓[/green] Checked item #{index}: [bold]{checklist[index-1]['item']}[/bold]")

@checklist_app.command("uncheck")
def checklist_uncheck(index: int = typer.Argument(..., help="Checklist item number (see checklist list)")):
    """
    Mark a checklist item as unchecked (not completed).
    """
    todos = load_todos()
    checklist = todos.get("checklist", [])
    if not (1 <= index <= len(checklist)):
        console.print(f"[red]Invalid index:[/red] {index}")
        return
    checklist[index-1]["checked"] = False
    save_todos(todos)
    console.print(f"[yellow]Unchecked item #{index}: [bold]{checklist[index-1]['item']}[/bold]")

@checklist_app.command("remove")
def checklist_remove(index: int = typer.Argument(..., help="Checklist item number (see checklist list)")):
    """
    Remove a checklist item by its number.
    """
    todos = load_todos()
    checklist = todos.get("checklist", [])
    if not (1 <= index <= len(checklist)):
        console.print(f"[red]Invalid index:[/red] {index}")
        return
    removed = checklist.pop(index-1)
    save_todos(todos)
    console.print(f"[red]Removed item #{index}: [bold]{removed['item']}[/bold]")


@checklist_app.command("export")
def checklist_export(
    filename: str = typer.Argument(..., help="Output filename (e.g., checklist.xlsx or checklist.html)"),
    html: bool = typer.Option(False, "--html", help="Export as interactive HTML instead of Excel")
):
    """
    Export the checklist to an Excel file (default) or interactive HTML page (--html).
    Both formats display checkboxes for item status.
    """
    todos = load_todos()
    checklist = todos.get("checklist", [])
    if not checklist:
        console.print("[yellow]No checklist items to export.[/yellow]")
        return
    df = pd.DataFrame(checklist)
    df.index += 1
    df.index.name = "#"
    # For Excel: use Unicode checkboxes
    df["Status"] = df["checked"].map(lambda x: "☑" if x else "☐")
    df.rename(columns={"item": "Item"}, inplace=True)
    if html:
        # For HTML: use real checkboxes
        def html_checkbox(val, idx):
            checked = " checked" if val else ""
            return f'<input type="checkbox" class="todo-checkbox" data-idx="{idx}"{checked}>'
        rows = []
        for idx, row in df.iterrows():
            is_checked = row["checked"]
            tr_class = "checked-row" if is_checked else ""
            item_html = row["Item"]
            checkbox_html = html_checkbox(is_checked, idx)
            rows.append(f'<tr class="{tr_class}"><th>{idx+1}</th><td>{item_html}</td><td>{checkbox_html}</td></tr>')
        table_html = '''<table class="dataframe sortable">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Item</th>
      <th>Status</th>
    </tr>
    <tr>
      <th>#</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
''' + "\n".join(rows) + '''
  </tbody>
</table>'''
        html_template = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<title>Checklist Export</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f9f9f9; }}
table.sortable {{ border-collapse: collapse; width: 70%; margin: 2em auto; background: #fff; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }}
table.sortable th, table.sortable td {{ border: 1px solid #e2e8f0; padding: 0.7em 1em; text-align: left; }}
table.sortable th {{ background: #f4f4f4; cursor: pointer; }}
table.sortable tr:nth-child(even) {{ background: #f7fafc; }}
table.sortable tr:hover {{ background: #e6fffa; }}
input[type=checkbox] {{ width: 1.2em; height: 1.2em; accent-color: #38a169; }}
.checked-row td, .checked-row th {{ background: #e6ffe6 !important; color: #4a7c59; text-decoration: line-through; }}
</style>
<script>
function sortTable(n) {{
  var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
  table = document.querySelector("table.sortable");
  switching = true;
  dir = "asc";
  while (switching) {{
    switching = false;
    rows = table.rows;
    for (i = 1; i < (rows.length - 1); i++) {{
      shouldSwitch = false;
      x = rows[i].getElementsByTagName("TD")[n];
      y = rows[i + 1].getElementsByTagName("TD")[n];
      if (dir == "asc") {{
        if (x.innerText.toLowerCase() > y.innerText.toLowerCase()) {{
          shouldSwitch = true;
          break;
        }}
      }} else if (dir == "desc") {{
        if (x.innerText.toLowerCase() < y.innerText.toLowerCase()) {{
          shouldSwitch = true;
          break;
        }}
      }}
    }}
    if (shouldSwitch) {{
      rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
      switching = true;
      switchcount ++;
    }} else {{
      if (switchcount == 0 && dir == "asc") {{
        dir = "desc";
        switching = true;
      }}
    }}
  }}
}}
document.addEventListener("DOMContentLoaded", function() {{
  var ths = document.querySelectorAll("table.sortable th");
  ths.forEach(function(th, idx) {{
    th.addEventListener("click", function() {{ sortTable(idx); }});
  }});
  // Checkbox interactivity & persistence
  var checkboxes = document.querySelectorAll('.todo-checkbox');
  checkboxes.forEach(function(cb, idx) {{
    var row = cb.closest('tr');
    var saved = localStorage.getItem('todo-checkbox-' + idx);
    if (saved !== null) {{
      cb.checked = saved === 'true';
    }}
    // Set initial row highlight
    if(cb.checked) {{
      row.classList.add('checked-row');
    }} else {{
      row.classList.remove('checked-row');
    }}
    cb.addEventListener('change', function() {{
      localStorage.setItem('todo-checkbox-' + idx, cb.checked);
      if(cb.checked) {{
        row.classList.add('checked-row');
      }} else {{
        row.classList.remove('checked-row');
      }}
    }});
  }});
}});
</script>
</head>
<body>
<h2 style='text-align:center;margin-top:2em;'>Checklist Export</h2>
{table_html}
<p style='text-align:center;color:#888;'>Exported from Flowistic Todo CLI</p>
</body>
</html>
"""
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html_template)
            console.print(f"[green]✓[/green] Checklist exported to [bold]{filename}[/bold] (HTML)")
        except Exception as e:
            console.print(f"[red]Error exporting to HTML:[/red] {e}")
    else:
        try:
            df[["Item", "Status"]].to_excel(filename)
            console.print(f"[green]✓[/green] Checklist exported to [bold]{filename}[/bold] (Excel)")
        except Exception as e:
            console.print(f"[red]Error exporting to Excel:[/red] {e}")


if __name__ == "__main__":
    app()
