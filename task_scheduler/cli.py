import argparse
import json
import datetime
import sys
import tempfile
from pathlib import Path
import difflib
from task_scheduler.scheduler import TaskScheduler
from task_scheduler.time_slot import TimeSlot
from task_scheduler.task import Task
from task_scheduler.utils import vim_extract, vim_edit, open_with_vim
from task_scheduler.visualisation import Visualisation
from task_scheduler.storage import Storage

from task_scheduler.interactive_mode import run_interactive_mode

class CommandProcessor:

    @staticmethod
    def save_scheduler(scheduler: TaskScheduler):

        scheduler.save_schedule()

    @staticmethod
    def create_scheduler(name):
        """Create a new TaskScheduler instance"""

        ## scheduler construction
        scheduler = TaskScheduler(name)

        ## saving the scheduler
        CommandProcessor.save_scheduler(scheduler)

        print(f"TaskScheduler '{name}' created.")

    @staticmethod
    def delete_scheduler(name):
        """ Delete a TaskScheduler instance """

        TaskScheduler.delete_schedule(name)

        print(f"TaskScheduler '{name}' deleted.")

    @staticmethod
    def load_scheduler(scheduler_name, load_schedule=False) -> TaskScheduler:
        """Initialize TaskScheduler from a JSON file"""

        scheduler = TaskScheduler(scheduler_name)

        try:
            scheduler.load_scheduler()

            if load_schedule:
                scheduler.load_schedule()

        except FileNotFoundError:

            print(f"Error: schedule with the given name not found.", file=sys.stderr)

            sys.exit(1)

        except json.JSONDecodeError:

            print(f"Error: Invalid JSON in configuration.", file=sys.stderr)

            sys.exit(1)

        return scheduler

    @staticmethod
    def merge_schedulers(new_schedule_name, *args):
        """ Merge one or more TaskSchedulers to one """

        TaskScheduler.merge_schedules(new_schedule_name, *args)
        print(f"Schedulers: {', '.join([s for s in args])} were merged to {new_schedule_name}.")

    @staticmethod
    def add_time_slot(scheduler_name, start_time, end_time):
        """Add a time slot to the TaskScheduler"""

        ## start_time and end_time are in isoformat

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## construct a datetime object
        time_slot = TimeSlot(datetime.datetime.fromisoformat(start_time), datetime.datetime.fromisoformat(end_time))

        scheduler.add_time_slot(time_slot)
        print(f"Time slot added - from {start_time} to {end_time}.")

        ## rescheduling
        scheduler.schedule_tasks()

        ## saving the scheduler
        CommandProcessor.save_scheduler(scheduler)

    @staticmethod
    def update_time_slots(scheduler_name):
        """ Display current time slots allowing editing """

        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## serialization
        serial = [time_slot.to_dict() for time_slot in scheduler.time_slots]

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w+", delete=False) as tmp_file:

            file_path = tmp_file.name

            Storage.save(file_path, serial)

            open_with_vim(file_path)

            new_time_slots = Storage.load(file_path)

            scheduler.time_slots = list(map(lambda x: TimeSlot.from_dict(x), new_time_slots))

        ## rescheduling the tasks
        scheduler.schedule_tasks()

        ## saving the schedule
        scheduler.save_schedule()

    @staticmethod
    def delete_time_slot(scheduler_name, start_time, end_time):
        """ Delete a time slot from the TaskScheduler """

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## constructing the time_slot
        time_slot = TimeSlot(datetime.datetime.fromisoformat(start_time), datetime.datetime.fromisoformat(end_time))

        scheduler.delete_time_slot(time_slot)

        print(f"Time slot deleted - from {start_time} to {end_time}.")

        ## rescheduling
        scheduler.schedule_tasks()

        scheduler.save_schedule()

    @staticmethod
    def add_task(scheduler_name, name, deadline=None, description=None, duration=None):
        """Add a task to the TaskScheduler"""

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## inputting the value of parameters through vim editor
        if name == "MISSING":
            name = vim_extract()

        if deadline == "MISSING":
            deadline = vim_extract()

        if description == "MISSING":
            description = vim_extract()

        ## construting the Task object
        task = Task(name=name, description=description, duration=duration, deadline= None if not deadline else datetime.datetime.fromisoformat(deadline))

        scheduler.add_task(task)

        print(f"Task '{name}' added.")

        ## rescheduling
        scheduler.schedule_tasks()

        ## saving the scheduler
        CommandProcessor.save_scheduler(scheduler)

    @staticmethod
    def delete_task(scheduler_name, task_name):
        """ Delete a task from the TaskScheduler"""

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## deleting the task
        scheduler.delete_task(task_name)

        print(f"Task '{task_name}' deleted.")

        ## rescheduling
        scheduler.schedule_tasks()

        ## saving the scheduler
        scheduler.save_schedule()

    @staticmethod
    def divide_task(scheduler_name, original_task_name, name, description=None, duration=None):
        """Divide a task"""

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## getting the task handle
        task = scheduler.get_task_by_name(original_task_name)

        if not task:
            matches = difflib.get_close_matches(original_task_name, [task.name for task in scheduler.tasks])
            msg = f"Task '{original_task_name}' not found."
            if matches:
                msg += f" Did you mean: {', '.join(matches)}?"
            print(msg, file=sys.stderr)
            sys.exit(1)

        ## creating a description file in the scheduler directory
        description_path = Path(__file__).parent / "../data" / scheduler.schedule_name / f"{name}.txt"

        description_path.touch(exist_ok=True)

        ## inputting missing arguments through vim editor
        if name == "MISSING":
            name = vim_extract()

        if description == "MISSING":
            description = vim_extract()

        ## adding the subtask to to the list of subtasks of the original task
        task.divide(name=name, description=description, duration=duration)

        print(f"Task '{name}' added to subtasks of {original_task_name}.")

        ## rescheduling
        scheduler.schedule_tasks()

        ## saving the scheduler
        CommandProcessor.save_scheduler(scheduler)

    @staticmethod
    def update_task(scheduler_name, task_name, name=None, description=None, duration=None, deadline=None, completion=None):
        """ Update a task's name/description/duration/completion/deadline """

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## getting the task handle
        task = scheduler.get_task_by_name(task_name)

        if task == None:
            matches = difflib.get_close_matches(task_name, [task.name for task in scheduler.tasks])
            msg = f"Task '{task_name}' not found."
            if matches:
                msg += f" Did you mean: {', '.join(matches)}?"
            print(msg, file=sys.stderr)
            sys.exit(1)

        ## inputting missing arguments through vim editor

        if name == "MISSING":
            name = vim_edit("" if task.description is None else task.description)

        if description == "MISSING":
            description = vim_edit("" if task.description is None else task.description)

        if deadline == "MISSING":
            deadline = vim_edit("" if task.deadline is None else task.deadline.isoformat()).strip()

        if name != None:

            task.name = name

        if description != None:

            task.description = description

        if duration != None:

            task.duration = duration

        if deadline != None:

            task.deadline = datetime.datetime.fromisoformat(deadline)

        if completion != None:

            task.completion = completion

        print(f"Task '{task_name}' updated.")

        ## rescheduling
        scheduler.schedule_tasks()

        ## saving the scheduler
        CommandProcessor.save_scheduler(scheduler)

    @staticmethod
    def completed_task(scheduler_name, task_name):
        """ Updating the task's status as completed """

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## top-level tasks are deleted
        task = scheduler.get_task_by_name(task_name)

        if not task:
            matches = difflib.get_close_matches(task_name, [task.name for task in scheduler.tasks])
            msg = f"Task '{task_name}' not found."
            if matches:
                msg += f" Did you mean: {', '.join(matches)}?"
            print(msg, file=sys.stderr)
            sys.exit(1)

        if not task.parent:
            CommandProcessor.delete_task(scheduler_name, task_name)

        else:
            CommandProcessor.update_task(scheduler_name, task_name, description=task.description, duration=task.duration, completion=100)

    @staticmethod
    def schedule_tasks(scheduler_name, show_unscheduled=False):
        """ Assigning the tasks to the time slots """

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## schedule tasks
        scheduler.schedule_tasks(show_unscheduled=show_unscheduled)

        ## saving the scheduler
        scheduler.save_schedule()

    @staticmethod
    def view_next_task(scheduler_name):
        """View the next scheduled task"""

        ## loading the scheduler and the schedule
        scheduler = CommandProcessor.load_scheduler(scheduler_name, load_schedule=True)

        ## getting the task handle
        next_task = scheduler.get_next_task()

        Visualisation.plot_single_task(scheduler, None if not next_task else next_task.name)

    @staticmethod
    def view_common_deadline(scheduler_name, year=None, month=None, day=None):
        """View task names sharing common deadline"""

        now = datetime.datetime.now()
        year = year or now.year
        month = month or now.month
        day = day or now.day

        ## loading the schedule
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        ## finding the tasks that match the specified deadline
        matching_tasks = list(filter(lambda x: x.deadline.year == year and x.deadline.month == month and x.deadline.day == day, scheduler.tasks))
        matching_tasks.sort()

        Visualisation.plot_common_deadline(matching_tasks, datetime.date(year, month, day))


    @staticmethod
    def view_schedule(scheduler_name):
        """view the schedule"""

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name, load_schedule=True)

        Visualisation.plot_schedule(scheduler)

    @staticmethod
    def view_calendar(scheduler_name, year, month):
        """ View the calendar """

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name, load_schedule=True)

        Visualisation.plot_calendar(scheduler, year, month)

    @staticmethod
    def view_gantt(scheduler_name):
        """View the schedule in the gantt view"""

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name, load_schedule=True)

        ## saving the scheduler
        scheduler.save_schedule()

        Visualisation.plot_gantt(scheduler)

    @staticmethod
    def view_task(scheduler_name, task_name):
        """View the task instance details """

        ## loading the scheduler and the schedule
        scheduler = CommandProcessor.load_scheduler(scheduler_name, load_schedule=True)

        ## getting the task handle
        task = scheduler.get_task_by_name(task_name)

        if not task:
            matches = difflib.get_close_matches(task_name, [task.name for task in scheduler.tasks])
            msg = f"Task '{task_name}' not found."
            if matches:
                msg += f" Did you mean: {', '.join(matches)}?"
            print(msg, file=sys.stderr)
            sys.exit(1)

        Visualisation.plot_single_task(scheduler, task_name)

    @staticmethod
    def view_dead(scheduler_name):
        """View tasks past their respective deadlines"""

        ## loading the scheduler
        scheduler = CommandProcessor.load_scheduler(scheduler_name)

        Visualisation.plot_dead_tasks(scheduler)


