"""! @file utils.py
@brief Utility functions for task scheduling system
@author Samuel Longauer

@defgroup utils Utilities Module
@brief Provides helper functions for time calculations, Vim integration, and time slot management
"""
import argparse
import datetime
from task_scheduler.time_slot import TimeSlot
from typing import List, Dict, Any
import subprocess
from task_scheduler.task import Task
import tempfile
import os
import sys

def time_till_deadline(task: Task) -> int:
    """! @brief Calculate remaining time until task deadline
    
    @ingroup utils
    
    @param task Task object to check
    @return Remaining time in seconds as integer
    @note Returns negative values if deadline has passed
    """
    time_now = datetime.datetime.now()
    deadline = task.deadline
    return (deadline - time_now).total_seconds()

def set_time_to_midnight(date_obj: datetime.date) -> datetime.datetime:
    """! @brief Extends a datetime.date object to a datetime.datetime object with the time set to 00:00.

    @ingroup utils

    @param date_obj datetime.date object to extend
    @return datetime.datetime object with the time set to 00:00
    """
    midnight = datetime.time.min  # Represents 00:00:00
    datetime_at_midnight = datetime.datetime.combine(date_obj, midnight)
    return datetime_at_midnight
def parse_relative_date(relative_date: str) -> datetime.datetime:
    """! @brief Initialize a date object from a relative date string

    @ingroup utils

    @param relative_date Relative date string
    @return datetime.date object representing date
    @note raises ValueError if relative date is not valid
    """
    day_str, shift_str = relative_date.split('+')
    shift = int(shift_str)

    today = datetime.date.today()

    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    match day_str.lower():
        case "today":
            return set_time_to_midnight(today + datetime.timedelta(days=shift))
        case day if day in days_of_week:
            target_day_index = days_of_week.index(day)
            today_index = today.weekday()  # Monday is 0, Sunday is 6
            days_ahead = (target_day_index - today_index + 7) % 7
            return set_time_to_midnight(today + datetime.timedelta(days=days_ahead + 7 * (shift) if shift > 0 else days_ahead))
        case _:
            raise ValueError(f"Invalid day: {day_str}")



def time_slot_covering(timeslots: List[TimeSlot]) -> List[TimeSlot]:
    """! @brief Create minimal non-overlapping time slot coverage
    
    @ingroup utils
    
    @param timeslots List of potentially overlapping TimeSlot objects
    @return List of merged non-overlapping TimeSlot objects
    @note Uses sweep line algorithm to merge overlapping intervals
    
    @details Algorithm steps:
    1. Split time slots into start/end markers
    2. Sort markers with start times before end times at same timestamp
    3. Process markers to count overlapping intervals
    4. Create new slots when overlap count transitions between 0
    """
    
    ## split to start-times and end-times

    start_times = [(slot.start_time, 0) for slot in timeslots]
    end_times = [(slot.end_time, 1) for slot in timeslots]

    ## merge sorted lists such that starts of identical times will precede ends
    joint_slots = start_times + end_times
    joint_slots.sort()

    # perform the algorithm to find non-overlapping timeslot coverage

    result_slots = list()
    diff = 0
    new_start_slot = None

    for slot, type in joint_slots:

        if type == 0:

            if diff == 0:

                new_start_slot = slot

            diff += 1

        else:
            diff -= 1

        if diff == 0:

            assert type == 1 ## the current slot must be an end

            result_slots.append(TimeSlot(new_start_slot, slot))

    return result_slots


def open_with_vim(file_path: str) -> None:
    """! @brief Open file in Vim editor with platform-specific handling
    
    @ingroup utils
    
    @param file_path Path to file to edit
    @exception subprocess.CalledProcessError If editor launch fails
    @note Uses gvim on Windows for better window management
    """
    if sys.platform == "win32":
        subprocess.run(
            f'start /WAIT gvim -c "set fileformat=unix" "{file_path}"',
            shell=True,
            check=True
        )
    else:
        subprocess.run(['vim', file_path])

def vim_edit(content: str) -> str:
    """! @brief Edit content in Vim and return modified version
    
    @ingroup utils
    
    @param content Initial text content to edit
    @return Modified content after editor closes
    @note Handles Windows file locking and line endings
    """
    with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=".txt",
            delete=False,
            newline='\n',
            encoding='utf-8'
    ) as tmp_file:
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        open_with_vim(tmp_path)
        with open(tmp_path, 'r', encoding='utf-8') as f:
            return f.read().replace('\r\n', '\n')
    finally:
        os.remove(tmp_path)

def vim_extract() -> str:
    """! @brief Create new content in Vim from empty file
    
    @ingroup utils
    
    @return Content created in editor
    @note Handles Windows file locking explicitly
    """
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    tmp_file.close()

    open_with_vim(tmp_path)

    with open(tmp_path, "r", newline='') as f:
        content = f.read()

    os.remove(tmp_path)
    return content


def main():
    ...

if __name__ == "__main__":
    main()
