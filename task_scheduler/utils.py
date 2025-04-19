import datetime
from task_scheduler.time_slot import TimeSlot
from typing import List, Dict, Any
import subprocess
from task_scheduler.task import Task
import tempfile
import os
import sys

## returning remaining time till deadline in seconds
def time_till_deadline(task: Task) -> int:
    time_now = datetime.datetime.now()
    deadline = task.deadline
    return (deadline - time_now).total_seconds()

## constructing minimal non-overlapping time_slot covering
def time_slot_covering(timeslots: List[TimeSlot]) -> List[TimeSlot]:

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


import datetime
from task_scheduler.time_slot import TimeSlot
from typing import List, Dict, Any
import subprocess
from task_scheduler.task import Task
import tempfile
import os
import sys


## returning remaining time till deadline in seconds
def time_till_deadline(task: Task) -> int:
    time_now = datetime.datetime.now()
    deadline = task.deadline
    return (deadline - time_now).total_seconds()


## constructing minimal non-overlapping time_slot covering
def time_slot_covering(timeslots: List[TimeSlot]) -> List[TimeSlot]:
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
            assert type == 1  ## the current slot must be an end

            result_slots.append(TimeSlot(new_start_slot, slot))

    return result_slots


def open_with_vim(file_path: str) -> None:
    """Proper Windows Vim launcher that waits for user input"""
    if sys.platform == "win32":
        subprocess.run(
            f'start /WAIT gvim -c "set fileformat=unix" "{file_path}"',
            shell=True,
            check=True
        )
    else:
        subprocess.run(['vim', file_path])


def vim_edit(content: str) -> str:
    """Universal editor function with Windows fix"""
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

        # Read back with Windows file locking workaround
        with open(tmp_path, 'r', encoding='utf-8') as f:
            return f.read().replace('\r\n', '\n')
    finally:
        os.remove(tmp_path)


def vim_extract() -> str:
    """Universal version that handles Windows file locking"""
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    tmp_file.close()  # Explicit close for Windows compatibility

    open_with_vim(tmp_path)

    with open(tmp_path, "r", newline='') as f:  # Universal newline support
        content = f.read()

    os.remove(tmp_path)
    return content
