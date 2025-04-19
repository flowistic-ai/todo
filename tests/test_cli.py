import os
import shutil
import tempfile
from pathlib import Path
import pytest
import yaml
from todo.cli import get_todo_file, load_todos, save_todos

@pytest.fixture
def temp_todo_dir(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(temp_dir)
    monkeypatch.setattr("todo.cli.TODO_FILE", Path("todo.yaml"))
    yield temp_dir
    os.chdir(cwd)
    shutil.rmtree(temp_dir)

def test_get_todo_file_creates_local(temp_todo_dir):
    todo_file = get_todo_file()
    assert todo_file == Path("todo.yaml")
    assert not todo_file.exists()

def test_load_todos_empty(temp_todo_dir):
    todos = load_todos()
    assert "project" in todos
    assert "tasks" in todos
    assert todos["tasks"] == []

def test_save_and_load_todos(temp_todo_dir):
    data = {
        "project": {"name": "TestProj", "description": "desc", "prefix": "TP", "next_task_number": 2},
        "tasks": [
            {"tag": "TP-001", "title": "Test", "description": "desc", "type": "feature", "priority": "high", "created_at": "2025-01-01T00:00:00", "due_date": None, "completed": False, "work_sessions": [], "notes": []}
        ]
    }
    save_todos(data)
    loaded = load_todos()
    assert loaded == data
