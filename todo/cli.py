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
        for tag in task.get("tags", []):
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
    filtered = [t for t in todos["tasks"] if tag in t.get("tags", [])]
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
        tasks = [t for t in tasks if tag in t.get("tags", [])]

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
        due_date_str = format_due_date(parser.parse(task["due_date"])) if task.get("due_date") else "-"
        total_time = format_duration(sum(ws["duration"] for ws in task.get("work_sessions", [])))
        status = (
            "[green]Complete[/green]" if task.get("completed") else
            "[yellow]Cancelled[/yellow]" if task.get("status") == "cancelled" else
            "[cyan]Pending[/cyan]"
        )
        note_count = len(task.get("notes", []))
        notes_text = f"[dim]{note_count} note{'s' if note_count != 1 else ''}[/dim]"
        type_color = TASK_TYPE_COLORS[task["type"]]
        tags_text = ", ".join(task.get("tags", [])) if task.get("tags") else "-"
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
        f"\n[bold blue]{task['task_id']}[/bold blue]: [bold]{task['title']}[/bold]"
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
        due_date_str = format_due_date(parser.parse(task["due_date"])) if task.get("due_date") else "-"
        total_time = format_duration(sum(ws["duration"] for ws in task.get("work_sessions", [])))
        status = (
            "[green]Complete[/green]" if task.get("completed") else
            "[yellow]Cancelled[/yellow]" if task.get("status") == "cancelled" else
            "[cyan]Pending[/cyan]"
        )
        note_count = len(task.get("notes", []))
        notes_text = f"[dim]{note_count} note{'s' if note_count != 1 else ''}[/dim]"
        type_color = TASK_TYPE_COLORS[task["type"]]
        tags_text = ", ".join(task.get("tags", [])) if task.get("tags") else "-"
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
    Show the version of the current CLI (dynamically retrieved from pyproject.toml).
    """
    import toml
    from pathlib import Path
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    if not pyproject_path.exists():
        console.print("[red]pyproject.toml not found![/red]")
        return
    try:
        data = toml.load(pyproject_path)
        version = (
            data.get("project", {}).get("version") or
            data.get("tool", {}).get("poetry", {}).get("version")
        )
        if version:
            console.print(f"[bold green]Todo CLI version:[/bold green] {version}")
        else:
            console.print("[red]Version not found in pyproject.toml[/red]")
    except Exception as e:
        console.print(f"[red]Error reading pyproject.toml:[/red] {e}")


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
        ("cancel <task_id>", "Cancel a task by its task id (sets status to cancelled)"),
        ("delete <task_id>", "Delete a task by its task id (completely removes it from the list)"),
        ("tags", "List all unique tags across all tasks, along with the number of tasks for each tag"),
        ("tag <tag>", "List all tasks associated with a given tag"),
        ("version", "Show the version of the current CLI"),
        ("search <query>", "Search tasks by title, description, or notes"),
        ("board", "Launch a Dash web app with a Trello-like board showing all tasks grouped by status"),
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


# Create an update command group
update_app = typer.Typer(help="Update task properties")
app.add_typer(update_app, name="update")


if __name__ == "__main__":
    app()
