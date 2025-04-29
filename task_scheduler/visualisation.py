"""! @file visualization.py
@brief Visualization module for task scheduling system
@author Samuel Longauer

@defgroup utils Utilities Module
@brief Provides visualization components for task scheduling system
"""

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
    """! @brief Visualization handler for task scheduling system
    
    @ingroup utils
    
    Provides multiple visualization formats including schedules, Gantt charts,
    and calendar views with color-coded task status indicators.
    """

    @staticmethod
    def get_task_color(task, config=None):
        """! @brief Determine color coding for task based on deadline proximity
        
        @param task Task object to evaluate
        @param config Optional dictionary with custom threshold values (seconds)
               Default thresholds:
               - critical: 86400 (1 day)
               - high: 259200 (3 days)
               - medium: 432000 (5 days)
               - low: 604800 (7 days)
        @return Colorama style string combination
        """
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
        """! @brief Display formatted task schedule
        
        @param scheduler TaskScheduler instance to visualize
        @details Shows time slots with associated tasks and progress bars
        """
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
        """! @brief Generate text-based progress bar
        
        @param completion Percentage completion (0-100)
        @return String representation of progress bar
        """
        filled_blocks = int((completion / 100) * 20)
        empty_blocks = 20 - filled_blocks
        return "[" + "#" * filled_blocks + "-" * empty_blocks + "]"

    @staticmethod
    def plot_single_task(scheduler, task_name):
        """! @brief Display detailed view of a single task
        
        @param scheduler TaskScheduler instance containing the task
        @param task_name Name of task to display
        """
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

    @staticmethod
    def plot_dead_tasks(scheduler):
        """! @brief Display overdue tasks
        
        @param scheduler TaskScheduler instance to analyze
        """
        print(f" \n=== Dead Tasks ===\n")
        dead_tasks = scheduler.dead_tasks()
        time_now = datetime.datetime.now()
        for task in dead_tasks:
            time_past_deadline = (time_now - task.deadline).total_seconds()
            print(f"Task {task.name} is {time_past_deadline // 3600:.0f} hours and {time_past_deadline % 3600 // 60:.0f} minutes past its deadline.\n")

    @staticmethod
    def plot_common_deadline(tasks: List[Task], deadline: datetime):
        """! @brief Visualize tasks sharing a common deadline
        
        @param tasks List of Task objects
        @param deadline Common deadline to display
        """
        print(f"\n=== Tasks with common deadline: {deadline} ===\n")
        for task in tasks:
            print(task)

    @staticmethod
    def plot_gantt(scheduler, days=7):
        """! @brief Generate Gantt chart visualization
        
        @param scheduler TaskScheduler instance to visualize
        @param days Number of days to display from current time
        """
        print("\n=== Gantt View ===\n")
        now = datetime.datetime.now()
        timescale = [now + datetime.timedelta(hours=h) for h in range(24 * days)]
        timeline_width = len(timescale)
        task_map = defaultdict(list)
        
        for time_slot, tasks in scheduler.scheduled_tasks.items():
            for task in tasks:
                task_map[task].append(time_slot)

        for task, slots in task_map.items():
            timeline = [' '] * timeline_width
            for slot in slots:
                start_rel = (slot.start_time - now).total_seconds() / 3600
                end_rel = (slot.end_time - now).total_seconds() / 3600
                start_idx = max(0, int(start_rel))
                end_idx = min(timeline_width, int(end_rel))
                for i in range(start_idx, end_idx):
                    timeline[i] = "▇"
            time_line = ''.join(timeline)
            print(f"{task.name[:15].ljust(15)} │ {time_line}")

    @staticmethod
    def plot_calendar(scheduler, year=None, month=None):
        """! @brief Display calendar view with task deadlines
        
        @param scheduler TaskScheduler instance to visualize
        @param year Optional year to display (default: current)
        @param month Optional month to display (default: current)
        """
        now = datetime.datetime.now()
        year = year or now.year
        month = month or now.month
        today = now.day
        cal = monthcalendar(year, month)

        STYLES = {
            'header': Style.BRIGHT + Fore.LIGHTBLUE_EX,
            'grid': Fore.LIGHTWHITE_EX,
            'today': Back.CYAN + Fore.BLACK,
            'high': Fore.GREEN,
            'medium': Fore.YELLOW,
            'low': Fore.RED,
            'reset': Style.RESET_ALL
        }

        CELL_WIDTH = 12
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

            day_str = f"{day:2}"
            content = f"{day_str}"

            if tasks:
                count = len(tasks)
                overall_completion = sum(t.completion*(0 if not t.duration else t.duration) for t in tasks) / max(1, sum((0 if not t.duration else t.duration) for t in tasks))
                color = STYLES['high']
                if overall_completion < 75: color = STYLES['medium']
                if overall_completion < 25: color = STYLES['low']
                task_info = f" ({count}) {int(overall_completion)}%"
                content += f"{color}{task_info}{STYLES['reset']}"

            if is_today:
                content = f"{STYLES['today']}{content}{STYLES['reset']}"
            return pad_cell(content, CELL_WIDTH)

        print("\n=== Calendar view ===")
        header = f"{STYLES['header']}{month_name[month]} {year}{STYLES['reset']}"
        print(f"\n {header}\n")
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
