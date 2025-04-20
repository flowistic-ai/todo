import os
import tempfile
import shutil
from pathlib import Path
import pytest
from typer.testing import CliRunner
from todo.cli import app, TODO_FILE

runner = CliRunner()

@pytest.fixture(autouse=True)
def temp_todo_dir(monkeypatch):
    temp_dir = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(temp_dir)
    monkeypatch.setattr("todo.cli.TODO_FILE", Path("todo.yaml"))
    yield temp_dir
    os.chdir(cwd)
    shutil.rmtree(temp_dir)

def test_init_command():
    result = runner.invoke(app, ["init"], input="TestProj\nA project\nTP\ny\n")
    assert result.exit_code == 0
    assert TODO_FILE.exists()
    with open(TODO_FILE) as f:
        content = f.read()
    assert "TestProj" in content
    assert "A project" in content
    assert "TP" in content

def test_add_and_list_commands():
    runner.invoke(app, ["init"], input="Proj\nDesc\nPX\ny\n")
    result = runner.invoke(app, ["add"], input="Test Task\nTest desc\nfeature\nhigh\n\n\n")
    assert result.exit_code == 0
    assert "added successfully" in result.output
    list_result = runner.invoke(app, ["list"])
    assert "Test Task" in list_result.output
    assert "PX-001" in list_result.output

def test_complete_command():
    runner.invoke(app, ["init"], input="Proj\nDesc\nPX\ny\n")
    runner.invoke(app, ["add"], input="Task\nDesc\nfeature\nhigh\n\n\n")
    result = runner.invoke(app, ["complete", "PX-001"])
    assert result.exit_code == 0
    assert "marked as complete" in result.output

def test_show_command():
    runner.invoke(app, ["init"], input="Proj\nDesc\nPX\ny\n")
    runner.invoke(app, ["add"], input="Show Task\nDesc\ndocs\nlow\n\n\n")
    result = runner.invoke(app, ["show", "PX-001"])
    assert result.exit_code == 0
    assert "Show Task" in result.output
    assert "PX-001" in result.output

def test_cancel_command():
    runner.invoke(app, ["init"], input="Proj\nDesc\nPX\ny\n")
    runner.invoke(app, ["add"], input="Cancel Task\nDesc\nfeature\nhigh\n\n\n")
    result = runner.invoke(app, ["cancel", "PX-001"])
    assert result.exit_code == 0
    assert "marked as cancelled" in result.output
    # Show should display status cancelled
    show_result = runner.invoke(app, ["show", "PX-001"])
    assert "Status: Cancelled" in show_result.output
    # List should show cancelled status
    list_result = runner.invoke(app, ["list"])
    assert "Cancelled" in list_result.output

def test_delete_command():
    runner.invoke(app, ["init"], input="Proj\nDesc\nPX\ny\n")
    runner.invoke(app, ["add"], input="Delete Task\nDesc\nfeature\nhigh\n\n\n")
    # Confirm task exists
    list_result = runner.invoke(app, ["list"])
    assert "Delete Task" in list_result.output
    # Delete the task
    result = runner.invoke(app, ["delete", "PX-001"])
    assert result.exit_code == 0
    assert "deleted" in result.output
    # Task should no longer appear
    list_result = runner.invoke(app, ["list"])
    assert "Delete Task" not in list_result.output
    # Show should error
    show_result = runner.invoke(app, ["show", "PX-001"])
    assert "not found" in show_result.output
