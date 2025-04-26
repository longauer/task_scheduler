# Task Scheduler

A CLI-based task scheduling application with interactive mode and visualization capabilities.

## Features

- Create/manage multiple independent schedulers
- Define time slots with start/end times
- Create tasks with deadlines, durations, and descriptions
- Hierarchical task management with subtasks
- Multiple visualization modes:
- Gantt chart view
- Calendar view
- progress bars
- deadline warnings
- Automatic task scheduling with deadline awareness
- Interactive terminal UI
- Docker container support
- JSON-based persistent storage

## Installation

### Local Installation (pip)
```bash

git clone https://github.com/yourusername/task_scheduler.git
cd task_scheduler
pip install -e .
```

- package is also availabole at PyPI under the name task-scheduler-x
- it can be installed using

```bash
pip install task-scheduler-x
```



## Docker Installation
```bash
# Build image
docker build -t task-scheduler .

# Run with default command
docker run -it task-scheduler

# Run with specific command
docker run -it task-scheduler view_schedule MySchedule
```



## Basic Usage

### CLI Commands

#### Create new scheduler
task-scheduler create --name MySchedule

#### Add time slot
task-scheduler add_time_slot MySchedule \
  --start_time 2024-03-01T09:00 \
  --end_time 2024-03-01T11:00

#### Add task with subtasks
task-scheduler add_task MySchedule \
  --name "Project X" \
  --description "Main project" \
  --duration 300 \
  --deadline 2024-03-15T17:00

#### Generate schedule
task-scheduler schedule_tasks MySchedule

#### View visualizations
task-scheduler view_gantt MySchedule
task-scheduler view_calendar MySchedule --month 3



## Interactive Mode

### Launch with:
task-scheduler interactive MySchedule


#### Controls:

- ↑/↓ - Navigate tasks
- Enter - Select task
- a - Add new task
- m - Move task mode
- q - Quit


#### Features:

- Visual task hierarchy
- Vim-based task editing
- Drag-and-drop reorganization
- Real-time progress updates
- Color-coded deadlines





### Controls:
#### Navigation

- ↑/↓ - Navigate items in focused panel
- Tab - Switch between task/time slot panels
- clicking on a task - selects the task

#### Actions

- Enter - Select task/time slot
- a - Add new task/time slot (depending on focused panel)
- m - Enter move mode (tasks) / Modify slot (time slots)

#### General
- q - Quit application

#### Key Features:

Dual-Pane Interface

##### 📋 Left Panel - Task Hierarchy:

- Visual tree structure with nested subtasks

##### ⏱️ Right Panel - Time Slot Management:

- Chronological schedule view
- Duration calculations with time slot validation
- Enhanced Editing
- In-line time slot modification with instant validation
- Drag-and-drop reorganization (tasks)
- Keyboard-based time slot adjustments

#### New Features

- Split-screen workflow management
- Cross-panel task/time slot associations
- Real-time schedule validation
- Visual focus indicators (highlighted panel borders)
- Smart time slot sorting and gap detection

#### Feedback & Safety

- Instant save confirmation toasts
- Undo/redo stack for critical operations


## Data Format

data format for information fully describing the scheduler instance - JSON

example:
```JSON
{
  "schedule_name": "MySchedule",
  "time_slots": [
    {
      "start_time": "2024-03-01T09:00:00",
      "end_time": "2024-03-01T11:00:00"
    }
  ],
  "tasks": [
    {
      "name": "Design Phase",
      "description": "Initial design work",
      "deadline": "2024-03-05T17:00:00",
      "duration": 360,
      "completion": 45,
      "subtasks": [
        {
          "name": "UI Mockups",
          "duration": 120,
          "completion": 75
        }
      ]
    }
  ]
}
```

## Visualisation Examples

### Gantt Chart
task-scheduler view_gantt MySchedule

### Calendar View
task-scheduler view_calendar MySchedule --month 3

### Task Progress
task-scheduler view_task MySchedule "Design Phase"

output: 

```
=== Task Details: Design Phase ===

Name: Design Phase
Deadline: 2024-03-05T17:00:00
Completion: 45.0%
Duration: 360 min
Subtasks: ['UI Mockups']
Description: Initial design work

```


## Testing
```bash
python -m pytest tests/ -v
```



## Docker Support


The Docker image includes:

- Pre-configured Python environment

- Automatic dependency installation

- Persistent data storage

- Built-in test execution

To mount local data directory:
```bash
docker run -v $(pwd)/data:/app/data -it task-scheduler
```

To build the docker image run:
```bash
docker build -t task-scheduler .
```


## Requirements

- Python 3.7+
- colorama
- urwid
- pytest (for testing)


## Remarks and Recommendations for Users


- using the **view_next** command is the fastest way to view details about the next scheduled task

- each scheduler instance stores two data files: schedule_state.json (storing all information input by the user), schedule.json (storing the result of the latest scheduling).
  - rescheduling happens automatically after all kinds of edits and operations, not upon calling the command **view_schedule** or **view_next** however! This commands loads directly the schedule.json file, thus removing the need of schedule recalculation in series of view_schedule calls
  - you can use the command **schedule_tasks** to recalculate your schedule - this command also lists impossible-to-schedule tasks in the terminal assuming your current settings

- it may be a good idea to occasionally save a version of your scheduler. For this purpose the command **merge** can be used. Example: ``` task-scheduler merge -n MySchedule_backup -ns MySchedule ```
  
- note that the order in which subtasks are added to a task is respected in scheduling. This is useful in situations when subtasks depend on the completion of preceding subtasks

- it only has an effect to edit completion/duration attributes of leaf tasks (tasks with 0 subtasks) since these attributes of tasks higher in the hierarchy are calculated based on those of the leaf tasks

- conversely, it only has an effect to edit deadlines of top-level tasks (highest in the task hierarchy). Deadlines of the rest of the tasks always corresponds to that of their ancestor

- the **view_calendar** command only shows the number of tasks and total completion of tasks (weighed by duration) having deadlines on each given day (note: not being scheduled on but having a deadline on). To show more details about individual tasks due by a given day use **common_deadline**. Exapmle: ``` task-scheduler common_deadline MySchedule -m 12 -d 25``` (if you leave out the -m option the current month is chosen by default)

- this application requires that **vim** be installed on your system. In certain scenarios, vim motions can be more efficient than editing your settings through **interactive mode** e.g. adding multiple time slots. You can use the command **update_time_slots** to edit/add/remove your time slots using the vim interface. Another example would be editing deadline/description of a specific task. This you can too achieve through the vim interface using the **update_task** command leaving out the argument for the option --name/--description/--deadline. Example: ``` task-scheduler update_task MySchedule MyTask --description ```

- a colorful terminal application is required to get color-coded outputs in terminal

- the application was so far tuned mainly for Unix-based operating systems (it works in windows as well but operations in the **interactive mode** are recommended to be carried out mainly by mouse clicks to avoid lag)

- the pip installs the source files and the JSON data files in two separate directories. Consequently, upon reinstalling the package your data are not deleted from the file system on your machine. If you want to uninstall for good the data files have to be deleted manually - ``` pip -V ``` command can be used to find the path to the package installation. Then look for the data/ directory.





## Contributing

Fork the repository

Create your feature branch (git checkout -b feature/awesome-feature)

Commit your changes (git commit -am 'Add awesome feature')

Push to the branch (git push origin feature/awesome-feature)

Open a Pull Request
