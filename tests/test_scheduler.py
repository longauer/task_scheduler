import unittest
import datetime
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

from task_scheduler.scheduler import TaskScheduler
from task_scheduler.time_slot import TimeSlot
from task_scheduler.task import Task
from task_scheduler.visualisation import Visualisation


class TestTaskScheduler(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first_scheduler = TaskScheduler("TestScheduleA")
        cls.second_scheduler = TaskScheduler("TestScheduleB")
        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)
        cls.slot = TimeSlot(start_time, end_time)

    def test_add_time_slot(self):
        self.first_scheduler.add_time_slot(self.slot)
        self.assertIn(self.slot, self.first_scheduler.time_slots)

    def test_add_task(self):
        deadline = datetime.datetime.now() + datetime.timedelta(hours=1)
        task = Task(name="TestTask", duration=42, description="description", deadline=deadline)
        self.first_scheduler.add_task(task)
        self.assertIn(task, self.first_scheduler.tasks)

    def test_delete_time_slot(self):
        self.first_scheduler.delete_time_slot(self.slot)
        self.assertEqual(self.first_scheduler.time_slots, [])

    def test_delete_task(self):
        self.first_scheduler.delete_task("TestTask")
        self.assertEqual(self.first_scheduler.tasks, [])


if __name__ == "__main__":
    unittest.main()