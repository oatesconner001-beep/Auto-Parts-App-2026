"""
Scheduler
Advanced Integration & Automation (Priority 5)

Advanced scheduling system for:
- Automated daily/weekly processing runs
- Smart scheduling based on system load
- Task queue management
- Dependency tracking
- Resource-aware scheduling
"""

import json
import threading
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, asdict
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.performance_metrics import PerformanceTracker
from optimization.priority_scheduler import PriorityScheduler

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class ScheduledTask:
    """Represents a scheduled processing task."""
    id: str
    name: str
    task_type: str
    priority: TaskPriority
    schedule_time: str  # ISO format
    parameters: Dict[str, Any]
    dependencies: List[str]  # Task IDs this task depends on
    status: TaskStatus
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result_summary: Optional[Dict] = None

class AutomationScheduler:
    """Advanced automation scheduler for Parts Agent processing."""

    def __init__(self, excel_path: str = None):
        """Initialize the automation scheduler."""
        if excel_path is None:
            excel_path = str(Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx")

        self.excel_path = excel_path
        self.performance_tracker = PerformanceTracker()
        self.priority_scheduler = PriorityScheduler(excel_path)

        # Task management
        self.tasks = {}  # Dict[str, ScheduledTask]
        self.task_queue = []  # List of task IDs in execution order
        self.running_tasks = {}  # Dict[str, threading.Thread]

        # Scheduling configuration
        self.config = {
            'max_concurrent_tasks': 2,
            'default_retry_attempts': 3,
            'retry_delay_minutes': 15,
            'maintenance_window_start': '02:00',
            'maintenance_window_end': '04:00',
            'max_cpu_threshold': 85.0,
            'max_memory_threshold': 90.0,
            'min_available_disk_gb': 5.0
        }

        # Scheduling thread
        self.scheduler_thread = None
        self.scheduler_running = False
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'total_tasks_scheduled': 0,
            'total_tasks_completed': 0,
            'total_tasks_failed': 0,
            'scheduler_start_time': None,
            'last_maintenance': None
        }

        # Task handlers
        self.task_handlers = {
            'main_processing': self._handle_main_processing,
            'image_analysis': self._handle_image_analysis,
            'data_validation': self._handle_data_validation,
            'system_maintenance': self._handle_system_maintenance,
            'report_generation': self._handle_report_generation,
            'backup_creation': self._handle_backup_creation
        }

        print("[AUTOMATION_SCHEDULER] Initialized with advanced task scheduling")

    def start_scheduler(self):
        """Start the automation scheduler."""
        with self.lock:
            if self.scheduler_running:
                print("Scheduler is already running")
                return

            self.scheduler_running = True
            self.stats['scheduler_start_time'] = datetime.now().isoformat()

            # Setup default schedules
            self._setup_default_schedules()

            # Start scheduler thread
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()

            print("[SCHEDULER] Automation scheduler started")

    def stop_scheduler(self):
        """Stop the automation scheduler."""
        with self.lock:
            if not self.scheduler_running:
                return

            self.scheduler_running = False

            # Cancel all pending tasks
            for task_id, task in self.tasks.items():
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED

            # Stop running tasks gracefully
            for task_id, thread in self.running_tasks.items():
                if thread.is_alive():
                    print(f"[SCHEDULER] Waiting for task {task_id} to complete...")
                    thread.join(timeout=30)

            print("[SCHEDULER] Automation scheduler stopped")

    def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a new task."""
        with self.lock:
            # Validate task
            if task.id in self.tasks:
                raise ValueError(f"Task with ID {task.id} already exists")

            # Validate dependencies
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    raise ValueError(f"Dependency task {dep_id} does not exist")

            # Add to tasks and queue
            self.tasks[task.id] = task
            self.task_queue.append(task.id)
            self.stats['total_tasks_scheduled'] += 1

            print(f"[SCHEDULER] Task '{task.name}' scheduled for {task.schedule_time}")

            return task.id

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        with self.lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]

            if task.status == TaskStatus.RUNNING:
                # Task is running, attempt to stop it
                if task_id in self.running_tasks:
                    # Mark as cancelled, thread will check status
                    task.status = TaskStatus.CANCELLED
                    return True
            elif task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                if task_id in self.task_queue:
                    self.task_queue.remove(task_id)
                return True

            return False

    def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """Get the status of a scheduled task."""
        with self.lock:
            return self.tasks.get(task_id)

    def get_scheduler_status(self) -> Dict:
        """Get overall scheduler status."""
        with self.lock:
            return {
                'running': self.scheduler_running,
                'total_tasks': len(self.tasks),
                'pending_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
                'running_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING),
                'completed_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
                'failed_tasks': sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
                'queue_length': len(self.task_queue),
                'current_load': len(self.running_tasks),
                'max_concurrent': self.config['max_concurrent_tasks'],
                'statistics': self.stats.copy()
            }

    def _setup_default_schedules(self):
        """Setup default automated schedules."""
        try:
            current_time = datetime.now()

            # Daily main processing (6 AM)
            daily_main = ScheduledTask(
                id=f"daily_main_{current_time.strftime('%Y%m%d')}",
                name="Daily Main Processing",
                task_type="main_processing",
                priority=TaskPriority.HIGH,
                schedule_time=(current_time + timedelta(hours=1)).isoformat(),  # Test: 1 hour from now
                parameters={'sheet': 'Anchor', 'limit': 50},
                dependencies=[],
                status=TaskStatus.PENDING,
                created_at=current_time.isoformat()
            )

            # Daily image analysis (8 AM)
            daily_image = ScheduledTask(
                id=f"daily_image_{current_time.strftime('%Y%m%d')}",
                name="Daily Image Analysis",
                task_type="image_analysis",
                priority=TaskPriority.NORMAL,
                schedule_time=(current_time + timedelta(hours=2)).isoformat(),  # Test: 2 hours from now
                parameters={'sheet': 'Anchor', 'limit': 20},
                dependencies=[daily_main.id],
                status=TaskStatus.PENDING,
                created_at=current_time.isoformat()
            )

            # Daily system maintenance (3 AM)
            daily_maintenance = ScheduledTask(
                id=f"maintenance_{current_time.strftime('%Y%m%d')}",
                name="Daily System Maintenance",
                task_type="system_maintenance",
                priority=TaskPriority.LOW,
                schedule_time=(current_time + timedelta(minutes=30)).isoformat(),  # Test: 30 minutes from now
                parameters={'cleanup': True, 'backup': True},
                dependencies=[],
                status=TaskStatus.PENDING,
                created_at=current_time.isoformat()
            )

            # Schedule the tasks
            self.tasks[daily_main.id] = daily_main
            self.tasks[daily_image.id] = daily_image
            self.tasks[daily_maintenance.id] = daily_maintenance

            self.task_queue.extend([daily_main.id, daily_image.id, daily_maintenance.id])

            print("[SCHEDULER] Default schedules created")

        except Exception as e:
            print(f"[SCHEDULER] Error setting up default schedules: {e}")

    def _scheduler_loop(self):
        """Main scheduler loop."""
        print("[SCHEDULER] Scheduler loop started")

        while self.scheduler_running:
            try:
                # Check system resources
                if not self._check_system_resources():
                    time.sleep(60)  # Wait 1 minute if resources are constrained
                    continue

                # Process task queue
                self._process_task_queue()

                # Clean up completed tasks
                self._cleanup_completed_tasks()

                # Sleep briefly
                time.sleep(10)

            except Exception as e:
                print(f"[SCHEDULER] Error in scheduler loop: {e}")
                time.sleep(30)

        print("[SCHEDULER] Scheduler loop stopped")

    def _check_system_resources(self) -> bool:
        """Check if system resources are available for processing."""
        try:
            metrics = self.performance_tracker.get_real_time_metrics()
            system_metrics = metrics.get('system', {})

            cpu_usage = system_metrics.get('cpu_percent', 0)
            memory_usage = system_metrics.get('memory_percent', 0)

            # Check CPU and memory thresholds
            if cpu_usage > self.config['max_cpu_threshold']:
                print(f"[SCHEDULER] CPU usage too high ({cpu_usage:.1f}%), deferring tasks")
                return False

            if memory_usage > self.config['max_memory_threshold']:
                print(f"[SCHEDULER] Memory usage too high ({memory_usage:.1f}%), deferring tasks")
                return False

            # Check if we're at max concurrent tasks
            if len(self.running_tasks) >= self.config['max_concurrent_tasks']:
                return False

            return True

        except Exception as e:
            print(f"[SCHEDULER] Error checking system resources: {e}")
            return False

    def _process_task_queue(self):
        """Process the task queue and start eligible tasks."""
        with self.lock:
            current_time = datetime.now()

            # Find tasks ready to run
            ready_tasks = []
            for task_id in self.task_queue[:]:
                if task_id not in self.tasks:
                    self.task_queue.remove(task_id)
                    continue

                task = self.tasks[task_id]

                # Skip if not pending
                if task.status != TaskStatus.PENDING:
                    self.task_queue.remove(task_id)
                    continue

                # Check if it's time to run
                schedule_time = datetime.fromisoformat(task.schedule_time)
                if schedule_time > current_time:
                    continue

                # Check dependencies
                dependencies_met = True
                for dep_id in task.dependencies:
                    if dep_id in self.tasks:
                        dep_task = self.tasks[dep_id]
                        if dep_task.status != TaskStatus.COMPLETED:
                            dependencies_met = False
                            break

                if dependencies_met:
                    ready_tasks.append(task_id)

            # Start ready tasks (up to concurrent limit)
            available_slots = self.config['max_concurrent_tasks'] - len(self.running_tasks)
            for task_id in ready_tasks[:available_slots]:
                self._start_task(task_id)

    def _start_task(self, task_id: str):
        """Start execution of a task."""
        task = self.tasks[task_id]
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now().isoformat()

        # Remove from queue
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)

        # Start task thread
        thread = threading.Thread(target=self._execute_task, args=(task_id,), daemon=True)
        self.running_tasks[task_id] = thread
        thread.start()

        print(f"[SCHEDULER] Started task '{task.name}' (ID: {task_id})")

    def _execute_task(self, task_id: str):
        """Execute a specific task."""
        task = self.tasks[task_id]

        try:
            # Check if task was cancelled
            if task.status == TaskStatus.CANCELLED:
                return

            # Get task handler
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {task.task_type}")

            # Execute the task
            result = handler(task.parameters)

            # Mark as completed
            with self.lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                task.result_summary = result
                self.stats['total_tasks_completed'] += 1

            print(f"[SCHEDULER] Completed task '{task.name}' (ID: {task_id})")

        except Exception as e:
            # Mark as failed
            with self.lock:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now().isoformat()
                task.error_message = str(e)
                self.stats['total_tasks_failed'] += 1

            print(f"[SCHEDULER] Failed task '{task.name}' (ID: {task_id}): {e}")

        finally:
            # Remove from running tasks
            with self.lock:
                if task_id in self.running_tasks:
                    del self.running_tasks[task_id]

    def _cleanup_completed_tasks(self):
        """Clean up old completed tasks."""
        with self.lock:
            current_time = datetime.now()
            cleanup_threshold = current_time - timedelta(days=7)  # Keep tasks for 7 days

            tasks_to_remove = []
            for task_id, task in self.tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    if task.completed_at:
                        completed_time = datetime.fromisoformat(task.completed_at)
                        if completed_time < cleanup_threshold:
                            tasks_to_remove.append(task_id)

            for task_id in tasks_to_remove:
                del self.tasks[task_id]

            if tasks_to_remove:
                print(f"[SCHEDULER] Cleaned up {len(tasks_to_remove)} old tasks")

    # Task handlers
    def _handle_main_processing(self, parameters: Dict) -> Dict:
        """Handle main processing task."""
        sheet = parameters.get('sheet', 'Anchor')
        limit = parameters.get('limit', 50)

        # Simulate main processing
        time.sleep(2)  # Simulate processing time

        return {
            'task_type': 'main_processing',
            'sheet': sheet,
            'rows_processed': limit,
            'success_rate': 0.75,
            'duration_seconds': 2.0
        }

    def _handle_image_analysis(self, parameters: Dict) -> Dict:
        """Handle image analysis task."""
        sheet = parameters.get('sheet', 'Anchor')
        limit = parameters.get('limit', 20)

        # Simulate image analysis
        time.sleep(1.5)

        return {
            'task_type': 'image_analysis',
            'sheet': sheet,
            'images_processed': limit,
            'upgrades_made': int(limit * 0.67),  # 67% upgrade rate
            'duration_seconds': 1.5
        }

    def _handle_data_validation(self, parameters: Dict) -> Dict:
        """Handle data validation task."""
        validation_type = parameters.get('type', 'comprehensive')

        # Simulate validation
        time.sleep(0.5)

        return {
            'task_type': 'data_validation',
            'validation_type': validation_type,
            'errors_found': 2,
            'warnings_found': 5,
            'quality_score': 0.92
        }

    def _handle_system_maintenance(self, parameters: Dict) -> Dict:
        """Handle system maintenance task."""
        cleanup = parameters.get('cleanup', False)
        backup = parameters.get('backup', False)

        # Simulate maintenance
        time.sleep(1.0)

        actions_performed = []
        if cleanup:
            actions_performed.append('cache_cleanup')
        if backup:
            actions_performed.append('data_backup')

        return {
            'task_type': 'system_maintenance',
            'actions_performed': actions_performed,
            'cleanup_size_mb': 150 if cleanup else 0,
            'backup_created': backup
        }

    def _handle_report_generation(self, parameters: Dict) -> Dict:
        """Handle report generation task."""
        report_type = parameters.get('type', 'daily')

        # Simulate report generation
        time.sleep(0.8)

        return {
            'task_type': 'report_generation',
            'report_type': report_type,
            'report_size_kb': 250,
            'charts_generated': 5
        }

    def _handle_backup_creation(self, parameters: Dict) -> Dict:
        """Handle backup creation task."""
        backup_type = parameters.get('type', 'incremental')

        # Simulate backup
        time.sleep(2.5)

        return {
            'task_type': 'backup_creation',
            'backup_type': backup_type,
            'backup_size_mb': 1200,
            'files_backed_up': 450
        }

    def get_automation_report(self) -> Dict:
        """Generate comprehensive automation report."""
        with self.lock:
            current_time = datetime.now()

            # Calculate uptime
            uptime_seconds = 0
            if self.stats['scheduler_start_time']:
                start_time = datetime.fromisoformat(self.stats['scheduler_start_time'])
                uptime_seconds = (current_time - start_time).total_seconds()

            # Task statistics by type
            task_stats_by_type = {}
            task_stats_by_status = {}

            for task in self.tasks.values():
                # By type
                task_type = task.task_type
                if task_type not in task_stats_by_type:
                    task_stats_by_type[task_type] = {'total': 0, 'completed': 0, 'failed': 0}

                task_stats_by_type[task_type]['total'] += 1
                if task.status == TaskStatus.COMPLETED:
                    task_stats_by_type[task_type]['completed'] += 1
                elif task.status == TaskStatus.FAILED:
                    task_stats_by_type[task_type]['failed'] += 1

                # By status
                status_key = task.status.value
                task_stats_by_status[status_key] = task_stats_by_status.get(status_key, 0) + 1

            return {
                'timestamp': current_time.isoformat(),
                'scheduler_status': {
                    'running': self.scheduler_running,
                    'uptime_seconds': uptime_seconds,
                    'uptime_hours': uptime_seconds / 3600
                },
                'task_statistics': {
                    'total_tasks': len(self.tasks),
                    'by_status': task_stats_by_status,
                    'by_type': task_stats_by_type,
                    'success_rate': (self.stats['total_tasks_completed'] /
                                   max(1, self.stats['total_tasks_completed'] + self.stats['total_tasks_failed']))
                },
                'system_status': {
                    'current_load': len(self.running_tasks),
                    'max_concurrent': self.config['max_concurrent_tasks'],
                    'queue_length': len(self.task_queue)
                },
                'configuration': self.config.copy(),
                'recommendations': self._generate_automation_recommendations()
            }

    def _generate_automation_recommendations(self) -> List[str]:
        """Generate automation improvement recommendations."""
        recommendations = []

        total_tasks = self.stats['total_tasks_completed'] + self.stats['total_tasks_failed']
        if total_tasks > 0:
            failure_rate = self.stats['total_tasks_failed'] / total_tasks

            if failure_rate > 0.2:
                recommendations.append("High task failure rate - review task implementations and error handling")

            if failure_rate < 0.05:
                recommendations.append("Excellent task success rate - consider increasing automation scope")

        if len(self.running_tasks) >= self.config['max_concurrent_tasks'] * 0.8:
            recommendations.append("High concurrent task usage - consider increasing max_concurrent_tasks")

        if len(self.task_queue) > 10:
            recommendations.append("Long task queue - review scheduling frequency and resource allocation")

        if not recommendations:
            recommendations.append("Automation system operating efficiently")

        return recommendations

if __name__ == "__main__":
    # Test the scheduler
    print("Testing Automation Scheduler...")

    scheduler = AutomationScheduler()

    # Start scheduler
    scheduler.start_scheduler()

    try:
        # Let it run for a short time
        print("Scheduler running... (will run for 30 seconds)")
        time.sleep(30)

        # Check status
        status = scheduler.get_scheduler_status()
        print(f"\nScheduler Status:")
        print(f"  Running: {status['running']}")
        print(f"  Total tasks: {status['total_tasks']}")
        print(f"  Completed: {status['completed_tasks']}")
        print(f"  Running: {status['running_tasks']}")

        # Generate report
        report = scheduler.get_automation_report()
        print(f"\nAutomation Report:")
        print(f"  Task success rate: {report['task_statistics']['success_rate']:.1%}")
        print(f"  Uptime: {report['scheduler_status']['uptime_hours']:.1f} hours")

    finally:
        # Stop scheduler
        scheduler.stop_scheduler()

    print("Automation Scheduler test completed.")