# Dictionary mapping commands to functions
COMMANDS = {
    "create": lambda args: CommandProcessor.create_scheduler(args.name),
    "wipe": lambda args: CommandProcessor.delete_scheduler(args.name),
    "load": lambda args: CommandProcessor.load_scheduler(args.scheduler_name),
    "merge": lambda args: CommandProcessor.merge_schedulers(args.name, *args.names),
    "add_time_slot": lambda args: CommandProcessor.add_time_slot(args.scheduler_name, args.start_time, args.end_time),
    "delete_time_slot": lambda args: CommandProcessor.delete_time_slot(args.scheduler_name, args.start_time, args.end_time),
    "update_time_slots": lambda args: CommandProcessor.update_time_slots(args.scheduler_name),
    "add_task": lambda args: CommandProcessor.add_task(args.scheduler_name, args.name, args.deadline, args.description, args.duration),
    "delete_task": lambda args: CommandProcessor.delete_task(args.scheduler_name, args.name),
    "update_task": lambda args: CommandProcessor.update_task(args.scheduler_name, args.task_name, args.name, args.description, args.duration, args.deadline, args.completion),
    "divide_task": lambda args: CommandProcessor.divide_task(args.scheduler_name, args.original_task_name, args.name, args.description, args.duration),
    "schedule_tasks": lambda args: CommandProcessor.schedule_tasks(args.scheduler_name, show_unscheduled=True),
    "view_next": lambda args: CommandProcessor.view_next_task(args.scheduler_name),
    "view_schedule": lambda args: CommandProcessor.view_schedule(args.scheduler_name),
    "view_calendar": lambda args: CommandProcessor.view_calendar(args.scheduler_name, args.year, args.month),
    "view_gantt": lambda args: CommandProcessor.view_gantt(args.scheduler_name),
    "view_task": lambda args: CommandProcessor.view_task(args.scheduler_name, args.name),
    "view_dead": lambda args: CommandProcessor.view_dead(args.scheduler_name),
    "common_deadline": lambda args: CommandProcessor.view_common_deadline(args.scheduler_name, args.year, args.month, args.day),
    "completed": lambda args: CommandProcessor.completed_task(args.scheduler_name, args.name),
    "interactive": lambda args: run_interactive_mode(args.scheduler_name)
}


