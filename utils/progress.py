"""
Progress Tracking Utilities
Reusable progress tracking for multi-agent and parallel processing systems.

Extracted from company-research.py for use across projects.
"""

import threading
import time
from typing import Dict, Optional, Literal
from dataclasses import dataclass, field
import logging


logger = logging.getLogger(__name__)

StatusType = Literal['pending', 'running', 'success', 'failed', 'cancelled']


def show_progress_bar(
    completed: int,
    total: int,
    success_count: int = 0,
    width: int = 50,
    show_success_rate: bool = True
) -> str:
    """
    Generate a visual progress bar string.

    Args:
        completed: Number of completed items
        total: Total number of items
        success_count: Number of successful items (default: 0)
        width: Width of the progress bar in characters (default: 50)
        show_success_rate: Whether to show success rate (default: True)

    Returns:
        Formatted progress bar string

    Examples:
        >>> show_progress_bar(5, 10)
        '     Progress: [█████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░] 50.0% (5/10) | 0/5 successful (0.0%)'
        >>> show_progress_bar(10, 10, 8)
        '     Progress: [██████████████████████████████████████████████████] 100.0% (10/10) | 8/10 successful (80.0%)'
    """
    if total == 0:
        return "     Progress: No items to process"

    percent = (completed / total) * 100
    filled_length = int(width * completed // total)
    filled = '█' * filled_length
    empty = '░' * (width - filled_length)

    progress_str = f"     Progress: [{filled}{empty}] {percent:5.1f}% ({completed}/{total})"

    if show_success_rate and completed > 0:
        success_rate = (success_count / completed * 100)
        progress_str += f" | {success_count}/{completed} successful ({success_rate:.1f}%)"

    return progress_str


@dataclass
class TaskInfo:
    """Information about a tracked task"""
    task_id: str
    name: str
    status: StatusType = 'pending'
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        elif self.start_time:
            return time.time() - self.start_time
        return None

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        duration = self.duration
        if duration is None:
            return "N/A"

        if duration < 60:
            return f"{duration:.1f}s"
        elif duration < 3600:
            return f"{duration/60:.1f}m"
        else:
            return f"{duration/3600:.1f}h"


class ProgressTracker:
    """
    Thread-safe progress tracker for parallel tasks.

    Useful for tracking multiple agents, workers, or parallel operations.
    """

    def __init__(self, name: str = "Progress Tracker"):
        """
        Initialize progress tracker.

        Args:
            name: Name of this tracker (for logging)
        """
        self.name = name
        self.tasks: Dict[str, TaskInfo] = {}
        self.lock = threading.Lock()
        self._created_at = time.time()

    def add_task(self, task_id: str, name: str, metadata: Optional[Dict] = None):
        """
        Add a new task to track.

        Args:
            task_id: Unique identifier for the task
            name: Human-readable task name
            metadata: Optional metadata dictionary
        """
        with self.lock:
            self.tasks[task_id] = TaskInfo(
                task_id=task_id,
                name=name,
                status='pending',
                metadata=metadata or {}
            )
        logger.debug(f"[{self.name}] Added task: {task_id} ({name})")

    def start_task(self, task_id: str):
        """
        Mark a task as started.

        Args:
            task_id: Task identifier

        Raises:
            KeyError: If task_id not found
        """
        with self.lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task not found: {task_id}")

            self.tasks[task_id].status = 'running'
            self.tasks[task_id].start_time = time.time()

        logger.debug(f"[{self.name}] Started task: {task_id}")

    def complete_task(self, task_id: str, success: bool = True, error: Optional[str] = None):
        """
        Mark a task as completed.

        Args:
            task_id: Task identifier
            success: Whether task completed successfully (default: True)
            error: Optional error message if failed

        Raises:
            KeyError: If task_id not found
        """
        with self.lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task not found: {task_id}")

            task = self.tasks[task_id]
            task.status = 'success' if success else 'failed'
            task.end_time = time.time()
            if error:
                task.error = error

        status_str = "successfully" if success else "with failure"
        logger.debug(f"[{self.name}] Completed task {task_id} {status_str}")

    def cancel_task(self, task_id: str):
        """
        Mark a task as cancelled.

        Args:
            task_id: Task identifier

        Raises:
            KeyError: If task_id not found
        """
        with self.lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task not found: {task_id}")

            task = self.tasks[task_id]
            task.status = 'cancelled'
            task.end_time = time.time()

        logger.debug(f"[{self.name}] Cancelled task: {task_id}")

    def get_summary(self) -> Dict:
        """
        Get current progress summary.

        Returns:
            Dictionary with progress statistics
        """
        with self.lock:
            total = len(self.tasks)
            completed = sum(1 for t in self.tasks.values() if t.status in ['success', 'failed', 'cancelled'])
            successful = sum(1 for t in self.tasks.values() if t.status == 'success')
            failed = sum(1 for t in self.tasks.values() if t.status == 'failed')
            running = sum(1 for t in self.tasks.values() if t.status == 'running')
            pending = sum(1 for t in self.tasks.values() if t.status == 'pending')
            cancelled = sum(1 for t in self.tasks.values() if t.status == 'cancelled')

            # Calculate average duration for completed tasks
            completed_tasks = [t for t in self.tasks.values() if t.duration is not None]
            avg_duration = sum(t.duration for t in completed_tasks) / len(completed_tasks) if completed_tasks else 0

            return {
                "total": total,
                "completed": completed,
                "successful": successful,
                "failed": failed,
                "running": running,
                "pending": pending,
                "cancelled": cancelled,
                "success_rate": (successful / completed * 100) if completed > 0 else 0,
                "avg_duration": avg_duration,
                "tracker_uptime": time.time() - self._created_at
            }

    def get_progress_bar(self, width: int = 50) -> str:
        """
        Get formatted progress bar.

        Args:
            width: Width of progress bar (default: 50)

        Returns:
            Formatted progress bar string
        """
        summary = self.get_summary()
        return show_progress_bar(
            completed=summary['completed'],
            total=summary['total'],
            success_count=summary['successful'],
            width=width
        )

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        Get task information.

        Args:
            task_id: Task identifier

        Returns:
            TaskInfo object or None if not found
        """
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, TaskInfo]:
        """
        Get all tasks (copy).

        Returns:
            Dictionary of task_id -> TaskInfo
        """
        with self.lock:
            return self.tasks.copy()

    def get_tasks_by_status(self, status: StatusType) -> Dict[str, TaskInfo]:
        """
        Get tasks filtered by status.

        Args:
            status: Status to filter by

        Returns:
            Dictionary of task_id -> TaskInfo for matching tasks
        """
        with self.lock:
            return {
                task_id: task
                for task_id, task in self.tasks.items()
                if task.status == status
            }

    def reset(self):
        """Clear all tasks and reset tracker"""
        with self.lock:
            self.tasks.clear()
            self._created_at = time.time()
        logger.debug(f"[{self.name}] Reset tracker")

    def print_summary(self):
        """Print a formatted summary to stdout"""
        summary = self.get_summary()
        print(f"\n{'='*70}")
        print(f"Progress Tracker: {self.name}")
        print(f"{'='*70}")
        print(f"Total tasks:      {summary['total']}")
        print(f"Completed:        {summary['completed']}")
        print(f"  Successful:     {summary['successful']}")
        print(f"  Failed:         {summary['failed']}")
        print(f"  Cancelled:      {summary['cancelled']}")
        print(f"Running:          {summary['running']}")
        print(f"Pending:          {summary['pending']}")
        print(f"Success rate:     {summary['success_rate']:.1f}%")
        print(f"Avg duration:     {summary['avg_duration']:.2f}s")
        print(f"Uptime:           {summary['tracker_uptime']:.1f}s")
        print(f"{'='*70}")
        print(self.get_progress_bar())
        print(f"{'='*70}\n")


class MultiProgressTracker:
    """
    Track multiple progress trackers (e.g., for hierarchical systems).

    Useful for systems with multiple layers like pods of agents.
    """

    def __init__(self, name: str = "Multi-Progress Tracker"):
        """
        Initialize multi-progress tracker.

        Args:
            name: Name of this tracker
        """
        self.name = name
        self.trackers: Dict[str, ProgressTracker] = {}
        self.lock = threading.Lock()

    def add_tracker(self, tracker_id: str, tracker_name: str) -> ProgressTracker:
        """
        Add a new progress tracker.

        Args:
            tracker_id: Unique identifier for the tracker
            tracker_name: Human-readable tracker name

        Returns:
            Created ProgressTracker instance
        """
        with self.lock:
            tracker = ProgressTracker(name=tracker_name)
            self.trackers[tracker_id] = tracker
            return tracker

    def get_tracker(self, tracker_id: str) -> Optional[ProgressTracker]:
        """
        Get a specific tracker.

        Args:
            tracker_id: Tracker identifier

        Returns:
            ProgressTracker or None if not found
        """
        with self.lock:
            return self.trackers.get(tracker_id)

    def get_overall_summary(self) -> Dict:
        """
        Get summary across all trackers.

        Returns:
            Aggregated summary dictionary
        """
        with self.lock:
            overall = {
                "total": 0,
                "completed": 0,
                "successful": 0,
                "failed": 0,
                "running": 0,
                "pending": 0,
                "cancelled": 0,
                "tracker_count": len(self.trackers)
            }

            for tracker in self.trackers.values():
                summary = tracker.get_summary()
                overall["total"] += summary["total"]
                overall["completed"] += summary["completed"]
                overall["successful"] += summary["successful"]
                overall["failed"] += summary["failed"]
                overall["running"] += summary["running"]
                overall["pending"] += summary["pending"]
                overall["cancelled"] += summary["cancelled"]

            overall["success_rate"] = (
                (overall["successful"] / overall["completed"] * 100)
                if overall["completed"] > 0
                else 0
            )

            return overall

    def print_overall_summary(self):
        """Print formatted overall summary"""
        summary = self.get_overall_summary()
        print(f"\n{'='*70}")
        print(f"Multi-Progress Tracker: {self.name}")
        print(f"{'='*70}")
        print(f"Trackers:         {summary['tracker_count']}")
        print(f"Total tasks:      {summary['total']}")
        print(f"Completed:        {summary['completed']}")
        print(f"  Successful:     {summary['successful']}")
        print(f"  Failed:         {summary['failed']}")
        print(f"  Cancelled:      {summary['cancelled']}")
        print(f"Running:          {summary['running']}")
        print(f"Pending:          {summary['pending']}")
        print(f"Success rate:     {summary['success_rate']:.1f}%")
        print(f"{'='*70}")
        print(show_progress_bar(
            completed=summary['completed'],
            total=summary['total'],
            success_count=summary['successful']
        ))
        print(f"{'='*70}\n")
