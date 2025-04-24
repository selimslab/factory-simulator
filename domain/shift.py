from dataclasses import dataclass
from enum import Enum
from bikefactory.domain.entity import Entity

@dataclass
class Break(Entity):
    start_time: datetime
    end_time: datetime

@dataclass
class Shift(Entity):
    start_time: datetime
    end_time: datetime
    breaks: list[Break]

@dataclass
class MorningShift(Shift):
    start_time: datetime = datetime.time(6, 0)
    end_time: datetime = datetime.time(14, 0)
    breaks: list[Break] = [
        Break(start_time=datetime.time(10, 0), end_time=datetime.time(10, 30)),
        Break(start_time=datetime.time(12, 0), end_time=datetime.time(12, 30))
    ]

@dataclass
class AfternoonShift(Shift):
    start_time: datetime = datetime.time(14, 0)
    end_time: datetime = datetime.time(22, 0)
    breaks: list[Break] = [
        Break(start_time=datetime.time(16, 0), end_time=datetime.time(16, 30)),
        Break(start_time=datetime.time(18, 0), end_time=datetime.time(18, 30))
    ]

@dataclass
class NightShift(Shift):
    start_time: datetime = datetime.time(22, 0)
    end_time: datetime = datetime.time(6, 0)
    breaks: list[Break] = [
        Break(start_time=datetime.time(23, 0), end_time=datetime.time(23, 30)),
        Break(start_time=datetime.time(1, 0), end_time=datetime.time(1, 30))
    ]

