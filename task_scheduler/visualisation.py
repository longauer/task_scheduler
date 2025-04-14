import sys
import datetime
from task_scheduler.task import Task
from task_scheduler.scheduler import TaskScheduler
from task_scheduler.utils import time_till_deadline
from calendar import monthcalendar, month_name
from collections import defaultdict
import re
from typing import List

from colorama import Fore, Back, Style, init

init(autoreset=True)



class Visualisation:

    @staticmethod
    def get_task_color(task, config=None):
        thresholds = config or {
            'critical': 86400,  # 1 day
            'high': 259200,  # 3 days
            'medium': 432000,  # 5 days
            'low': 604800  # 7 days
        }
        remaining = time_till_deadline(task)

        if remaining < 0:
            return Fore.WHITE + Back.RED + Style.BRIGHT  # Overdue styling
        elif remaining < thresholds['critical']:
            return Style.BRIGHT + Fore.GREEN
        elif remaining < thresholds['high']:
            return Fore.RED
        elif remaining < thresholds['medium']:
            return Fore.LIGHTRED_EX
        elif remaining < thresholds['low']:
            return Fore.YELLOW
        return Fore.WHITE
    @staticmethod
    def plot_schedule(scheduler):

        table_constant = 0

        print("\n=== Task Schedule Visualisation ===\n")
        for time_slot in scheduler.time_slots:

            start = time_slot.start_time

            end = time_slot.end_time

            tasks = scheduler.scheduled_tasks[time_slot]

            table_constant = 0 if not len(tasks) else max([len(x.name) for x in tasks]) + 5

            print(f"Time Slot: {start} - {end}")

            print("‾" * 52)

            for task in tasks:

                name = task.name

                coloring = Visualisation.get_task_color(task)

                completion = task.completion

                progress_bar = Visualisation.create_progress_bar(completion)

                print(coloring + f"{name.ljust(table_constant)} {progress_bar} {completion:.1f}% Complete | est. duration {task.duration:.1f} min")

            print("\n")

        top_level_tasks = list(filter(lambda task: not task.parent, scheduler.tasks))

        print("\n=== Top-level Tasks ===\n")

        table_constant = 0 if not len(top_level_tasks) else max([len(task.name) for task in top_level_tasks]) + 5

        for task in top_level_tasks:

            name = task.name

            coloring = Visualisation.get_task_color(task)

            completion = task.completion

            progress_bar = Visualisation.create_progress_bar(completion)

            print(coloring + f"{name.ljust(table_constant)} {progress_bar} {completion:.1f}% Complete")

        print("\n")

    @staticmethod
    def create_progress_bar(completion):

        filled_blocks = int((completion / 100) * 20)

        empty_blocks = 20 - filled_blocks

        return "[" + "#" * filled_blocks + "-" * empty_blocks + "]"

    @staticmethod
    def plot_single_task(scheduler, task_name):

        ## helper lambda for extractint names out of
        ## extract_names = lambda ls: list(map(lambda task: task.name, ls))


        print(f"\n=== Task Details: {task_name} ===\n")

        task = scheduler.get_task_by_name(task_name)


        if task:

            print(f"Task: {task.name}")
            print(f"Deadline: {task.deadline}")
            print(f"Completion: {task.completion}%")
            print(f"Duration: {task.duration} min")
            print(f"Parent: {None if not task.parent else task.parent.name}")
            print("subtasks:"); print((lambda ls: list(map(lambda task: task.name, ls)))(task.subtasks))
            print(f"Description: \n{task.description}")
            print("\n")
            return
    @staticmethod
    def plot_dead_tasks(scheduler):

        print(f" \n=== Dead Tasks ===\n")

        dead_tasks = scheduler.dead_tasks()

        time_now = datetime.datetime.now()

        for task in dead_tasks:

            time_past_deadline = (time_now - task.deadline).total_seconds()

            print(f"Task {task.name} is {time_past_deadline // 3600:.0f} hours and {time_past_deadline % 3600 // 60:.0f} minutes past its deadline.\n")

    @staticmethod
    def plot_common_deadline(tasks: List[Task], deadline: datetime):
        """ Visualize tasks sharing common deadline"""

        print(f"\n=== Tasks with common deadline: {deadline} ===\n")
        for task in tasks:
            print(task)


    @staticmethod
    def plot_gantt(scheduler, days=7):
        """Visualize scheduled tasks in a Gantt chart format"""
        print("\n=== Gantt View ===\n")
        now = datetime.datetime.now()

        # Create timeline buckets (1 hour increments)
        timescale = [now + datetime.timedelta(hours=h) for h in range(24 * days)]
        timeline_width = len(timescale)

        # Map tasks to their time slots
        task_map = defaultdict(list)
        for time_slot, tasks in scheduler.scheduled_tasks.items():
            for task in tasks:
                task_map[task].append(time_slot)

        # Build visualization
        for task, slots in task_map.items():
            timeline = [' '] * timeline_width

            for slot in slots:
                # Calculate position in timeline
                start_rel = (slot.start_time - now).total_seconds() / 3600
                end_rel = (slot.end_time - now).total_seconds() / 3600

                # Convert to timeline indices
                start_idx = max(0, int(start_rel))
                end_idx = min(timeline_width, int(end_rel))

                # Fill the time period
                for i in range(start_idx, end_idx):
                    timeline[i] = "▇"  # Unicode block character

            # Print task row
            time_line = ''.join(timeline)
            print(f"{task.name[:15].ljust(15)} │ {time_line}")

    @staticmethod
    def plot_calendar(scheduler, year=None, month=None):
        now = datetime.datetime.now()
        year = year or now.year
        month = month or now.month
        today = now.day
        cal = monthcalendar(year, month)

        # Style configurations
        STYLES = {
            'header': Style.BRIGHT + Fore.LIGHTBLUE_EX,
            'grid': Fore.LIGHTWHITE_EX,
            'today': Back.CYAN + Fore.BLACK,
            'high': Fore.GREEN,
            'medium': Fore.YELLOW,
            'low': Fore.RED,
            'reset': Style.RESET_ALL
        }

        CELL_WIDTH = 12  # Wider cells for better information display
        GRID_CHAR = "─"

        def visible_len(s):
            return len(re.sub(r'\x1b\[[0-9;]*m', '', s))

        def pad_cell(content, width):
            padding = max(width - visible_len(content), 0)
            return content + " " * padding

        def format_day(day):
            if day == 0:
                return " " * CELL_WIDTH

            is_today = day == today and month == now.month
            tasks = [t for t in scheduler.tasks
                     if t.deadline and t.deadline.year == year
                     and t.deadline.month == month
                     and t.deadline.day == day]

            # Base content with day number
            day_str = f"{day:2}"
            content = f"{day_str}"

            if tasks:
                count = len(tasks)
                overall_completion = sum(t.completion*(0 if not t.duration else t.duration) for t in tasks) / max(1, sum((0 if not t.duration else t.duration) for t in tasks))

                # Color coding for completion percentage
                color = STYLES['high']
                if overall_completion < 75: color = STYLES['medium']
                if overall_completion < 25: color = STYLES['low']

                # Format task info
                task_info = f" ({count}) {int(overall_completion)}%"
                content += f"{color}{task_info}{STYLES['reset']}"

            # Apply today's background
            if is_today:
                content = f"{STYLES['today']}{content}{STYLES['reset']}"

            return pad_cell(content, CELL_WIDTH)

        print("\n=== Calendar view ===")

        # Header
        header = f"{STYLES['header']}{month_name[month]} {year}{STYLES['reset']}"
        print(f"\n {header}\n")

        # Grid
        print(f"{STYLES['grid']}┌{'┬'.join([GRID_CHAR * CELL_WIDTH] * 7)}┐")
        print(f"│{'│'.join([f'{day:^{CELL_WIDTH}}' for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']])}│")
        print(f"╞{'╪'.join([GRID_CHAR * CELL_WIDTH] * 7)}╡")

        for week in cal:
            days = []
            for day in week:
                days.append(format_day(day))
            print(f"{STYLES['grid']}│{'│'.join(days)}│")

            print(f"{STYLES['grid']}├{'┼'.join([GRID_CHAR * CELL_WIDTH] * 7)}┤")

        print(f"{STYLES['grid']}└{'┴'.join([GRID_CHAR * CELL_WIDTH] * 7)}┘{STYLES['reset']}")

        # Legend
        legend = [
            f"\n{STYLES['header']}Legend:{STYLES['reset']}",
            f"{STYLES['today']} 15 (2) 50% {STYLES['reset']} - Today's tasks example",
            f"{STYLES['high']}XX (X) 75%{STYLES['reset']} - High completion (≥75%)",
            f"{STYLES['medium']}XX (X) 50%{STYLES['reset']} - Medium completion (25-74%)",
            f"{STYLES['low']}XX (X) 10%{STYLES['reset']} - Low completion (<25%)"
        ]
        print("\n".join(legend))




if __name__ == "__main__":
    ...
