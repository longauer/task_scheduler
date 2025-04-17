import datetime

class TimeSlot:
    def __init__(self, start_time: datetime, end_time: datetime):

        self.start_time = start_time

        self.end_time = end_time

    def duration(self):

        return (self.end_time - self.start_time).total_seconds()/60 

    def to_dict(self):
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat()
        }

    @classmethod
    def from_dict(cls, time_slot: dict):

        start_time = time_slot["start_time"]

        end_time = time_slot["end_time"]

        return TimeSlot(datetime.datetime.fromisoformat(start_time), datetime.datetime.fromisoformat(end_time))

    def duration(self):
        return self.end_time - self.start_time

    def __eq__(self, other):
        return self.start_time == other.start_time and self.end_time == other.end_time

    def __lt__(self, other):
        return self.start_time < other.start_time

    def __le__(self, other):
        return self.start_time <= other.start_time

    def __ge__(self, other):
        return self.start_time >= other.start_time

    def __hash__(self):
        return hash((self.start_time, self.end_time))

    def __repr__(self):
        return f"from: {self.start_time} till: {self.end_time}"
