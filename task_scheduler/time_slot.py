"""! @file time_slot.py
@brief Time slot management module
@author Samuel Longauer

@defgroup timeslot Time Slot Module
@brief Implements time interval management with datetime operations
"""

import datetime

class TimeSlot:
    """! @brief Represents a time interval with start and end times
    
    @ingroup timeslot
    
    Provides duration calculation, serialization, and comparison operations.
    Maintains chronological sorting through rich comparison operators.
    """

    def __init__(self, start_time: datetime, end_time: datetime):
        """! @brief Initialize TimeSlot instance
        
        @param start_time Start datetime of the time slot
        @param end_time End datetime of the time slot
        @pre end_time must be after start_time
        """
        self.start_time = start_time
        self.end_time = end_time

    def to_dict(self):
        """! @brief Serialize to dictionary
        @return Dictionary with ISO-formatted time strings
        """
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat()
        }

    @classmethod
    def from_dict(cls, time_slot: dict):
        """! @brief Construct from dictionary
        @param time_slot Dictionary with "start_time" and "end_time" ISO strings
        @return New TimeSlot instance
        """
        start_time = datetime.datetime.fromisoformat(time_slot["start_time"])
        end_time = datetime.datetime.fromisoformat(time_slot["end_time"])
        return cls(start_time, end_time)

    def duration(self):
        """! @brief Calculate duration as timedelta
        @return datetime.timedelta between start and end
        @note This implementation overrides the previous duration method
        """
        return self.end_time - self.start_time

    def __eq__(self, other):
        """! @brief Equality comparison
        @param other Comparison target
        @return True if both start and end times match
        """
        return self.start_time == other.start_time and self.end_time == other.end_time

    def __lt__(self, other):
        """! @brief Less-than comparison
        @param other Comparison target
        @return True if this slot starts earlier
        """
        return self.start_time < other.start_time

    def __le__(self, other):
        """! @brief Less-than-or-equal comparison
        @param other Comparison target
        @return True if this slot starts earlier or equal
        """
        return self.start_time <= other.start_time

    def __ge__(self, other):
        """! @brief Greater-than-or-equal comparison
        @param other Comparison target
        @return True if this slot starts later or equal
        """
        return self.start_time >= other.start_time

    def __hash__(self):
        """! @brief Hash implementation
        @return Hash value based on start and end times
        """
        return hash((self.start_time, self.end_time))

    def __repr__(self):
        """! @brief Machine-readable representation
        @return String showing start and end times
        """
        return f"from: {self.start_time} till: {self.end_time}"
