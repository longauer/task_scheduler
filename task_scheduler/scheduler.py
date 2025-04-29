"""! @file scheduler.py
@brief Task scheduling system implementation
@author Samuel Longauer

@defgroup scheduler Scheduler Module
@brief Core scheduling logic and data management
"""

from task_scheduler.task import Task
from task_scheduler.time_slot import TimeSlot
from task_scheduler.storage import Storage
from task_scheduler.utils import time_slot_covering

from collections import deque
from collections import defaultdict
import bisect
import inspect
from typing import Optional, List, Dict, Any
from pathlib import Path
import difflib
import shutil
import datetime
import sys


class TaskScheduler:
    """! @brief Main task scheduling system
    
    @ingroup scheduler
    
    Manages time slots, tasks, and their assignments using greedy scheduling algorithm
    """

    def __init__(self, schedule_name):
        """! @brief Initialize TaskScheduler instance
        
        @param schedule_name Name identifier for the schedule
        """
        self.schedule_name = schedule_name
        self.time_slots = list()  ##< Sorted list of TimeSlot objects
        self.tasks = list()  ##< Sorted list of Task objects by deadline
        self.scheduled_tasks = defaultdict(deque)  ##< TimeSlot to Task mapping
        self.storage = Storage()

    def add_time_slot(self, time_slot):
        """! @brief Add time slot to scheduler
        
        @param time_slot TimeSlot object to add
        @note Maintains sorted order using bisect.insort
        """
        bisect.insort(self.time_slots, time_slot)

    def delete_time_slot(self, time_slot):
        """! @brief Remove time slot from scheduler
        
        @param time_slot TimeSlot object to remove
        """
        self.time_slots.remove(time_slot)

    def time_slot_management(self):
        """! @brief Clean up expired time slots
        @details Removes all time slots that have ended before current time
        """
        time_now = datetime.datetime.now()
        self.time_slots = list(filter(lambda slot: slot.end_time >= time_now, self.time_slots))

    def add_task(self, task: Optional["Task"]):
        """! @brief Add task to scheduler
        
        @param task Task object to add
        @note Maintains sorted order by deadline using bisect.insort
        """
        bisect.insort(self.tasks, task)

    def delete_task(self, task_name):
        """! @brief Remove task from scheduler
        
        @param task_name Name of task to remove
        @exception SystemExit If task not found with close match suggestions
        """
        task = self.get_task_by_name(task_name)
        if not task:
            matches = difflib.get_close_matches(task_name, [t.name for t in self.tasks])
            msg = f"Task '{task_name}' not found."
            if matches:
                msg += f" Did you mean: {', '.join(matches)}?"
            print(msg, file=sys.stderr)
            sys.exit(1)

        task.duration, task.completion = 0, 0
        for ind, task in enumerate(self.tasks):
            if task.name == task_name:
                del self.tasks[ind]
            else:
                task.delete(task_name)
        self.save_schedule()

    def get_task_by_name(self, name):
        """! @brief Find task by name in hierarchy
        
        @param name Task name to search for
        @return Task object if found, None otherwise
        """
        return Task.find_task_by_name(name, self.tasks)

    def schedule_tasks(self, show_unscheduled=False):
        """! @brief Core scheduling algorithm
        
        @param show_unscheduled Whether to print unschedulable tasks
        @details Uses greedy algorithm to assign lowest-level tasks to time slots
        """
        self.time_slot_management()
        self.time_slots = time_slot_covering(self.time_slots)
        self.tasks = list(filter(lambda t: t.completion < 100, self.tasks))
        self.tasks.sort(key=lambda t: t.deadline)

        lowest_level_tasks = [p for task in self.tasks for p in Task.collect_lowest_level_tasks(task)]
        lowest_level_tasks = list(filter(lambda t: t.completion < 100 and t.duration != 0, lowest_level_tasks))

        impossible_to_schedule = []
        scheduling_result = dict()
        shift = 0
        iterator = iter(lowest_level_tasks)

        for ind, task in enumerate(iterator):
            for time_slot in self.time_slots:
                available_time = (min(time_slot.end_time, task.deadline) - 
                                max(datetime.datetime.now(), time_slot.start_time)).total_seconds() / 60 - \
                                (0 if time_slot not in self.scheduled_tasks else 
                                sum(t.duration for t in self.scheduled_tasks[time_slot]))

                task_root = task.get_root()
                if (task.duration <= available_time) and \
                   (task_root not in scheduling_result or scheduling_result[task_root] <= time_slot):
                    self.scheduled_tasks[time_slot].append(task)
                    scheduling_result[task_root] = time_slot
                    break
            else:
                if show_unscheduled:
                    impossible_to_schedule.append(task.name)
                    root = task.get_root()
                    while ind + shift + 1 < len(lowest_level_tasks) and \
                        lowest_level_tasks[ind + shift + 1].get_root() is root:
                        shift += 1
                        next_task = next(iterator, None)
                        if next_task:
                            impossible_to_schedule.append(next_task.name)

        if impossible_to_schedule and show_unscheduled:
            print("Unschedulable tasks:", ", ".join(impossible_to_schedule), file=sys.stderr)

    def get_next_task(self):
        """! @brief Get first uncompleted task
        
        @return First uncompleted Task or None if none available
        """
        for ts in self.time_slots:
            if self.scheduled_tasks[ts]:
                for task in self.scheduled_tasks[ts]:
                    if task.completion != 100:
                        return task
        return None

    def dead_tasks(self) -> List[Task]:
        """! @brief Get tasks past their deadline
        
        @return List of expired Task objects
        """
        time_now = datetime.datetime.now()
        return [t for t in self.tasks if (time_now - t.deadline).total_seconds() > 0]

    def to_dict(self):
        """! @brief Serialize scheduler state
        
        @return Dictionary representation of scheduler state
        """
        return {
            "schedule_name": self.schedule_name,
            "time_slots": [ts.to_dict() for ts in self.time_slots],
            "tasks": [t.to_dict() for t in self.tasks],
        }

    def schedule_to_dict(self):
        """! @brief Serialize schedule assignments
        
        @return List of dictionaries representing time slot assignments
        """
        return [{
            "start_time": ts.start_time.isoformat(),
            "end_time": ts.end_time.isoformat(),
            "tasks": [t.to_dict() for t in tasks]
        } for ts, tasks in self.scheduled_tasks.items()]

    def save_schedule(self):
        """! @brief Persist schedule to storage"""
        script_dir = Path(__file__).parent
        path = script_dir / "../data" / self.schedule_name
        path.mkdir(exist_ok=True, parents=True)
        self.storage.save(path/"schedule_state.json", self.to_dict())
        self.storage.save(path/"schedule.json", self.schedule_to_dict())

    def load_scheduler(self):
        """! @brief Load scheduler state from storage
        
        @exception FileNotFoundError If state file is missing
        """
        path = Path(__file__).parent / "../data" / self.schedule_name / "schedule_state.json"
        state_json = self.storage.load(path)
        self.schedule_name = state_json["schedule_name"]
        self.time_slots = [
            TimeSlot.fromisoformat(ts["start_time"], ts["end_time"]) 
            for ts in state_json["time_slots"]
        ]
        self.tasks = self._construct_tasks(state_json["tasks"])

    def load_schedule(self):
        """! @brief Load schedule assignments from storage
        
        @exception FileNotFoundError If schedule file is missing
        """
        path = Path(__file__).parent / "../data" / self.schedule_name / "schedule.json"
        schedule_json = self.storage.load(path)
        for slot in schedule_json:
            ts = TimeSlot.fromisoformat(slot["start_time"], slot["end_time"])
            self.scheduled_tasks[ts] = deque(self._construct_tasks(slot["tasks"]))

    def _construct_tasks(self, tasks: List[Dict[str, Any]]) -> List[Task]:
        """! @brief Reconstruct task hierarchy from serialized data
        
        @param tasks List of serialized task dictionaries
        @return List of reconstructed Task objects
        """
        constructed = []
        for task in tasks:
            subtasks = self._construct_tasks(task["subtasks"])
            filtered = {k:v for k,v in task.items() if k in inspect.signature(Task.__init__).parameters}
            filtered["deadline"] = datetime.datetime.fromisoformat(filtered["deadline"])
            new_task = Task(**filtered)
            new_task.subtasks = subtasks
            for t in subtasks:
                t.parent = new_task
            constructed.append(new_task)
        return constructed

    @staticmethod
    def delete_schedule(schedule_name):
        """! @brief Permanently remove schedule
        
        @param schedule_name Name of schedule to delete
        """
        script_dir = Path(__file__).parent
        shutil.rmtree(script_dir / "../data" / schedule_name)

    @staticmethod
    def merge_schedules(new_schedule_name, *args):
        """! @brief Combine multiple schedules
        
        @param new_schedule_name Name for merged schedule
        @param args Names of schedules to merge
        """
        schedulers = [TaskScheduler(name) for name in args]
        for s in schedulers:
            s.load_scheduler()
        
        merged = TaskScheduler(new_schedule_name)
        merged.tasks = [t for s in schedulers for t in s.tasks]
        merged.time_slots = time_slot_covering([ts for s in schedulers for ts in s.time_slots])
        merged.save_schedule()


def main():
    ...


if __name__ == "__main__":
    main()
