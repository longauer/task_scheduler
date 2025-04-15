import datetime as datetime
from typing import Optional

class Task:
    def __init__(self, name, description = None, deadline: datetime = None, duration: int = 0, parent: Optional["Task"] = None):

        self.name = name
        self.description = description
        self._deadline = datetime.datetime.fromisoformat("9999-12-31T23:59:59") if not deadline else deadline
        self.subtasks = list()  # list of Task objects
        self._duration = duration
        self._completion = 0  # completion in %
        self.parent = parent

    @property
    def deadline(self):

        return self._deadline

    @deadline.setter
    def deadline(self, value):

        self._deadline = value

        for task in self.subtasks:

            task.deadline = value
    @property
    def duration(self):

        return self._duration

    @duration.setter
    def duration(self, value):

        assert value >= 0

        self._duration = value

        self.__recalc()

    @property
    def completion(self):

        return self._completion

    @completion.setter
    def completion(self, value):

        assert value >= 0 and value <= 100

        self._completion = value

        self.__recalc()

    def divide(self, *args, **kwargs):
        ''' method for subdividing the task - adding one subclass at a time '''

        new_task = Task(*args, **kwargs)

        new_task.parent = self

        new_task.deadline = self.deadline ## deadline propagation

        self.subtasks.append(new_task)

        self.__recalc()

    def delete(self, task_name):
        ''' method for deleting a subclass'''

        for ind, task in enumerate(self.subtasks):

            if task.name == task_name:

                del self.subtasks[ind]

            else:
                task.delete(task_name)

    def __repr__(self):
        return f"(name: {self.name}, deadline: {self.deadline}, duration: {self.duration}, completion: {self.completion})"

    def __hash__(self):
        return hash(self.name)

    def get_root(self):

        root = self

        while root.parent is not None:

            root = root.parent

        return root

    def __duration_recalc(self):

        if len(self.subtasks) == 0:

            return self.duration

        else:
            subtask_durations = list()

            for task in self.subtasks:

                subtask_durations.append(task.__duration_recalc())

            self._duration = sum(subtask_durations)

            return self.duration

    def __completion_recalc(self):

        if len(self.subtasks) == 0:

            return self.completion
        else:
            subtask_completion = list()

            for task in self.subtasks:

                subtask_completion.append(task.__completion_recalc())

            if self.duration == 0:

                self._completion = 0

            else:

                self._completion = sum(list(map(lambda x: x.completion*x.duration/self.duration, self.subtasks)))

            return self.completion

    def __recalc(self):

        root = self.get_root()

        root.__duration_recalc()

        root.__completion_recalc()

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "deadline": self.deadline.isoformat(),
            "duration": self.duration,
            "completion": self.completion,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks]
        }

    ## comparing based on deadlines
    def __eq__(self, other):
        if not isinstance(other, Task):
            return False
        return self.deadline == other.deadline and self.name == other.name

    def __lt__(self, other):

        return self.deadline < other.deadline


    ## TODO: annotate container as an iterable
    @staticmethod
    def find_task_by_name(name, container):
        """Search for a task by name in a nested task structure."""

        for task in container:

            if task.name == name:

                return task

            # Search recursively in subtasks
            found_task = Task.find_task_by_name(name, task.subtasks)

            if found_task:

                return found_task

        return None  # Return None if no match is found

    @staticmethod
    def collect_lowest_level_tasks(instance: Optional["Task"]):

        if len(instance.subtasks) == 0:

            return [instance]

        else:

            return [p for task in instance.subtasks for p in Task.collect_lowest_level_tasks(task)]


def main():
    ...

if __name__ == "__main__":
    main()
