import urwid
from task_scheduler.scheduler import TaskScheduler
from task_scheduler.utils import vim_edit
from task_scheduler.task import Task
import datetime
import sys


class InteractiveApp:
    def __init__(self, scheduler_name):
        self.scheduler_name = scheduler_name
        self.scheduler = self.load_scheduler(scheduler_name)
        self.main_loop = None
        self.listbox = None
        self.body_walker = None
        self.selected_task_to_move = None
        self.move_mode_active = False

        # Define color palette
        self.palette = [
            ('header', 'white', 'dark blue'),
            ('footer', 'white', 'dark blue'),
            ('reversed', 'black', 'light gray'),
            ('selected_task', 'white', 'dark green'),
            ('cancel_button', 'white', 'dark red'),
            ('error', 'white', 'dark red'),
            ('success', 'white', 'dark green'),
            ('loading', 'yellow', 'black')
        ]

        # Initialize UI components
        self.header = urwid.Text(f"📅 Interactive Task Manager - {self.scheduler_name}", align='center')
        self.footer = urwid.Text("↑↓ navigate | Enter select/move | m toggle move | a add | q quit", align='center')

        # Create initial empty listbox
        self.body_walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.body_walker)
        self.frame = urwid.Frame(
            header=urwid.AttrMap(self.header, 'header'),
            body=self.listbox,
            footer=urwid.AttrMap(self.footer, 'footer')
        )

        # Initial refresh
        self.refresh_view()

    def load_scheduler(self, name):
        """Load scheduler with proper error handling"""
        try:
            scheduler = TaskScheduler(name)
            scheduler.load_scheduler()
            scheduler.load_schedule()
            return scheduler
        except Exception as e:
            print(f"Failed to load scheduler: {e}", file=sys.stderr)
            sys.exit(1)

    def start(self):
        """Start the main loop with proper initialization"""
        self.main_loop = urwid.MainLoop(
            self.frame,
            palette=self.palette,
            unhandled_input=self.handle_input
        )
        try:
            self.main_loop.run()
        except Exception as e:
            print(f"Error in main loop: {e}", file=sys.stderr)
            sys.exit(1)

    def refresh_view(self, maintain_focus=False):
        """Refresh the view while maintaining focus position"""
        try:
            # Store current focus
            old_focus = None
            if maintain_focus and self.listbox:
                focus_widget, _ = self.listbox.get_focus()
                old_focus = getattr(focus_widget, 'original_task', None) if focus_widget else None

            # Rebuild task list
            items = []
            # Ensure tasks is a list to prevent 'Task' is not iterable
            tasks = self.scheduler.tasks
            if not isinstance(tasks, list):
                tasks = [tasks] if isinstance(tasks, Task) else []
            self._build_task_widgets(items, tasks)

            # Add controls
            items.append(urwid.Divider())
            items.append(urwid.AttrMap(
                urwid.Button("➕ Add New Task", on_press=self.add_new_task),
                None, focus_map='reversed'
            ))

            if self.move_mode_active:
                items.append(urwid.Divider())
                items.append(urwid.AttrMap(
                    urwid.Button("❌ Cancel Move", on_press=self.cancel_move),
                    'cancel_button', focus_map='reversed'
                ))

            # Update widgets
            self.body_walker[:] = items  # Update existing walker
            self.listbox.body = self.body_walker  # Ensure listbox is connected

            # Restore focus
            if maintain_focus and old_focus:
                for idx, item in enumerate(items):
                    if hasattr(item, 'original_task') and item.original_task == old_focus:
                        self.listbox.set_focus(idx)
                        break

        except Exception as e:
            self.footer.set_text(("error", f"Refresh error: {str(e)}"))
            # Fallback to full reset if refresh fails
            self.body_walker[:] = [urwid.Text("Error refreshing view")]
            self.listbox.body = self.body_walker

    def _build_task_widgets(self, items, tasks, depth=0):
        """Build task widgets recursively"""
        for task in tasks:
            prefix = "👉" if (
                        self.move_mode_active and task == self.selected_task_to_move) else "📌" if task == self.selected_task_to_move else "•"
            attr = 'selected_task' if task == self.selected_task_to_move else None

            label = f"{' ' * (depth * 4)}{prefix} {task.name}"
            btn = urwid.Button(label, on_press=self.on_task_click, user_data=task)
            btn_map = urwid.AttrMap(btn, attr, focus_map='reversed')
            btn_map.original_task = task
            items.append(btn_map)

            if task.subtasks:
                self._build_task_widgets(items, task.subtasks, depth + 1)

    def drop_task(self):
        """Final working version of task movement"""
        focus_widget, _ = self.listbox.get_focus()
        if not (focus_widget and hasattr(focus_widget, 'original_task')):
            self.footer.set_text(("error", "No valid target selected"))
            return

        target_task = focus_widget.original_task
        task_to_move = self.selected_task_to_move

        # Validate the move
        if not self._validate_move(task_to_move, target_task):
            return

        # Perform the move
        if not self._execute_move(task_to_move, target_task):
            return

        self._finalize_move()

    def _validate_move(self, task_to_move, target_task):
        """Check if move is valid"""
        if target_task == task_to_move:
            self.footer.set_text(("error", "Cannot move task to itself"))
            return False
        if self._is_child_of(task_to_move, target_task):
            self.footer.set_text(("error", "Cannot create circular dependency"))
            return False
        return True

    def _execute_move(self, task_to_move, target_task):
        """Perform the actual movement of tasks"""

        # Remove from current position
        name = task_to_move.name
        description = task_to_move.description
        duration = task_to_move.duration

        if not self._remove_task(task_to_move):
            self.footer.set_text(("error", "Failed to remove from current position"))
            return False

        # Add to new position
        # target_task.subtasks.append(task_to_move)
        # task_to_move.parent = target_task

        target_task.divide(name=name, description=description, duration=duration)
        self.scheduler.schedule_tasks()
        self.scheduler.save_schedule()



        # self.scheduler.schedule_tasks()
        # self.scheduler.save_schedule()
        return True

    def _finalize_move(self):
        """Complete the move operation"""
        self.move_mode_active = False
        self.selected_task_to_move = None

        try:
            self.footer.set_text(("success", "Task moved successfully"))
            self.refresh_view(maintain_focus=True)
        except Exception as e:
            self.footer.set_text(("error", f"Save failed: {str(e)}"))
            # Revert if save failed
            self.refresh_view()

    def _remove_task(self, task_to_remove):
        """Remove task from current position in hierarchy"""
        # Check top-level tasks first
        # if task_to_remove in self.scheduler.tasks:
        #     self.scheduler.delete_task(task_to_remove.name)
        #     return True
        #
        # # Search through all subtasks
        # for task in self.scheduler.tasks:
        #     if self._remove_from_subtasks(task, task_to_remove):
        #         return True

        task = self.scheduler.get_task_by_name(task_to_remove.name)
        if task:
            self.scheduler.delete_task(task.name)
            return True

        return False

    def _remove_from_subtasks(self, parent_task, task_to_remove):
        """Recursively remove from subtasks"""
        if task_to_remove in parent_task.subtasks:
            parent_task.subtasks.remove(task_to_remove)
            return True

        for subtask in parent_task.subtasks:
            if self._remove_from_subtasks(subtask, task_to_remove):
                return True
        return False

    def _is_child_of(self, potential_child, potential_parent):
        """Check if task is already a child of potential parent"""
        current = potential_child.parent
        while current:
            if current == potential_parent:
                return True
            current = current.parent
        return False

    def handle_input(self, key):
        if key in ('q', 'Q'):
            sys.exit(0)
            ## raise urwid.ExitMainLoop()
        elif key == 'a':
            self.add_new_task(None)
        elif key == 'm':
            self.toggle_move_mode()
        elif key == 'esc' and self.move_mode_active:
            self.cancel_move()

    def on_task_click(self, button, task: Task):
        print("Entering on_task_click")
        if self.move_mode_active:
            if self.selected_task_to_move is None:
                # First selection - choose task to move
                self.selected_task_to_move = task
                self.footer.set_text(f"Selected '{task.name}'. Now choose parent task (ESC to cancel)")
            else:
                # Second selection - choose parent
                if task == self.selected_task_to_move:
                    self.footer.set_text("Can't move task to itself")
                elif self._is_child_of(task, self.selected_task_to_move):
                    self.footer.set_text("Can't create circular dependency")
                else:
                    ##self._perform_move(self.selected_task_to_move, task)
                    self.drop_task()
            self.refresh_view()
        else:
            self.view_task_details(button, task)

    def toggle_move_mode(self):
        self.move_mode_active = not self.move_mode_active
        if not self.move_mode_active:
            self.selected_task_to_move = None
            self.footer.set_text("Move mode cancelled")
        else:
            self.footer.set_text("Move mode: Select task to move (ESC to cancel)")
        self.refresh_view()

    def cancel_move(self, button=None):
        self.move_mode_active = False
        self.selected_task_to_move = None
        self.refresh_view()
        self.footer.set_text("Move operation cancelled")


    def view_task_details(self, button, task: Task):
        details = f"""
Name: {task.name}
Description: {task.description}
Duration: {task.duration} minutes
Deadline: {task.deadline.isoformat() if task.deadline else 'None'}
Completion: {task.completion}%
Parent Task: {task.parent.name if task.parent else 'None'}
Subtasks: {len(task.subtasks)}
        """.strip()
        text = urwid.Text(details)
        back_button = urwid.Button("← Back", on_press=self.back_to_main)
        edit_button = urwid.Button("✏️ Edit Task", on_press=self.edit_task, user_data=task)
        delete_button = urwid.Button("🗑️ Delete Task", on_press=self.delete_task, user_data=task)
        completed_button = urwid.Button("✅ Completed", on_press=self.completed_task, user_data=task)

        pile = urwid.Pile([
            text, urwid.Divider(),
            edit_button,
            delete_button,
            completed_button,
            urwid.Divider(),
            back_button
        ])
        fill = urwid.Filler(pile, valign='top')
        self.main_loop.widget = urwid.Padding(fill, left=2, right=2)

    def back_to_main(self, button):
        self.start()

    def edit_task(self, button, task: Task):
        new_name = vim_edit(task.name or "")
        new_desc = vim_edit(task.description or "")
        new_duration = vim_edit("" if not task.duration else str(task.duration))
        new_deadline = vim_edit(task.deadline.isoformat() if task.deadline else "")

        task.name = new_name.strip()
        task.description = new_desc.strip()
        task.duration = int(new_duration.strip()) if new_duration.strip().isdigit() else None
        try:
            dt = datetime.datetime.fromisoformat(new_deadline.strip())
            task.deadline = dt
        except ValueError:
            task.deadline = datetime.datetime.fromisoformat("9999-12-31T23:59:59")

        self.scheduler.schedule_tasks()
        self.scheduler.save_schedule()
        self.back_to_main(None)
        self.refresh_view(maintain_focus=True)

    def delete_task(self, button, task: Task):
        # Confirm deletion
        text = urwid.Text(f"Are you sure you want to delete '{task.name}'?")
        yes_button = urwid.Button("Yes", on_press=self.confirm_delete, user_data=task)
        no_button = urwid.Button("No", on_press=self.back_to_main)

        pile = urwid.Pile([
            text, urwid.Divider(),
            urwid.Columns([
                urwid.AttrMap(yes_button, None, focus_map='reversed'),
                urwid.AttrMap(no_button, None, focus_map='reversed')
            ])
        ])
        fill = urwid.Filler(pile, valign='top')
        self.main_loop.widget = urwid.Padding(fill, left=2, right=2)
        self.refresh_view(maintain_focus=True)

    def completed_task(self, button, task: Task):

        task = self.scheduler.get_task_by_name(task.name)
        if not task.parent:
            self.scheduler.delete_task(task.name)
        else:
            task.completion = 100

        self.scheduler.schedule_tasks()
        self.scheduler.save_schedule()
        self.refresh_view(maintain_focus=True)
        self.back_to_main(None)

    def confirm_delete(self, button, task: Task):
        if self._remove_task(task):
            self.scheduler.schedule_tasks()
            self.scheduler.save_schedule()
            self.refresh_view(maintain_focus=True)
            self.back_to_main(None)
        else:
            self.footer.set_text("Failed to delete task")

    def add_new_task(self, button):
        name = vim_edit("New Task Name")
        description = vim_edit("New Task Description")
        duration_str = vim_edit("Duration in minutes")
        deadline_str = vim_edit("Deadline (YYYY-MM-DDTHH:MM)")

        try:
            dt = datetime.datetime.fromisoformat(deadline_str.strip())
            deadline_str = dt
        except ValueError:
            deadline_str = None

        try:
            task = Task(
                name=name.strip(),
                description=description.strip(),
                duration=int(duration_str.strip()) if (duration_str.strip()).isdigit() else None,
                deadline=deadline_str
            )
            self.scheduler.add_task(task)
            self.scheduler.schedule_tasks()
            self.scheduler.save_schedule()
        except Exception as e:
            self.footer.set_text(f"Failed to add task: {e}")

        self.refresh_view(maintain_focus=True)
        self.back_to_main(None)


def run_interactive_mode(scheduler_name: str):
    """Run the interactive mode with proper error handling"""
    try:
        app = InteractiveApp(scheduler_name)
        app.start()
    except Exception as e:
        print(f"Error starting interactive mode: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        ## reschedule the tasks after potential changes (temporary fix)
        scheduler = TaskScheduler(scheduler_name)
        scheduler.load_scheduler()
        scheduler.schedule_tasks()
        scheduler.save_schedule()