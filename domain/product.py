from dataclasses import dataclass
from enum import Enum
from bikefactory.domain.entity import Entity

@dataclass
class Product(Entity):
    ... 

@dataclass
class Bike(Product):
    ... 

@dataclass
class MountainBike(Bike):
    parts: list[BikePart]

@dataclass
class RoadBike(Bike):
    parts: list[BikePart]

@dataclass
class BikePart(Product):
    ... 

@dataclass
class Frame(BikePart):
    ... 

@dataclass
class Wheel(BikePart):
    ... 

@dataclass
class Chain(BikePart):
    ... 

@dataclass
class Suspension(BikePart):
    ... 

