import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import yaml
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, date
import os
from rich.style import Style
import dateparser

app = typer.Typer()
console = Console()

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
    if not TODO_FILE.exists():
        return {
            "project": {
                "name": "",
                "description": "",
                "prefix": "",
                "next_task_number": 1
            },
            "tasks": []
        }
    with open(TODO_FILE, "r") as f:
        return yaml.safe_load(f) or {
            "project": {
                "name": "",
                "description": "",
                "prefix": "",
                "next_task_number": 1
            },
            "tasks": []
        }

def save_todos(todos: Dict):
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
        return f"[red]Overdue by {abs(days_until)} days[/red]"
    elif days_until == 0:
        return "[yellow]Due today[/yellow]"
    elif days_until == 1:
        return "[yellow]Due tomorrow[/yellow]"
    else:
        return f"[green]Due in {days_until} days[/green]"

@app.command()
def init():
    """Initialize a new todo list with project details"""
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
            "next_task_number": 1
        },
        "tasks": []
    }
    save_todos(todos)
    console.print("[green]✓[/green] Initialized new todo list!")
    console.print(f"Project: [bold]{project_name}[/bold]")
    console.print(f"Description: {project_description}")
    console.print(f"Todo file location: {TODO_FILE}")

@app.command()
def add():
    """Add a new task interactively"""
    todos = load_todos()
    
    if not todos["project"]["prefix"]:
        console.print("[red]Error:[/red] Project not initialized. Please run 'todo init' first.")
        return
    
    title = Prompt.ask("Task title")
    description = Prompt.ask("Description (optional)", default="")
    priority = Prompt.ask("Priority", choices=["low", "medium", "high"], default="medium")
    due_date_str = Prompt.ask(
        "Due date (optional, e.g., 'tomorrow', 'next friday', '2025-04-20')",
        default=""
    )
    
    due_date = parse_due_date(due_date_str)
    if due_date_str and not due_date:
        console.print("[yellow]Warning:[/yellow] Could not parse due date, task will be created without one.")
    
    # Generate task tag
    task_number = todos["project"]["next_task_number"]
    task_tag = f"{todos['project']['prefix']}-{task_number:03d}"
    todos["project"]["next_task_number"] += 1
    
    task = {
        "tag": task_tag,
        "title": title,
        "description": description,
        "priority": priority,
        "created_at": datetime.now().isoformat(),
        "due_date": due_date.isoformat() if due_date else None,
        "completed": False
    }
    
    todos["tasks"].append(task)
    save_todos(todos)
    console.print(f"[green]✓[/green] Task [bold]{task_tag}[/bold] added successfully!")

@app.command()
def list():
    """List all tasks with project information"""
    todos = load_todos()
    
    # Show project info
    if todos["project"]["name"]:
        console.print(f"\n[bold]Project:[/bold] {todos['project']['name']}")
        console.print(f"[bold]Description:[/bold] {todos['project']['description']}\n")
    
    if not todos["tasks"]:
        console.print("[yellow]No tasks found![/yellow]")
        return
    
    table = Table(show_header=True)
    table.add_column("Tag", style="bold")
    table.add_column("Title")
    table.add_column("Description")
    table.add_column("Priority", style="bold")
    table.add_column("Due Date", style="bold")
    table.add_column("Status")
    
    # Sort tasks by due date and completion status
    def sort_key(task):
        if "due_date" not in task:
            task["due_date"] = None
        due_date = datetime.fromisoformat(task["due_date"]) if task["due_date"] else datetime.max
        return (task["completed"], due_date)
    
    sorted_tasks = sorted(todos["tasks"], key=sort_key)
    
    for task in sorted_tasks:
        status = "[green]✓[/green]" if task["completed"] else "[red]✗[/red]"
        priority_color = {
            "low": "blue",
            "medium": "yellow",
            "high": "red"
        }[task["priority"]]
        
        due_date_str = format_due_date(
            datetime.fromisoformat(task.get("due_date")) if task.get("due_date") else None
        )
        
        table.add_row(
            task["tag"],
            task["title"],
            task["description"] or "-",
            f"[{priority_color}]{task['priority']}[/{priority_color}]",
            due_date_str,
            status
        )
    
    console.print(table)

@app.command()
def complete(tag: str):
    """Mark a task as complete by its tag"""
    todos = load_todos()
    
    for task in todos["tasks"]:
        if task["tag"].lower() == tag.lower():
            task["completed"] = True
            save_todos(todos)
            console.print(f"[green]✓[/green] Task [bold]{tag}[/bold] marked as complete!")
            return
    
    console.print(f"[red]Error:[/red] Task with tag [bold]{tag}[/bold] not found!")

@app.command()
def help():
    """Show all available commands and their descriptions"""
    console.print("\n[bold blue]Todo App Commands:[/bold blue]")
    
    commands = [
        ("init", "Initialize a new todo list with project details"),
        ("add", "Add a new task interactively"),
        ("list", "List all tasks with project information"),
        ("complete <tag>", "Mark a task as complete using its tag (e.g., PROJ-001)"),
        ("help", "Show this help message")
    ]
    
    table = Table(show_header=False, box=None)
    table.add_column("Command", style="green")
    table.add_column("Description")
    
    for cmd, desc in commands:
        table.add_row(f"todo {cmd}", desc)
    
    console.print(table)
    console.print("\n[dim]You can also use --help with any command for more details (e.g., todo add --help)[/dim]")

if __name__ == "__main__":
    app()
