import urwid
from task_scheduler.scheduler import TaskScheduler
from task_scheduler.utils import vim_edit
from task_scheduler.task import Task
from task_scheduler.time_slot import TimeSlot
import datetime
import sys


class InteractiveApp:
    def __init__(self, scheduler_name):
        self.scheduler_name = scheduler_name
        self.scheduler = self.load_scheduler(scheduler_name)
        self.main_loop = None
        self.listbox = None
        self.time_slot_listbox = None
        self.body_walker = None
        self.time_slot_walker = None
        self.selected_task_to_move = None
        self.selected_time_slot = None
        self.move_mode_active = False
        self.current_focus = 'tasks'  # 'tasks' or 'time_slots'
        self.current_dialog = None

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
        self.footer = urwid.Text(
            "↑↓ navigate | Tab switch panels | Enter select/move | "
            "a add | m toggle move | q quit",
            align='center'
        )

        # Create initial empty listbox
        self.body_walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.body_walker)
        self.frame = urwid.Frame(
            header=urwid.AttrMap(self.header, 'header'),
            body=self.listbox,
            footer=urwid.AttrMap(self.footer, 'footer')
        )

        # Initialize time slot components
        self.time_slot_walker = urwid.SimpleFocusListWalker([])
        self.time_slot_listbox = urwid.ListBox(self.time_slot_walker)

        # Create split view columns
        self.columns = urwid.Columns([
            ('weight', 1, urwid.LineBox(self.listbox, title="Tasks")),
            ('weight', 1, urwid.LineBox(self.time_slot_listbox, title="Time Slots"))
        ])

        # Update frame body
        self.frame = urwid.Frame(
            header=urwid.AttrMap(self.header, 'header'),
            body=self.columns,
            footer=urwid.AttrMap(self.footer, 'footer')
        )

        # Initial refresh of both panels
        self.refresh_view()

    def load_scheduler(self, name):
        """Load scheduler with proper error handling"""
        try:
            scheduler = TaskScheduler(name)
            scheduler.load_scheduler()
            scheduler.load_schedule()
            return scheduler
        except Exception as e:
            print(f"Error: schedule with the given name not found.", file=sys.stderr)
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
        """Refresh both task and time slot views"""
        self._refresh_tasks(maintain_focus)
        self._refresh_time_slots()
        self.update_focus_indicator()

    def _refresh_tasks(self, maintain_focus=False):
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

        task = self.scheduler.get_task_by_name(task_to_remove.name)
        if task:
            self.scheduler.delete_task(task.name)
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

    def update_focus_indicator(self):
        """Update focus highlight using attribute maps"""
        # Create fresh attribute maps for both panels
        task_attr = 'reversed' if self.current_focus == 'tasks' else None
        schedule_attr = 'reversed' if self.current_focus == 'time_slots' else None

        # Rebuild columns with updated attributes
        self.columns.contents = [
            (
                urwid.AttrMap(
                    urwid.LineBox(self.listbox, title="Tasks"),
                    task_attr
                ),
                self.columns.contents[0][1]
            ),
            (
                urwid.AttrMap(
                    urwid.LineBox(self.time_slot_listbox, title="Time Slots"),
                    schedule_attr
                ),
                self.columns.contents[1][1]
            )
        ]

        # Set focus to the correct column
        self.columns.focus_position = 0 if self.current_focus == 'tasks' else 1

    def handle_input(self, key):
        if key in ('q', 'Q'):
            sys.exit(0)
        elif key == 'tab':
            self.current_focus = 'time_slots' if self.current_focus == 'tasks' else 'tasks'
            self.update_focus_indicator()
            return
        elif key == 'a':
            if self.current_focus == 'tasks':
                self.add_new_task(None)
            else:
                self.add_time_slot_dialog(None)
            return
        elif key == 'm':
            if self.current_focus == 'tasks':
                self.toggle_move_mode()
            return
        elif key == 'esc' and self.move_mode_active:
            self.cancel_move()
            return

            # Delegate keypress to currently focused column
        if self.current_focus == 'tasks':
            self.listbox.keypress(self.main_loop.screen_size, key)
        else:
            self.time_slot_listbox.keypress(self.main_loop.screen_size, key)

    def on_task_click(self, button, task: Task):
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

        description = "\n".join(line.strip() for line in str(task.description).splitlines())

        details = (
            f"Name: {task.name.strip()}\n\n"
            f"Description: {description}\n"
            f"Duration: {task.duration} minutes\n\n"
            f"Deadline: {task.deadline.isoformat() if task.deadline else 'None'}\n\n"
            f"Completion: {task.completion}%\n\n"
            f"Parent Task: {task.parent.name.strip() if task.parent else 'None'}\n\n"
            f"Subtasks: {len(task.subtasks)}"
        )

        # Create left-aligned text widget
        text = urwid.Text(("body", details))

        text = urwid.Text(details)
        back_button = urwid.Button("← Back", on_press=self.back_to_main)
        edit_button = urwid.Button("✏️ Edit Task", lambda _: self.edit_task_dialog(button=None, task=task))
        delete_button = urwid.Button("🗑️ Delete Task", on_press=self.delete_task, user_data=task)
        completed_button = urwid.Button("✅ Completed", on_press=self.completed_task, user_data=task)

        pile = urwid.Pile([
            urwid.AttrMap(text, "body"),
            urwid.Divider(),
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

    def edit_task_dialog(self, button, task: Task):
        """Show task editing options with proper back navigation"""
        # Store reference to current view
        self.previous_view = self.main_loop.widget

        options = [
            ("📝 Name", lambda _: self.edit_task_field(task, "name")),
            ("📄 Description", lambda _: self.edit_task_field(task, "description")),
            ("⏱ Duration", lambda _: self.edit_task_field(task, "duration")),
            ("📅 Deadline", lambda _: self.edit_task_field(task, "deadline")),
            ("✅ Completion", lambda _: self.edit_task_field(task, "completion")),
            ("🔙 Back", lambda _: (self.back_to_main, self.view_task_details(None, task)))
        ]

        # Create formatted menu items
        menu_items = []
        for text, callback in options:
            btn = urwid.AttrMap(
                urwid.Button(text, callback),
                None, focus_map='reversed'
            )
            menu_items.append(urwid.Padding(btn, align='center', width=('relative', 80)))
            menu_items.append(urwid.Divider())

        # Create centered popup content
        pile = urwid.Pile(menu_items[:-1])  # Remove last divider
        content = urwid.Filler(pile, valign='top')
        popup = urwid.LineBox(
            content,
            title=f"Edit {task.name[:15]}...",
            title_align='left'
        )

        # Create overlay with consistent sizing
        self.main_loop.widget = urwid.Overlay(
            popup,
            self.previous_view,
            align='center', width=('relative', 25),
            valign='middle', height=('relative', 25)
        )

    def edit_task_field(self, task: Task, field: str):
        """Edit specific task field with validation"""

        current_value = getattr(task, field)

        # Format current value for display
        if field == "deadline" and current_value:
            edit_text = current_value.isoformat(sep=" ", timespec="minutes")
        elif field == "completion":
            edit_text = str(int(current_value))
        elif field == "description":
            # Windows-compatible edit handler

            # Store current screen state
            original_screen = self.main_loop.screen

            try:
                # Suspend Urwid's terminal handling
                self.main_loop.screen.stop()

                # Perform Vim editing
                edit_text = vim_edit(task.description)

            finally:
                # Restore Urwid's terminal handling
                self.main_loop.screen = original_screen
                self.main_loop.screen.start()
                self.refresh_view()
        else:
            edit_text = str(current_value)

        # Create edit box
        edit = urwid.Edit(("bold", f"New {field.replace('_', ' ')}:\n"), edit_text)

        # Create proper callbacks
        def save_callback(_):
            self.save_task_edit(task, field, edit.edit_text)
            self.main_loop.widget = self.previous_view  # Close popup
            self.view_task_details(None, task)  # Refresh details

        def cancel_callback(_):
            self.main_loop.widget = self.previous_view  # Just close popup

        # Create buttons
        save_btn = urwid.Button("💾 Save", save_callback)
        cancel_btn = urwid.Button("❌ Cancel", cancel_callback)

        # Build layout
        pile = urwid.Pile([
            edit,
            urwid.Divider(),
            urwid.Columns([
                urwid.AttrMap(save_btn, None, focus_map='reversed'),
                urwid.AttrMap(cancel_btn, None, focus_map='reversed')
            ])
        ])

        # Show edit dialog
        popup = urwid.LineBox(urwid.Filler(pile), title=f"Edit {field.title()}")
        self.main_loop.widget = urwid.Overlay(
            popup,
            self.main_loop.widget,
            align='center', width=('relative', 25),
            valign='middle', height=('relative', 25)
        )

    def save_task_edit(self, task: Task, field: str, value: str):
        """Validate and save edited field"""
        try:
            # Field-specific validation
            if field == "name":
                if not value.strip():
                    raise ValueError("Name cannot be empty")
                task.name = value.strip()

            elif field == "description":
                task.description = value

            elif field == "duration":
                duration = int(value)
                if duration < 0:
                    raise ValueError("Duration must be non-negative")
                task.duration = duration

            elif field == "deadline":
                if value.lower() == "none":
                    task.deadline = None
                else:
                    task.deadline = datetime.datetime.fromisoformat(value)

            elif field == "completion":
                completion = int(value)
                if not 0 <= completion <= 100:
                    raise ValueError("Completion must be 0-100")
                task.completion = completion

            # Save changes
            self.scheduler.save_schedule()
            self.refresh_view(maintain_focus=True)

        except Exception as e:
            self.footer.set_text(("error", f"Invalid value: {str(e)}"))

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
                duration=int(duration_str.strip()) if (duration_str.strip()).isdigit() else 0,
                deadline=deadline_str
            )
            self.scheduler.add_task(task)
            self.scheduler.schedule_tasks()
            self.scheduler.save_schedule()
        except Exception as e:
            self.footer.set_text(f"Failed to add task: {e}")

        self.refresh_view(maintain_focus=True)
        self.back_to_main(None)


    # ----------------------------
    # Time slot management methods
    # ----------------------------

    def _build_time_slot_widgets(self, items):
        """Build time slot widgets"""
        for slot in self.scheduler.time_slots:

            btn = urwid.Button(
                f"🕒 {slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}",
                on_press=self.on_time_slot_click,
                user_data=slot
            )
            attr = 'selected_task' if slot == self.selected_time_slot else None
            btn_map = urwid.AttrMap(btn, attr, focus_map='reversed')
            btn_map.original_slot = slot
            items.append(btn_map)

    def _refresh_time_slots(self):
        """Refresh time slot display"""
        try:
            items = []
            for slot in self.scheduler.time_slots:
                btn = urwid.Button(
                    f"{slot.start_time.strftime('%Y-%m-%d %H:%M')}  <------->  {slot.end_time.strftime('%Y-%m-%d %H:%M')}",
                    on_press=self.on_time_slot_click,
                    user_data=slot
                )
                items.append(urwid.AttrMap(btn, None, focus_map='reversed'))

            # Add time slot controls
            items.append(urwid.Divider())
            items.append(urwid.AttrMap(
                urwid.Button("➕ Add Time Slot", on_press=self.add_time_slot_dialog),
                None, focus_map='reversed'
            ))

            self.time_slot_walker[:] = items
        except Exception as e:
            self.footer.set_text(("error", f"Time slot error: {str(e)}"))

    def add_time_slot_dialog(self, button):
        """Show time slot creation dialog"""
        start_edit = urwid.Edit("Start time (YYYY-MM-DD HH:MM): ")
        end_edit = urwid.Edit("End time (YYYY-MM-DD HH:MM): ")

        # Store references to the input fields
        self.current_dialog = {
            'start_edit': start_edit,
            'end_edit': end_edit
        }

        done_btn = urwid.Button("Add", self.do_add_time_slot)
        cancel_btn = urwid.Button("Cancel", self.back_to_main)

        pile = urwid.Pile([
            start_edit,
            end_edit,
            urwid.Divider(),
            urwid.Columns([
                urwid.AttrMap(done_btn, None, focus_map='reversed'),
                urwid.AttrMap(cancel_btn, None, focus_map='reversed')
            ])
        ])

        self._show_popup(pile, "New Time Slot")

    def do_add_time_slot(self, button):
        """Create time slot using original interface"""
        try:
            # Access stored dialog fields
            start_str = self.current_dialog['start_edit'].edit_text
            end_str = self.current_dialog['end_edit'].edit_text

            # Clear dialog reference
            # self.current_dialog = None

            # Parse and create time slot
            start_time = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            end_time = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M")

            new_slot = TimeSlot(start_time, end_time)
            self.scheduler.add_time_slot(new_slot)
            self.scheduler.schedule_tasks()
            self.scheduler.save_schedule()

            self._refresh_time_slots()
            self.back_to_main(None)

        except ValueError as e:
            self.footer.set_text(("error", f"Invalid time: {str(e)}"))

    def on_time_slot_click(self, button, time_slot):
        """Handle time slot selection"""
        if self.move_mode_active:
            # Implement time slot movement logic if needed
            pass
        else:
            self.view_time_slot_details(button, time_slot)

    def view_time_slot_details(self, button, time_slot):
        """Show time slot details popup"""
        details = f"""
Start: {time_slot.start_time.strftime('%Y-%m-%d %H:%M')}
End: {time_slot.end_time.strftime('%Y-%m-%d %H:%M')}
Duration: {time_slot.duration()} hours
        """.strip()
        text = urwid.Text(details)
        edit_btn = urwid.Button("✏️ Edit", lambda _: self.edit_time_slot(time_slot))
        delete_btn = urwid.Button("🗑️ Delete", lambda _: self.delete_time_slot(time_slot))
        back_btn = urwid.Button("← Back", self.back_to_main)

        pile = urwid.Pile([
            text,
            urwid.Divider(),
            edit_btn,
            delete_btn,
            urwid.Divider(),
            back_btn
        ])
        self._show_popup(pile, "Time Slot Details")

    def edit_time_slot(self, time_slot):
        """Edit an existing time slot"""
        # Store reference to the original time slot
        self._original_time_slot = time_slot

        # Create input fields with current values
        start_edit = urwid.Edit("Start time: ", time_slot.start_time.strftime("%Y-%m-%d %H:%M"))
        end_edit = urwid.Edit("End time: ", time_slot.end_time.strftime("%Y-%m-%d %H:%M"))

        # Store dialog references
        self.current_dialog = {
            'start_edit': start_edit,
            'end_edit': end_edit
        }

        # Create buttons
        save_btn = urwid.Button("💾 Save", self._do_edit_time_slot)
        cancel_btn = urwid.Button("❌ Cancel", self.back_to_main)

        # Build layout
        pile = urwid.Pile([
            start_edit,
            end_edit,
            urwid.Divider(),
            urwid.Columns([
                urwid.AttrMap(save_btn, None, focus_map='reversed'),
                urwid.AttrMap(cancel_btn, None, focus_map='reversed')
            ])
        ])

        self._show_popup(pile, "Edit Time Slot")

    def _do_edit_time_slot(self, button):
        """Handle the actual editing logic"""
        try:
            # Get input values
            start_str = self.current_dialog['start_edit'].edit_text
            end_str = self.current_dialog['end_edit'].edit_text

            # Clear dialog reference
            self.current_dialog = None

            # Parse datetime values
            new_start = datetime.datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            new_end = datetime.datetime.strptime(end_str, "%Y-%m-%d %H:%M")

            # Validate times
            if new_end <= new_start:
                raise ValueError("End time must be after start time")

            # Create new time slot (preserving original interface)
            updated_slot = TimeSlot(new_start, new_end)

            # Replace in scheduler
            index = self.scheduler.time_slots.index(self._original_time_slot)
            self.scheduler.time_slots[index] = updated_slot
            self.scheduler.time_slots.sort()

            # Save and refresh
            self.scheduler.save_schedule()
            self._refresh_time_slots()
            self.back_to_main(None)
            self.footer.set_text(("success", "Time slot updated successfully"))

        except ValueError as e:
            self.footer.set_text(("error", f"Invalid input: {str(e)}"))
        finally:
            self._original_time_slot = None

    def delete_time_slot(self, time_slot):
        """Delete selected time slot"""
        self.scheduler.time_slots.remove(time_slot)
        self.scheduler.save_schedule()
        self.refresh_view()
        self.back_to_main(None)

    def _show_popup(self, widget, title):
        """Helper to show popup dialogs"""
        popup = urwid.LineBox(urwid.Filler(widget), title=title)
        overlay = urwid.Overlay(popup, self.columns,
                                align='center', width=('relative', 80),
                                valign='middle', height=('relative', 80))
        self.main_loop.widget = overlay


def run_interactive_mode(scheduler_name: str):
    """Run the interactive mode with proper error handling"""
    try:
        app = InteractiveApp(scheduler_name)
        app.start()
    except Exception as e:
        print(f"Error starting interactive mode: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Reschedule the tasks after potential changes (temporary fix)
        try:
            scheduler = TaskScheduler(scheduler_name)
            scheduler.load_scheduler()
            scheduler.schedule_tasks()
            scheduler.save_schedule()
        except FileNotFoundError:
            sys.exit(1)

