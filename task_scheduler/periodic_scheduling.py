"""! @file periodic_scheduler.py
@brief Periodic task scheduling components for task management system
@author Samuel Longauer

@defgroup scheduler Scheduler Module
@brief Handles recurring task patterns and automated scheduling
"""
import datetime
import json
from pathlib import Path
from task_scheduler.task import Task
from task_scheduler.storage import Storage
from typing import List


class SchedulingPattern:
    """! @brief Defines temporal patterns for recurring task scheduling"""

    def __init__(self, week_day=None, day=None, month=None, year=None):
        """! @brief Initialize scheduling pattern criteria

        @param week_day Name of weekday (e.g., "monday") or None for any
        @param day Day of month (1-31) or None for any
        @param month Month number (1-12) or None for any
        @param year Specific year or None for any
        """
        self.week_day = week_day
        self.day = day
        self.month = month
        self.year = year

    def date_match(self, date: datetime) -> bool:
        """! @brief Check if date matches all specified pattern criteria

        @ingroup scheduler

        @param date Date to validate against pattern
        @return True if date matches all non-null pattern fields
        @note Comparison is case-insensitive for weekday names
        """
        day_of_week = date.strftime("%A").lower()
        day = date.day
        month = date.month
        year = date.year

        if self.week_day is not None and self.week_day != day_of_week:
            return False

        if self.day is not None and self.day != day:
            return False

        if self.month is not None and self.month != month:
            return False

        if self.year is not None and self.year != year:
            return False

        return True

    def to_dict(self) -> dict:
        """! @brief Serialize pattern to dictionary format

        @return Dictionary representation of pattern fields
        """
        return {'week_day': self.week_day, 'day': self.day, 'month': self.month, 'year': self.year}

    @classmethod
    def from_dict(cls, serialized_pattern) -> 'SchedulingPattern':
        """! @brief Reconstruct pattern from serialized dictionary

        @param serialized_pattern Dictionary with pattern fields
        @return Initialized SchedulingPattern object
        """
        return SchedulingPattern(
            week_day=serialized_pattern['week_day'],
            day=serialized_pattern['day'],
            month=serialized_pattern['month'],
            year=serialized_pattern['year']
        )

    def __eq__(self, other) -> bool:
        """! @brief Equality check based on pattern fields

        @param other Object to compare against
        @return True if all pattern fields match
        """
        if not isinstance(other, SchedulingPattern):
            return False
        return (self.day == other.day and self.month == other.month
                and self.year == other.year and self.week_day == other.week_day)


class PeriodicScheduler:
    """! @brief Manages storage and execution of recurring task patterns"""

    storage = Storage()

    def __init__(self, task: Task, pattern: SchedulingPattern, scheduler: str):
        """! @brief Initialize recurring task configuration

        @param task Task object to schedule
        @param pattern Temporal pattern for recurrence
        @param scheduler Name of scheduler subsystem using this pattern
        """
        self.task = task
        self.pattern = pattern
        self.scheduler = scheduler

    def add_task(self):
        """! @brief Persist task to recurring schedule storage

        @note Uses __eq__ check to prevent duplicate entries
        @details Loads existing tasks, adds new entry if unique,
                 then saves updated collection
        """

        script_dir = Path(__file__).parent
        path = script_dir / "../data/periodic_schedule.json"
        path.parent.mkdir(exist_ok=True, parents=True)
        objs = PeriodicScheduler.storage.load(path)

        if self.to_dict() not in objs:
            objs.append(self.to_dict())

        PeriodicScheduler.storage.save(path, objs)

    def to_dict(self) -> dict:
        """! @brief Serialize scheduler configuration to dictionary

        @return Nested dictionary with task, pattern and scheduler name
        """
        return {
            'task': self.task.to_dict(),
            'pattern': self.pattern.to_dict(),
            'scheduler': self.scheduler
        }

    @classmethod
    def from_dict(cls, serialized_objs) -> List['PeriodicScheduler']:
        """! @brief Reconstruct scheduler objects from serialized data

        @param serialized_objs List of dictionary representations
        @return List of initialized PeriodicScheduler objects
        """
        tasks = Task.construct_tasks([t['task'] for t in serialized_objs])
        patterns = [SchedulingPattern.from_dict(p['pattern'])
                    for p in serialized_objs]
        scheduler_names = [t['scheduler'] for t in serialized_objs]
        return [PeriodicScheduler(task, pattern, scheduler)
                for task, pattern, scheduler in zip(tasks, patterns, scheduler_names)]

    @classmethod
    def save_periodic_tasks(cls, objs):
        """! @brief Save collection of periodic tasks to JSON storage

        @param objs List of PeriodicScheduler objects to persist
        """
        script_dir = Path(__file__).parent
        path = script_dir / "../data/periodic_schedule.json"
        path.parent.mkdir(exist_ok=True, parents=True)
        cls.storage.save(path, [obj.to_dict() for obj in objs])

    @classmethod
    def load_periodic_tasks(cls) -> list:
        """! @brief Load periodic tasks from JSON storage

        @return List of loaded PeriodicScheduler objects
        """
        path = Path(__file__).parent / "../data/periodic_schedule.json"
        return cls.storage.load(path)

    def __eq__(self, other) -> bool:
        """! @brief Equality check based on task and pattern

        @param other Object to compare against
        @return True if both task and pattern match
        """
        if not isinstance(other, PeriodicScheduler):
            return False
        return (self.task == other.task) and (self.pattern == other.pattern)

    @staticmethod
    def automatic_scheduling(scheduler_name: str) -> List[Task]:
        """! @brief Get tasks scheduled for automatic execution today

        @ingroup scheduler
        @param scheduler_name Name of scheduler subsystem using this pattern
        @return List of tasks matching current date's pattern
        @details Filters periodic tasks using today's date check
        """
        today = datetime.date.today()
        periodic_schedulers = PeriodicScheduler.from_dict(
            PeriodicScheduler.load_periodic_tasks())
        return [ps.task for ps in periodic_schedulers
                if ps.pattern.date_match(today) and ps.scheduler == scheduler_name]


def main():
    ...


if __name__ == "__main__":
    main()