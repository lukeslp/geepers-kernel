#!/usr/bin/env python3
"""
Todoist CLI - Command-line interface for Todoist task management.

Author: Luke Steuber

Usage:
    todoist tasks                    # List all tasks
    todoist tasks -p "Work"          # Filter by project
    todoist projects                 # List projects
    todoist add "Buy groceries"      # Add task
    todoist add "Meeting" -d "tomorrow 3pm" -p 4  # With due date and priority
    todoist complete <task_id>       # Complete task
    todoist delete <task_id>         # Delete task
"""

import argparse
import os
import sys
from datetime import datetime
from typing import Optional

# Try to import the official SDK
try:
    from todoist_api_python.api import TodoistAPI
except ImportError:
    print("Error: The 'todoist-api-python' library is required.")
    print("Please install it using: pip install todoist-api-python")
    sys.exit(1)


def get_api_key() -> str:
    """
    Get Todoist API key from environment variable.

    Returns:
        str: The API key

    Raises:
        SystemExit: If API key is not found
    """
    api_key = os.environ.get('TODOIST_API_KEY')

    if not api_key:
        print("Error: TODOIST_API_KEY environment variable not set.")
        print("Set it with: export TODOIST_API_KEY='your-api-key'")
        print("Or add to ~/.bashrc for persistence.")
        sys.exit(1)

    return api_key


def get_api() -> TodoistAPI:
    """Initialize and return the Todoist API client."""
    return TodoistAPI(get_api_key())


def format_priority(priority: int) -> str:
    """
    Format priority for display.

    Note: Todoist API uses 4 for highest priority (P1 in UI),
    and 1 for normal/lowest priority (P4 in UI).
    """
    mapping = {4: "P1 (High)", 3: "P2", 2: "P3", 1: "P4 (Normal)"}
    return mapping.get(priority, "P4")


def format_task_row(task_id: str, priority: str, due: str, content: str) -> str:
    """Format a task as a table row."""
    return f"{task_id:<20} | {priority:<12} | {due:<15} | {content}"


def get_project_id_by_name(api: TodoistAPI, project_name: str) -> Optional[str]:
    """Look up project ID by name (case-insensitive)."""
    for page in api.get_projects():
        for proj in page:
            if proj.name.lower() == project_name.lower():
                return proj.id
    return None


def list_tasks(args: argparse.Namespace) -> None:
    """List active tasks with optional project filter."""
    api = get_api()
    try:
        # Build filter parameters
        task_params = {}

        if args.project:
            # Look up project ID by name
            project_id = get_project_id_by_name(api, args.project)
            if project_id:
                task_params['project_id'] = project_id
            else:
                print(f"Warning: Project '{args.project}' not found. Showing all tasks.")

        # Collect all tasks from paginated results
        all_tasks = []
        for page in api.get_tasks(**task_params):
            all_tasks.extend(page)

        if not all_tasks:
            print("No active tasks found.")
            return

        # Print header
        print(format_task_row("ID", "Priority", "Due", "Content"))
        print("-" * 80)

        for task in all_tasks:
            due_str = task.due.string if task.due else "No Date"
            prio = format_priority(task.priority)
            print(format_task_row(task.id, prio, due_str, task.content))

    except Exception as e:
        print(f"Error fetching tasks: {e}")
        sys.exit(1)


def add_task(args: argparse.Namespace) -> None:
    """Create a new task."""
    api = get_api()
    try:
        # Build task parameters
        task_params = {
            'content': args.content,
            'priority': args.priority,
        }

        if args.due:
            task_params['due_string'] = args.due

        if args.project_id:
            task_params['project_id'] = args.project_id

        task = api.add_task(**task_params)

        print(f"Task created successfully!")
        print(f"  ID: {task.id}")
        print(f"  Content: {task.content}")
        if task.due:
            print(f"  Due: {task.due.string}")
        print(f"  Priority: {format_priority(task.priority)}")

    except Exception as e:
        print(f"Error creating task: {e}")
        sys.exit(1)


def complete_task(args: argparse.Namespace) -> None:
    """Close/Complete a task by ID."""
    api = get_api()
    try:
        is_success = api.complete_task(task_id=args.task_id)
        if is_success:
            print(f"Task {args.task_id} marked as completed.")
        else:
            print(f"Error: Could not complete task {args.task_id}.")
            sys.exit(1)
    except Exception as e:
        print(f"Error completing task: {e}")
        sys.exit(1)


def delete_task(args: argparse.Namespace) -> None:
    """Delete a task by ID."""
    api = get_api()
    try:
        is_success = api.delete_task(task_id=args.task_id)
        if is_success:
            print(f"Task {args.task_id} deleted.")
        else:
            print(f"Error: Could not delete task {args.task_id}.")
            sys.exit(1)
    except Exception as e:
        print(f"Error deleting task: {e}")
        sys.exit(1)


