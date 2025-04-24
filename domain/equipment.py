from dataclasses import dataclass
from enum import Enum
from bikefactory.domain.entity import Entity

class EquipmentStatus(Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    BROKEN = "broken"

@dataclass
class Equipment(Entity):
    ... 

@dataclass
class Machine(Equipment):
    ... 

@dataclass
class Tool(Equipment):
    ... 


