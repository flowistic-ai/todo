import os
import shutil
import tempfile
from pathlib import Path

import pytest

from todo.cli import get_todo_file, load_todos, save_todos


@pytest.fixture
def temp_todo_dir(monkeypatch):
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(temp_dir)
    monkeypatch.setattr("todo.cli.TODO_FILE", Path("todo.yaml"))
    yield temp_dir
    os.chdir(cwd)
    shutil.rmtree(temp_dir)

def test_get_todo_file_creates_local(temp_todo_dir):
    """Test that get_todo_file creates a local todo file if it doesn't exist"""
    todo_file = get_todo_file()
    assert todo_file == Path("todo.yaml")
    assert not todo_file.exists()

def test_load_todos_empty(temp_todo_dir):
    """Test that load_todos returns an empty dictionary if the todo file doesn't exist"""
    todos = load_todos()
    assert "project" in todos
    assert "tasks" in todos
    assert todos["tasks"] == []

def test_save_and_load_todos(temp_todo_dir):
    """Test that save_todos and load_todos work correctly"""
    data = {
        "project": {"name": "TestProj", "description": "desc", "prefix": "TP", "next_task_number": 2},
        "tasks": [
            {"tag": "TP-001", "title": "Test", "description": "desc", "type": "feature", "priority": "high", "created_at": "2025-01-01T00:00:00", "due_date": None, "completed": False, "work_sessions": [], "notes": []}
        ]
    }
    save_todos(data)
    loaded = load_todos()
    assert loaded == data

def test_load_todos_with_existing_file(temp_todo_dir):
    """Test that load_todos works correctly with an existing todo file"""
    # Create a todo.yaml with minimal valid content
    with open("todo.yaml", "w") as f:
        f.write("""
project:
  name: ExistingProj
  description: ExistingDesc
  prefix: EX
  next_task_number: 5
tasks:
  - tag: EX-001
    title: Existing Task
    description: Some desc
    type: bugfix
    priority: low
    created_at: 2025-01-01T00:00:00
    due_date: null
    completed: false
    work_sessions: []
    notes: []
""")
    todos = load_todos()
    assert todos["project"]["name"] == "ExistingProj"
    assert len(todos["tasks"]) == 1
    assert todos["tasks"][0]["tag"] == "EX-001"

def test_save_todos_overwrites_file(temp_todo_dir):
    """Test that save_todos overwrites the todo file with new data"""
    # Save initial data
    data1 = {"project": {"name": "A", "description": "B", "prefix": "X", "next_task_number": 1}, "tasks": []}
    save_todos(data1)
    # Overwrite with new data
    data2 = {"project": {"name": "C", "description": "D", "prefix": "Y", "next_task_number": 2}, "tasks": []}
    save_todos(data2)
    loaded = load_todos()
    assert loaded["project"]["name"] == "C"
    assert loaded["project"]["prefix"] == "Y"

def test_load_todos_with_missing_fields(temp_todo_dir):
    """Test that load_todos works correctly with a todo file missing 'tasks' field"""
    # Write a file missing 'tasks' field
    with open("todo.yaml", "w") as f:
        f.write("project:\n  name: Oops\n  description: Oops\n  prefix: O\n  next_task_number: 1\n")
    todos = load_todos()
    assert "tasks" in todos
    assert isinstance(todos["tasks"], list)

def test_save_and_load_empty_todos(temp_todo_dir):
    """Test that save_todos and load_todos work correctly with empty data"""
    data = {"project": {"name": "", "description": "", "prefix": "", "next_task_number": 1}, "tasks": []}
    save_todos(data)
    loaded = load_todos()
    assert loaded["project"]["name"] == ""
    assert loaded["tasks"] == []
