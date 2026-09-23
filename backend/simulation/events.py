"""Simple event/mission timeline logger."""
import datetime


class EventLog:
    def __init__(self):
        self.events = []

    def log(self, icon: str, message: str):
        self.events.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "icon": icon,
            "message": message,
        })
        return self.events[-1]

    def reset(self):
        self.events = []

    def to_list(self):
        return self.events
