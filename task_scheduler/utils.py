import datetime
from task_scheduler.time_slot import TimeSlot
from typing import List, Dict, Any
import subprocess
from task_scheduler.task import Task
import tempfile
import os

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

def open_with_vim(file_path: str) -> None:
    subprocess.run(['vim', file_path])

def vim_extract() -> str:
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    open_with_vim(tmp_path)

    # Reopen the file for reading after vim edits
    with open(tmp_path, "r") as f:
        content = f.read()

    os.remove(tmp_path)

    return content

def vim_edit(content: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w+", delete=False) as tmp_file:
        tmp_file.write(content)
        tmp_file.flush()
        tmp_path = tmp_file.name

    open_with_vim(tmp_path)

    # Reopen to read after vim edit
    with open(tmp_path, "r") as f:
        edited_content = f.read()

    os.remove(tmp_path)

    return edited_content