# Main function to set up CLI
def parse_args():
    parser = argparse.ArgumentParser(prog='task_scheduler')
    subparsers = parser.add_subparsers(title='Operations', dest='command')

    # Subcommand: create
    create_parser = subparsers.add_parser('create', help='Create a TaskScheduler instance')
    create_parser.add_argument('-n', '--name', required=True, help='The name of the TaskScheduler')

    # Subcommand: wipe
    wipe_parser = subparsers.add_parser('wipe', help='Delete a TaskScheduler instance')
    wipe_parser.add_argument('name', help='The name of the TaskScheduler')

    # Subcommand: load
    load_scheduler_parser = subparsers.add_parser('load', help='Load TaskScheduler from JSON')
    load_scheduler_parser.add_argument('scheduler_name', help='Name of the scheduler to be loaded')

    # Subcommand: merge
    merge_scheduler_parser = subparsers.add_parser('merge', help='Merge TaskScheduler from JSON')
    merge_scheduler_parser.add_argument('-n', '--name', help='Name of the resulting scheduler')
    merge_scheduler_parser.add_argument('-ns', '--names', nargs="+", help='Name of the scheduler to be merged')

    # Subcommand: add_time_slot
    add_time_slot_parser = subparsers.add_parser('add_time_slot', help='Add a time slot to the TaskScheduler')
    add_time_slot_parser.add_argument('scheduler_name', help='Name of the scheduler for the time_slot to be added to')
    add_time_slot_parser.add_argument('-st', '--start_time', required=True, help='Start time of the time slot')
    add_time_slot_parser.add_argument('-et', '--end_time', required=True, help='End time of the time slot')

    # Subcommand: update_time_slots
    update_time_slot_parser = subparsers.add_parser('update_time_slots', help='Update a time slot from the TaskScheduler')
    update_time_slot_parser.add_argument('scheduler_name', help='Name of the scheduler for the time_slot to be updated')

    #Subcommand: delete_time_slot
    delete_time_slot_parser = subparsers.add_parser('delete_time_slot', help='Delete a time slot from the TaskScheduler')
    delete_time_slot_parser.add_argument('scheduler_name', help='Name of the scheduler for the time_slot to be deleted')
    delete_time_slot_parser.add_argument('-st', '--start_time', required=True, help='Start time of the time slot')
    delete_time_slot_parser.add_argument('-et', '--end_time', required=True, help='End time of the time slot')

    # Subcommand: add_task
    add_task_parser = subparsers.add_parser('add_task', help='Add a task to the TaskScheduler')
    add_task_parser.add_argument('scheduler_name', help='Name of the scheduler for the task to be added to')
    add_task_parser.add_argument('-n', '--name', nargs='?', const='MISSING', help='Name of the task')
    add_task_parser.add_argument('-desc', '--description', nargs='?', const='MISSING', help='Description of the task')
    add_task_parser.add_argument('-dur', '--duration', type=int, help='Duration of the task in minutes')
    add_task_parser.add_argument('-dl', '--deadline', type=str, nargs='?', const='MISSING', help='Deadline of the task in the iso format')

    # Subcommand: divide_task
    divide_task_parser = subparsers.add_parser('divide_task', help='Subdividing the task')
    divide_task_parser.add_argument('scheduler_name', help='Name of the scheduler for the time_slot to be added to')
    divide_task_parser.add_argument('original_task_name', help='Name of the task')
    divide_task_parser.add_argument('-n', '--name', nargs='?', const='MISSING', required=True, help='Name of the task')
    divide_task_parser.add_argument('-desc', '--description', nargs='?', const='MISSING', help='Description of the task')
    divide_task_parser.add_argument('-dur', '--duration', type=int, help='Duration of the task in minutes')


    # Subcommand: mark a task as completed
    completed_task = subparsers.add_parser('completed', help='Complete a task')
    completed_task.add_argument('scheduler_name', help='Name of the scheduler containing the completed task')
    completed_task.add_argument('name', help='Name of the task')

    # Subcommand: update_task
    update_task_parser = subparsers.add_parser('update_task', help='Update the name/description/duration/completion of a task')
    update_task_parser.add_argument('scheduler_name', help='Name of the scheduler to be updated')
    update_task_parser.add_argument('task_name', help='Name of the task to update')
    update_task_parser.add_argument('-n', '--name', nargs='?', const='MISSING', help='New name for the task')
    update_task_parser.add_argument('-desc', '--description', nargs='?', const='MISSING', help='New description for the task')
    update_task_parser.add_argument('-dl', '--deadline', nargs='?', const='MISSING', help='New deadline for the task')
    update_task_parser.add_argument('-dur', '--duration', nargs='?', type=int, help='New duration for the task in minutes')
    update_task_parser.add_argument('-c', '--completion', type=int, help='New completion for the task in percentage')

    # Subcommand: delete_task
    delete_task_parser = subparsers.add_parser('delete_task', help='Delete a task from the TaskScheduler')
    delete_task_parser.add_argument('scheduler_name', help='Name of the scheduler to be deleted')
    delete_task_parser.add_argument('name', help='Name of the task to be deleted')

    # Subcommand: schedule_tasks
    schedule_tasks_parser = subparsers.add_parser('schedule_tasks', help='Schedule tasks')
    schedule_tasks_parser.add_argument('scheduler_name', help='Name of the scheduler to be scheduled')

    # Subcommand: view_next_task
    view_next_task_parser = subparsers.add_parser('view_next', help='View the next scheduled task')
    view_next_task_parser.add_argument("scheduler_name", help="Name of the scheduler")

    # Subcommand: view_schedule
    view_schedule_parser = subparsers.add_parser('view_schedule', help='View the schedule')
    view_schedule_parser.add_argument('scheduler_name', help='Name of the scheduler')

    # Subcommand: view_calendar
    view_calendar_parser = subparsers.add_parser('view_calendar', help='View the calendar')
    view_calendar_parser.add_argument('scheduler_name', help='Name of the scheduler')
    view_calendar_parser.add_argument( '-y', '--year', type=int, help='Specify the year')
    view_calendar_parser.add_argument('-m', '--month', type=int, help='Specify the month')

    # Subcommand: view_gantt
    view_gantt_parser = subparsers.add_parser('view_gantt', help='View the gantt')
    view_gantt_parser.add_argument('scheduler_name', help='Name of the scheduler')

    # Subcommand: view_dead
    view_dead_parser = subparsers.add_parser('view_dead', help='View tasks past their deadlines')
    view_dead_parser.add_argument('scheduler_name', help='Name of the scheduler')

    # Subcommand: common_deadline
    common_deadline_parser = subparsers.add_parser('common_deadline', help='Common deadline')
    common_deadline_parser.add_argument('scheduler_name', help='Name of the scheduler')
    common_deadline_parser.add_argument('-y', '--year', type=int, help='Specify the year')
    common_deadline_parser.add_argument('-m', '--month', type=int, help='Specify the month')
    common_deadline_parser.add_argument('-d', '--day', type=int, help='Specify the day')

    # Subcommand: view_task
    view_task_parser = subparsers.add_parser('view_task', help='View the task')
    view_task_parser.add_argument('scheduler_name', help='Name of the scheduler')
    view_task_parser.add_argument('name', help='Name of the task')

    # Subcommand: interactive_mode
    interactive_parser = subparsers.add_parser("interactive", help="Launch interactive mode")
    interactive_parser.add_argument("scheduler_name", help="Name of the scheduler")

    # Parse the arguments
    args = parser.parse_args()


    if args.command in COMMANDS:

        COMMANDS[args.command](args)

    else:

        print("Unknown command. Use 'task_scheduler --help' to see available commands.")

if __name__ == '__main__':
    ...