def list_projects(args: argparse.Namespace) -> None:
    """List all projects."""
    api = get_api()
    try:
        # Collect all projects from paginated results
        all_projects = []
        for page in api.get_projects():
            all_projects.extend(page)

        if not all_projects:
            print("No projects found.")
            return

        print(f"{'ID':<20} | {'Name'}")
        print("-" * 45)
        for proj in all_projects:
            # Check for parent_id attribute (may vary by SDK version)
            has_parent = getattr(proj, 'parent_id', None) is not None
            indent = "  " if has_parent else ""
            print(f"{proj.id:<20} | {indent}{proj.name}")
    except Exception as e:
        print(f"Error fetching projects: {e}")
        sys.exit(1)


def get_task(args: argparse.Namespace) -> None:
    """Get details of a single task."""
    api = get_api()
    try:
        task = api.get_task(task_id=args.task_id)

        print(f"Task Details")
        print("-" * 40)
        print(f"  ID:          {task.id}")
        print(f"  Content:     {task.content}")
        print(f"  Priority:    {format_priority(task.priority)}")
        print(f"  Due:         {task.due.string if task.due else 'No date'}")
        print(f"  Created:     {task.created_at}")
        if task.description:
            print(f"  Description: {task.description}")
        if task.labels:
            print(f"  Labels:      {', '.join(task.labels)}")

    except Exception as e:
        print(f"Error fetching task: {e}")
        sys.exit(1)


def update_task(args: argparse.Namespace) -> None:
    """Update an existing task."""
    api = get_api()
    try:
        update_params = {}

        if args.content:
            update_params['content'] = args.content
        if args.due:
            update_params['due_string'] = args.due
        if args.priority:
            update_params['priority'] = args.priority

        if not update_params:
            print("Error: No updates specified. Use --content, --due, or --priority.")
            sys.exit(1)

        is_success = api.update_task(task_id=args.task_id, **update_params)

        if is_success:
            print(f"Task {args.task_id} updated successfully.")
        else:
            print(f"Error: Could not update task {args.task_id}.")
            sys.exit(1)

    except Exception as e:
        print(f"Error updating task: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Todoist CLI - Manage your Todoist tasks from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  todoist tasks                         List all active tasks
  todoist tasks -p "Work"               Filter tasks by project
  todoist projects                      List all projects
  todoist add "Buy groceries"           Add a simple task
  todoist add "Meeting" -d "tomorrow"   Add task with due date
  todoist add "Urgent" -P 4             Add high-priority task
  todoist complete <task_id>            Mark task as complete
  todoist delete <task_id>              Delete a task
  todoist get <task_id>                 View task details
  todoist update <task_id> --content "New text"

Environment:
  TODOIST_API_KEY    Required. Your Todoist API key.
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: tasks (ls)
    parser_ls = subparsers.add_parser(
        "tasks",
        aliases=["ls", "list"],
        help="List active tasks"
    )
    parser_ls.add_argument(
        "--project", "-p",
        help="Filter by project name"
    )
    parser_ls.set_defaults(func=list_tasks)

    # Command: projects
    parser_proj = subparsers.add_parser(
        "projects",
        aliases=["proj"],
        help="List all projects"
    )
    parser_proj.set_defaults(func=list_projects)

    # Command: add
    parser_add = subparsers.add_parser(
        "add",
        aliases=["new", "create"],
        help="Add a new task"
    )
    parser_add.add_argument(
        "content",
        help="Task content (text)"
    )
    parser_add.add_argument(
        "--due", "-d",
        help="Natural language due date (e.g., 'tomorrow at 5pm', 'next monday')"
    )
    parser_add.add_argument(
        "--priority", "-P",
        type=int,
        choices=[1, 2, 3, 4],
        default=1,
        help="Priority: 1=P4(normal), 2=P3, 3=P2, 4=P1(high)"
    )
    parser_add.add_argument(
        "--project-id",
        help="Project ID to add the task to"
    )
    parser_add.set_defaults(func=add_task)

    # Command: complete (done, close)
    parser_done = subparsers.add_parser(
        "complete",
        aliases=["done", "close", "finish"],
        help="Complete a task"
    )
    parser_done.add_argument(
        "task_id",
        help="The ID of the task to complete"
    )
    parser_done.set_defaults(func=complete_task)

    # Command: delete (rm)
    parser_rm = subparsers.add_parser(
        "delete",
        aliases=["rm", "remove"],
        help="Delete a task"
    )
    parser_rm.add_argument(
        "task_id",
        help="The ID of the task to delete"
    )
    parser_rm.set_defaults(func=delete_task)

    # Command: get (show, view)
    parser_get = subparsers.add_parser(
        "get",
        aliases=["show", "view"],
        help="Get task details"
    )
    parser_get.add_argument(
        "task_id",
        help="The ID of the task to view"
    )
    parser_get.set_defaults(func=get_task)

    # Command: update (edit)
    parser_update = subparsers.add_parser(
        "update",
        aliases=["edit", "modify"],
        help="Update an existing task"
    )
    parser_update.add_argument(
        "task_id",
        help="The ID of the task to update"
    )
    parser_update.add_argument(
        "--content", "-c",
        help="New task content"
    )
    parser_update.add_argument(
        "--due", "-d",
        help="New due date (natural language)"
    )
    parser_update.add_argument(
        "--priority", "-P",
        type=int,
        choices=[1, 2, 3, 4],
        help="New priority"
    )
    parser_update.set_defaults(func=update_task)

    # Handle no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
