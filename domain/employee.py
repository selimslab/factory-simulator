from dataclasses import dataclass
from enum import Enum
from bikefactory.domain.entity import Entity
from bikefactory.domain.skill import Skill
from bikefactory.domain.shift import Shift

@dataclass
class Employee(Entity):
    skills: list[Skill]
    shift: Shift


