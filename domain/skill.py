from dataclasses import dataclass
from enum import Enum

class SkillLevel(Enum):
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class Skill:
    name: str
    description: str
    level: SkillLevel

@dataclass
class Molding(Skill):
    name: str = "molding"
    description: str = "Molding plastic parts"

@dataclass
class Cutting(Skill):
    name: str = "cutting"
    description: str = "Cutting parts"

@dataclass
class Welding(Skill):
    name: str = "welding"
    description: str = "Welding metal parts"

@dataclass
class Machining(Skill):
    name: str = "machining"
    description: str = "Operating CNC machines"


@dataclass
class Assembly(Skill):
    name: str = "component_assembly"
    description: str = "Assembling bike components"

@dataclass
class Painting(Skill):
    name: str = "painting"
    description: str = "Painting and finishing"

@dataclass
class SuspensionTuning(Skill):
    name: str = "suspension_tuning"
    description: str = "Adjusting and tuning suspension systems"

@dataclass
class Maintenance(Skill):
    name: str = "maintenance"
    description: str = "Machine maintenance"

@dataclass
class QualityControl(Skill):
    name: str = "quality_control"
    description: str = "Testing and quality assurance"
