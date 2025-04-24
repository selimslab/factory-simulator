from dataclasses import dataclass
from enum import Enum
from uuid import uuid4


@dataclass
class Entity:
    uid: str = field(default_factory=lambda: str(uuid4()))
    name: str 
    description: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

