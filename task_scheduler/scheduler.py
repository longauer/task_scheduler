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


## Schedule instance contains following 3 data structures
## - sorted list of time_slots
## - sorted list of tasks ordered by deadlines
## - assignment of arrays of tasks to time_slots: simple mapping from time_slots to arrays/queues of tasks


class TaskScheduler:

    def __init__(self, schedule_name):

        self.schedule_name = schedule_name

        self.time_slots = list()  ## adding new instances with bisect.insort -- keepint the list sorted

        self.tasks = list()  ## adding new instances with bisect.insort

        self.scheduled_tasks = defaultdict(
            deque)  ## after initialization a dict (keys: time_slots, values: dequeue instances)

        self.storage = Storage()

    ## time_slots
    def add_time_slot(self, time_slot):  ## assuming passing initialized TimeSlot objects

        bisect.insort(self.time_slots, time_slot)

    def delete_time_slot(self, time_slot):

        self.time_slots.remove(time_slot)

    def time_slot_management(self):
        """ Removes all time slots that are overdue """

        time_now = datetime.datetime.now()

        self.time_slots = list(filter(lambda slot: slot.end_time >= time_now, self.time_slots))

    ## tasks
    def add_task(self, task: Optional["Task"]):  ## adding a task with a deadline

        bisect.insort(self.tasks, task)

    def delete_task(self, task_name):
        """ Removing a task from the list of tasks """

        ## ensuring consistency of duration and completion of ancestors
        task = self.get_task_by_name(task_name)

        if not task:

            matches = difflib.get_close_matches(task_name, [task.name for task in self.tasks])
            msg = f"Task '{task_name}' not found."
            if matches:
                msg += f" Did you mean: {', '.join(matches)}?"

            print(msg, file=sys.stderr)
            sys.exit(1)

        task.duration, task.completion = 0, 0

        ## removing the task from the list of tasks
        for ind, task in enumerate(self.tasks):

            if task.name == task_name:

                del self.tasks[ind]

            else:
                task.delete(task_name)

        ## saving the scheduler
        self.save_schedule()

    def get_task_by_name(self, name):

        return Task.find_task_by_name(name, self.tasks)

    ## basic algorithm for scheduling tasks
    ## - greedy approach: polling tasks in order of their deadlines and fitting their corresponding subtasks in the available time_slots

    def schedule_tasks(self, show_unscheduled=False):
        ## always scheduling as far ahead as possible (until we run out of either time_slots or tasks)
        ## announcing impossible to schedule tasks
        ## the order subtasks must be preserved in the schedule

        ## removing all past time_slots
        self.time_slot_management()

        ## finding minimal time slot covering
        self.time_slots = time_slot_covering(self.time_slots)

        ## removing all completed top-level tasks
        self.tasks = list(filter(lambda task: task.completion < 100, self.tasks))

        ## sorting the task list
        self.tasks.sort(key=lambda task: task.deadline)

        ## first collect all lowest_level tasks
        lowest_level_tasks = [p for task in self.tasks for p in Task.collect_lowest_level_tasks(task)]

        ## filter out the completed tasks:
        lowest_level_tasks = list(filter(lambda task: task.completion < 100, lowest_level_tasks))

        ## filter out the tasks with unset duration
        lowest_level_tasks = list(filter(lambda task: task.duration != 0, lowest_level_tasks))

        ## keep adding tasks to free time_slots until possible (while continuously checking for deadlines and tiem left available for the current clot)

        impossible_to_schedule = list()
        scheduling_result = dict()  ## task.name -> time_slot
        shift = 0
        iterator = iter(lowest_level_tasks)

        for ind, task in enumerate(iterator):

            for ind1, time_slot in enumerate(self.time_slots):

                ## calculating the remaining time for the current time slot
                available_time = (min(time_slot.end_time, task.deadline) - max(datetime.datetime.now(),
                                                                               time_slot.start_time)).total_seconds() / 60 - (
                                     0 if time_slot not in self.scheduled_tasks else
                                     sum([t.duration for t in self.scheduled_tasks[time_slot]]))


                task_root = task.get_root()

                if (task.duration <= available_time) and (task_root not in scheduling_result or scheduling_result[task_root] <= time_slot):

                    self.scheduled_tasks[time_slot].append(task)

                    scheduling_result[task.get_root()] = time_slot

                    break

                else:

                    if ind1 == len(self.time_slots) - 1:

                        impossible_to_schedule.append(task.name)

                        root = task.get_root()

                        while ind + shift + 1 < len(lowest_level_tasks) and lowest_level_tasks[

                            ind + shift + 1].get_root() is root:

                            shift += 1

                            next_task = next(iterator, None)  # defensive programming ig

                            if next_task is not None:
                                impossible_to_schedule.append(next_task.name)

        if len(impossible_to_schedule) > 0 and show_unscheduled:
            print("impossible_to_schedule:", ", ".join(impossible_to_schedule), file=sys.stderr)

    def get_next_task(self):
        """ returning a handle for the first uncompleted task """

        # choosing the first non-empty time_slot
        time_slot = None

        for ts in self.time_slots:

            if len(self.scheduled_tasks[ts]) > 0:
                time_slot = ts

                break

        if time_slot is None:
            print("No tasks scheduled.", file=sys.stderr)

        # extracting the first uncompleted task handle
        for task in self.scheduled_tasks[time_slot]:

            if task.completion == 100:  ## this can only happen after editing the json files manually

                continue

            return task

        return None

    def dead_tasks(self) -> List[Task]:
        """ returns a list of dead tasks """

        time_now = datetime.datetime.now()

        return list(filter(lambda s: (time_now - s.deadline).total_seconds() > 0, self.tasks))

    def to_dict(self):
        """ user data preprocessing for serialization"""

        return {
            "schedule_name": self.schedule_name,
            "time_slots": [time_slot.to_dict() for time_slot in self.time_slots],
            "tasks": [task.to_dict() for task in self.tasks],
        }

    def schedule_to_dict(self):
        """ schedule preprocessing for serialization """

        apply_to_dict = lambda x: list(map(lambda y: y.to_dict(), x))

        return [{"start_time": key.start_time.isoformat(), "end_time": key.end_time.isoformat(),
                 "tasks": list(apply_to_dict(self.scheduled_tasks[key]))} for key in self.scheduled_tasks.keys()]

    def save_schedule(self):

        script_dir = Path(__file__).parent

        path = script_dir / "../data" / self.schedule_name

        path.mkdir(exist_ok=True, parents=True)

        path_to_schedule = path.joinpath("schedule.json")

        path_to_state = path.joinpath("schedule_state.json")

        self.storage.save(path_to_state, self.to_dict())

        self.storage.save(path_to_schedule, self.schedule_to_dict())

    def load_scheduler(self):

        ## loading the initialization data from the json file
        path_to_state = Path(__file__).parent / "../data" / self.schedule_name / "schedule_state.json"

        try:
            state_json = self.storage.load(path_to_state)

        except FileNotFoundError:

            raise FileNotFoundError


        ## TaskScheduler object initialization
        self.schedule_name = state_json["schedule_name"]

        self.time_slots = list(map(lambda time_slot: TimeSlot(datetime.datetime.fromisoformat(time_slot["start_time"]),
                                                              datetime.datetime.fromisoformat(time_slot["end_time"])),
                                   state_json["time_slots"]))
        self.tasks = self._construct_tasks(state_json["tasks"])

    def load_schedule(self):

        ##loading the schedule data from the json file
        path_to_schedule = Path(__file__).parent / "../data" / self.schedule_name / "schedule.json"

        try:
            schedule_json = self.storage.load(path_to_schedule)

        except FileNotFoundError:

            raise FileNotFoundError

        ## schedule initialization

        for slot in schedule_json:
            self.scheduled_tasks[TimeSlot(datetime.datetime.fromisoformat(slot["start_time"]),
                                          datetime.datetime.fromisoformat(slot["end_time"]))] = deque(
                self._construct_tasks(slot["tasks"]))

    def _construct_tasks(self, tasks: List[Dict[str, Any]]) -> List[Task]:
        ## filter arguments for initialization of a Task object

        filter_dict = lambda d: {key: value for key, value in d.items() if
                                 key in inspect.signature(Task.__init__).parameters}

        filter_complement = lambda d: {key: value for key, value in d.items() if
                                       key not in inspect.signature(Task.__init__).parameters}

        constructed_tasks = list()
        for task in tasks:

            ## recursively construct the subtasks
            subtasks = self._construct_tasks(task["subtasks"])

            ## filter out key-value pairs that are not in the argument list of the Task constructor
            filtered_arguments = filter_dict(task)

            ## filter out key-value pairs that are in the argument list of the Task constructor
            argument_list_complement = filter_complement(task)

            ##construct the datetime object from iso format
            filtered_arguments["deadline"] = datetime.datetime.fromisoformat(filtered_arguments["deadline"])

            new_task = Task(**filtered_arguments)

            ## initializing the rest of the attributes (outside the constructor argument list)
            for key, value in argument_list_complement.items():
                setattr(new_task, key, value)

            new_task.subtasks = subtasks

            ## setting parent pointers to all task instances
            for t in new_task.subtasks:
                t.parent = new_task

            constructed_tasks.append(new_task)

        return constructed_tasks

    @staticmethod
    def delete_schedule(schedule_name):
        script_dir = Path(__file__).parent

        schedule_dir = script_dir / "../data" / schedule_name

        shutil.rmtree(schedule_dir)

    @staticmethod
    def merge_schedules(new_schedule_name, *args):

        schedulers = [TaskScheduler(name) for name in args]

        ## loading the schedulers
        for scheduler in schedulers:
            scheduler.load_scheduler()

        ## collect tasks and slots
        joint_tasks = [task for scheduler in schedulers for task in scheduler.tasks]
        joint_time_slots = [time_slot for scheduler in schedulers for time_slot in scheduler.time_slots]

        result_scheduler = TaskScheduler(new_schedule_name)

        result_scheduler.tasks = joint_tasks

        result_scheduler.time_slots = time_slot_covering(joint_time_slots)

        ## saving the schedule
        result_scheduler.save_schedule()


def main():
    ...


if __name__ == "__main__":
    main()
