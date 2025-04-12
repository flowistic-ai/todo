import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
import yaml
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

app = typer.Typer()
console = Console()

TODO_FILE = Path("todo.yaml")

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
    with open(TODO_FILE, "w") as f:
        yaml.dump(todos, f, sort_keys=False)

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

@app.command()
def add():
    """Add a new task interactively"""
    todos = load_todos()
    
    if not todos["project"]["prefix"]:
        console.print("[red]Error:[/red] Project not initialized. Please run 'init' first.")
        return
    
    title = Prompt.ask("Task title")
    description = Prompt.ask("Description (optional)", default="")
    priority = Prompt.ask("Priority", choices=["low", "medium", "high"], default="medium")
    
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
        "completed": False
    }
    
    todos["tasks"].append(task)
    save_todos(todos)
    console.print(f"[green]✓[/green] Task [bold]{task_tag}[/bold] added successfully!")

@app.command()
def list():
    """List all tasks"""
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
    table.add_column("Status")
    
    for task in todos["tasks"]:
        status = "[green]✓[/green]" if task["completed"] else "[red]✗[/red]"
        priority_color = {
            "low": "blue",
            "medium": "yellow",
            "high": "red"
        }[task["priority"]]
        
        table.add_row(
            task["tag"],
            task["title"],
            task["description"] or "-",
            f"[{priority_color}]{task['priority']}[/{priority_color}]",
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
        table.add_row(f"todo.py {cmd}", desc)
    
    console.print(table)
    console.print("\n[dim]You can also use --help with any command for more details (e.g., todo.py add --help)[/dim]")

if __name__ == "__main__":
    app()