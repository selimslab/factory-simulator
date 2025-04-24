from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Protocol, Self, Callable, Any
from datetime import datetime, timedelta
import uuid
import simpy
import random

# === Core Types Module ===

class ResourceStatus(Enum):
    AVAILABLE = auto()
    BUSY = auto()
    UNAVAILABLE = auto()
    MAINTENANCE = auto()

class OrderStatus(Enum):
    RECEIVED = auto()
    SCHEDULED = auto()
    IN_PRODUCTION = auto()
    COMPLETED = auto()
    CANCELLED = auto()

# === Resource Module ===
@dataclass
class Resource(Protocol):
    id: str
    name: str
    status: ResourceStatus
    
    def is_available(self, start_time: datetime, duration: int) -> bool: ...

@dataclass
class Material:
    id: str
    name: str
    quantity: int
    location: str = "warehouse"
    unit_cost: float = 0.0

@dataclass
class Employee:
    id: str
    name: str
    skills: Dict[Skill, SkillLevel]
    schedule: Dict[datetime, bool] = field(default_factory=dict)
    status: ResourceStatus = ResourceStatus.AVAILABLE
    hourly_rate: float = 20.0
    
    def has_skill(self, skill: Skill, level: SkillLevel) -> bool:
        return skill in self.skills and self.skills[skill].value >= level.value
    
    def is_available(self, start_time: datetime, duration: int) -> bool:
        # Simplified availability check
        return self.status == ResourceStatus.AVAILABLE

@dataclass
class Machine:
    id: str
    name: str
    machine_type: str
    skills_required: Dict[Skill, SkillLevel]
    schedule: Dict[datetime, bool] = field(default_factory=dict)
    status: ResourceStatus = ResourceStatus.AVAILABLE
    maintenance_interval: int = 2400  # minutes (40 hours)
    minutes_since_maintenance: int = 0
    failure_rate: float = 0.01  # 1% chance of failure per hour
    
    def is_available(self, start_time: datetime, duration: int) -> bool:
        # Check if maintenance is needed
        if self.minutes_since_maintenance >= self.maintenance_interval:
            return False
        return self.status == ResourceStatus.AVAILABLE
    
    def needs_maintenance(self) -> bool:
        return self.minutes_since_maintenance >= self.maintenance_interval

# === Production Module ===
@dataclass
class ProductionStep:
    id: str
    name: str
    required_skills: Dict[Skill, SkillLevel]
    required_machines: List[str]
    required_materials: Dict[str, int]
    duration: int  # minutes
    quality_factor: float = 1.0  # multiplier for quality based on skill level
    
    def can_be_performed_by(self, employee: Employee) -> bool:
        return all(employee.has_skill(skill, level) for skill, level in self.required_skills.items())

@dataclass
class BikeModel:
    id: str
    name: str
    type: str  # mountain, road, hybrid, electric
    steps: List[ProductionStep]
    base_price: float
    
    def total_production_time(self) -> int:
        return sum(step.duration for step in self.steps)

# === Event System ===
@dataclass
class Event:
    type: str
    data: Dict
    timestamp: datetime = field(default_factory=datetime.now)

class EventHandler(Protocol):
    def handle(self, event: Event) -> None: ...

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[EventHandler]] = {}
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def publish(self, event: Event) -> None:
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                handler.handle(event)

# === Order Module ===
@dataclass
class ScheduledTask:
    step: ProductionStep
    start_time: datetime
    end_time: datetime
    assigned_employees: List[Employee]
    assigned_machines: List[Machine]
    completed: bool = False
    quality_score: float = 0.0

@dataclass
class Order:
    id: str
    customer: str
    bike_model: BikeModel
    quantity: int
    due_date: datetime
    tasks: List[ScheduledTask] = field(default_factory=list)
    status: OrderStatus = OrderStatus.RECEIVED
    
    @classmethod
    def create(cls, customer: str, bike_model: BikeModel, quantity: int, due_date: datetime) -> Self:
        return cls(
            id=str(uuid.uuid4()),
            customer=customer,
            bike_model=bike_model,
            quantity=quantity,
            due_date=due_date
        )

# === Scheduling Module ===
class ResourceScheduler:
    def __init__(self, employees: List[Employee], machines: List[Machine], inventory: Dict[str, Material]):
        self.employees = employees
        self.machines = machines
        self.inventory = inventory
    
    def find_available_employees(self, skills_required: Dict[Skill, SkillLevel], 
                                start_time: datetime, duration: int) -> List[Employee]:
        return [
            employee for employee in self.employees
            if all(employee.has_skill(skill, level) for skill, level in skills_required.items())
            and employee.is_available(start_time, duration)
        ]
    
    def find_available_machines(self, machine_types: List[str], 
                               start_time: datetime, duration: int) -> List[Machine]:
        return [
            machine for machine in self.machines
            if machine.machine_type in machine_types and machine.is_available(start_time, duration)
        ]
    
    def has_materials(self, materials_required: Dict[str, int]) -> bool:
        return all(
            material_id in self.inventory and 
            self.inventory[material_id].quantity >= quantity
            for material_id, quantity in materials_required.items()
        )

class ProductionScheduler:
    def __init__(self, resource_scheduler: ResourceScheduler, event_bus: EventBus):
        self.resource_scheduler = resource_scheduler
        self.event_bus = event_bus
    
    def schedule_order(self, order: Order) -> bool:
        # A simple scheduling algorithm (rough sketch)
        current_time = datetime.now()
        
        for _ in range(order.quantity):  # For each bike in the order
            for step in order.bike_model.steps:
                # Check material availability
                if not self.resource_scheduler.has_materials(step.required_materials):
                    return False  # Can't schedule due to material shortage
                
                # Find available employees
                employees = self.resource_scheduler.find_available_employees(
                    step.required_skills, current_time, step.duration
                )
                if not employees:
                    return False  # Can't schedule due to employee unavailability
                
                # Find available machines
                machines = self.resource_scheduler.find_available_machines(
                    step.required_machines, current_time, step.duration
                )
                if step.required_machines and not machines:
                    return False  # Can't schedule due to machine unavailability
                
                # Schedule the task
                end_time = current_time.replace(minute=current_time.minute + step.duration)
                task = ScheduledTask(
                    step=step,
                    start_time=current_time,
                    end_time=end_time,
                    assigned_employees=employees[:1],  # Just take the first available employee
                    assigned_machines=machines
                )
                order.tasks.append(task)
                
                # Update time for next step
                current_time = end_time
        
        # If we got here, scheduling was successful
        order.status = OrderStatus.SCHEDULED
        self.event_bus.publish(Event("order_scheduled", {"order_id": order.id}))
        return True

# === Factory Module ===
class OrderHandler:
    def __init__(self, scheduler: ProductionScheduler, event_bus: EventBus):
        self.scheduler = scheduler
        self.event_bus = event_bus
        self.orders: Dict[str, Order] = {}
        
        # Subscribe to events
        event_bus.subscribe("order_created", self)
    
    def handle(self, event: Event) -> None:
        if event.type == "order_created":
            order_id = event.data["order_id"]
            self.process_new_order(self.orders[order_id])
    
    def create_order(self, customer: str, bike_model: BikeModel, quantity: int, due_date: datetime) -> Order:
        order = Order.create(customer, bike_model, quantity, due_date)
        self.orders[order.id] = order
        self.event_bus.publish(Event("order_created", {"order_id": order.id}))
        return order
    
    def process_new_order(self, order: Order) -> None:
        success = self.scheduler.schedule_order(order)
        if not success:
            # Handle scheduling failure
            order.status = OrderStatus.CANCELLED
            self.event_bus.publish(Event("order_cancelled", {"order_id": order.id, "reason": "scheduling_failed"}))

class BikeFactory:
    def __init__(self, name: str):
        self.name = name
        self.event_bus = EventBus()
        
        # Initialize resources
        self.employees: List[Employee] = []
        self.machines: List[Machine] = []
        self.inventory: Dict[str, Material] = {}
        self.bike_models: Dict[str, BikeModel] = {}
        
        # Initialize modules
        self.resource_scheduler = ResourceScheduler(self.employees, self.machines, self.inventory)
        self.production_scheduler = ProductionScheduler(self.resource_scheduler, self.event_bus)
        self.order_handler = OrderHandler(self.production_scheduler, self.event_bus)
    
    def add_employee(self, employee: Employee) -> None:
        self.employees.append(employee)
    
    def add_machine(self, machine: Machine) -> None:
        self.machines.append(machine)
    
    def add_material(self, material: Material) -> None:
        self.inventory[material.id] = material
    
    def add_bike_model(self, model: BikeModel) -> None:
        self.bike_models[model.id] = model
    
    def create_order(self, customer: str, bike_model_id: str, quantity: int, due_date: datetime) -> Optional[Order]:
        if bike_model_id not in self.bike_models:
            return None
        
        return self.order_handler.create_order(
            customer, 
            self.bike_models[bike_model_id],
            quantity,
            due_date
        )

# === SimPy Simulation ===
class FactorySimulation:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.factory = self.create_sample_factory()
        self.human_resources = {}  # Resources by skill
        self.machine_resources = {}
        self.simulation_stats = {
            "orders_received": 0,
            "orders_completed": 0,
            "orders_cancelled": 0,
            "bikes_produced": 0,
            "total_production_time": 0,
            "machine_breakdowns": 0,
            "maintenance_events": 0,
            "quality_scores": []
        }
        
        # Create resources for each skill
        for skill in Skill:
            skilled_employees = sum(1 for e in self.factory.employees if skill in e.skills)
            self.human_resources[skill] = simpy.Resource(env, capacity=skilled_employees)
        
        # Create resources for each machine type
        machine_types = set(machine.machine_type for machine in self.factory.machines)
        for machine_type in machine_types:
            machines_of_type = sum(1 for m in self.factory.machines if m.machine_type == machine_type)
            self.machine_resources[machine_type] = simpy.Resource(env, capacity=machines_of_type)
    
    def create_sample_factory(self) -> BikeFactory:
        # Create a sample factory with employees, machines, materials, and bike models
        factory = BikeFactory("Advanced Bike Factory")
        
        # Add employees with realistic skills
        employee_skills = [
            # Welders
            {Skill.FRAME_WELDING: SkillLevel.EXPERT, Skill.TUBE_CUTTING: SkillLevel.ADVANCED, Skill.MAINTENANCE: SkillLevel.INTERMEDIATE},
            {Skill.FRAME_WELDING: SkillLevel.ADVANCED, Skill.TUBE_CUTTING: SkillLevel.INTERMEDIATE},
            
            # Assemblers
            {Skill.COMPONENT_ASSEMBLY: SkillLevel.EXPERT, Skill.WHEEL_BUILDING: SkillLevel.ADVANCED},
            {Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED, Skill.SUSPENSION_TUNING: SkillLevel.EXPERT},
            {Skill.COMPONENT_ASSEMBLY: SkillLevel.INTERMEDIATE, Skill.QUALITY_CONTROL: SkillLevel.INTERMEDIATE},
            
            # Painters
            {Skill.PAINTING: SkillLevel.EXPERT},
            {Skill.PAINTING: SkillLevel.ADVANCED, Skill.MAINTENANCE: SkillLevel.NOVICE},
            
            # Specialists
            {Skill.WHEEL_BUILDING: SkillLevel.EXPERT, Skill.COMPONENT_ASSEMBLY: SkillLevel.INTERMEDIATE},
            {Skill.ELECTRONICS: SkillLevel.EXPERT, Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED},
            {Skill.MACHINING: SkillLevel.EXPERT, Skill.MAINTENANCE: SkillLevel.ADVANCED},
            
            # QA/QC
            {Skill.QUALITY_CONTROL: SkillLevel.EXPERT, Skill.SUSPENSION_TUNING: SkillLevel.ADVANCED},
            {Skill.QUALITY_CONTROL: SkillLevel.ADVANCED, Skill.WHEEL_BUILDING: SkillLevel.INTERMEDIATE}
        ]
        
        for i, skills in enumerate(employee_skills):
            factory.add_employee(Employee(
                id=f"emp-{i+1}",
                name=f"Employee {i+1}",
                skills=skills,
                hourly_rate=20.0 + (sum(level.value for level in skills.values()) * 1.5)  # Higher skills = higher pay
            ))
        
        # Add realistic machines with meaningful parameters
        machines = [
            # Frame preparation
            ("tube_cutter", "Tube Cutting Machine", "CuttingMachine", 
             {Skill.TUBE_CUTTING: SkillLevel.INTERMEDIATE}, 2400, 0.01),
            ("cnc_mill", "CNC Milling Machine", "CNCMachine", 
             {Skill.MACHINING: SkillLevel.ADVANCED}, 1800, 0.02),
            
            # Welding
            ("tig_welder_1", "TIG Welding Station 1", "WeldingStation", 
             {Skill.FRAME_WELDING: SkillLevel.INTERMEDIATE}, 2400, 0.01),
            ("tig_welder_2", "TIG Welding Station 2", "WeldingStation", 
             {Skill.FRAME_WELDING: SkillLevel.INTERMEDIATE}, 2400, 0.01),
            
            # Wheel building
            ("wheel_truing_stand_1", "Wheel Truing Stand 1", "WheelStation", 
             {Skill.WHEEL_BUILDING: SkillLevel.INTERMEDIATE}, 4800, 0.005),
            ("wheel_truing_stand_2", "Wheel Truing Stand 2", "WheelStation", 
             {Skill.WHEEL_BUILDING: SkillLevel.INTERMEDIATE}, 4800, 0.005),
            
            # Assembly
            ("assembly_station_1", "Bike Assembly Station 1", "AssemblyStation", 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE}, 4800, 0.005),
            ("assembly_station_2", "Bike Assembly Station 2", "AssemblyStation", 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE}, 4800, 0.005),
            ("assembly_station_3", "Bike Assembly Station 3", "AssemblyStation", 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE}, 4800, 0.005),
            
            # Painting
            ("paint_booth_1", "Paint Booth 1", "PaintBooth", 
             {Skill.PAINTING: SkillLevel.INTERMEDIATE}, 1200, 0.02),
            ("paint_booth_2", "Paint Booth 2", "PaintBooth", 
             {Skill.PAINTING: SkillLevel.INTERMEDIATE}, 1200, 0.02),
            
            # Special equipment
            ("suspension_dyno", "Suspension Dynamometer", "TestingEquipment", 
             {Skill.SUSPENSION_TUNING: SkillLevel.ADVANCED}, 2400, 0.01),
            ("electronics_bench", "Electronics Workbench", "ElectronicsStation", 
             {Skill.ELECTRONICS: SkillLevel.INTERMEDIATE}, 3600, 0.01),
            
            # Quality control
            ("qa_stand_1", "Quality Assurance Station 1", "QAStation", 
             {Skill.QUALITY_CONTROL: SkillLevel.INTERMEDIATE}, 4800, 0.005),
            ("qa_stand_2", "Quality Assurance Station 2", "QAStation", 
             {Skill.QUALITY_CONTROL: SkillLevel.INTERMEDIATE}, 4800, 0.005)
        ]
        
        for machine_id, name, machine_type, skills_required, maintenance_interval, failure_rate in machines:
            factory.add_machine(Machine(
                id=machine_id,
                name=name,
                machine_type=machine_type,
                skills_required=skills_required,
                maintenance_interval=maintenance_interval,
                failure_rate=failure_rate
            ))
        
        # Add realistic materials
        materials = [
            # Frame materials
            ("aluminum_tube", "Aluminum Tubing", 500, "frame_storage", 8.50),
            ("carbon_tube", "Carbon Fiber Tubing", 200, "frame_storage", 22.75),
            ("steel_tube", "Chromoly Steel Tubing", 300, "frame_storage", 5.25),
            
            # Components
            ("handlebar", "Handlebars", 150, "components", 12.00),
            ("stem", "Stems", 150, "components", 8.50),
            ("seat_post", "Seat Posts", 150, "components", 9.25),
            ("saddle", "Saddles", 150, "components", 15.00),
            ("front_derailleur", "Front Derailleurs", 100, "components", 18.50),
            ("rear_derailleur", "Rear Derailleurs", 100, "components", 25.00),
            ("brake_set", "Hydraulic Brake Sets", 100, "components", 45.00),
            ("chain", "Chains", 200, "components", 12.00),
            ("cassette", "Cassettes", 100, "components", 22.00),
            ("bottom_bracket", "Bottom Brackets", 100, "components", 15.00),
            ("crankset", "Cranksets", 100, "components", 35.00),
            
            # Wheels
            ("rim", "Wheel Rims", 300, "wheel_storage", 18.00),
            ("hub", "Wheel Hubs", 300, "wheel_storage", 22.00),
            ("spoke", "Wheel Spokes (pack)", 1000, "wheel_storage", 0.50),
            ("tire", "Tires", 300, "wheel_storage", 25.00),
            ("tube", "Inner Tubes", 400, "wheel_storage", 5.00),
            
            # Suspension
            ("fork", "Front Forks", 80, "suspension", 120.00),
            ("rear_shock", "Rear Shocks", 50, "suspension", 85.00),
            
            # Electronics
            ("motor", "E-Bike Motors", 30, "electronics", 150.00),
            ("battery", "Lithium Batteries", 30, "electronics", 200.00),
            ("controller", "Motor Controllers", 30, "electronics", 45.00),
            ("display", "Digital Displays", 30, "electronics", 35.00),
            
            # Finishing
            ("paint", "Paint (liter)", 200, "paint_storage", 12.00),
            ("clear_coat", "Clear Coat (liter)", 150, "paint_storage", 15.00),
            ("decal", "Decal Sets", 100, "paint_storage", 8.00),
            
            # Packaging
            ("box", "Shipping Boxes", 100, "packaging", 3.50),
            ("manual", "User Manuals", 200, "packaging", 1.25),
            ("toolkit", "Basic Tool Kits", 100, "packaging", 8.00)
        ]
        
        for material_id, name, quantity, location, unit_cost in materials:
            factory.add_material(Material(
                id=material_id,
                name=name,
                quantity=quantity,
                location=location,
                unit_cost=unit_cost
            ))
        
        # Create realistic production steps for different bike types
        
        # Mountain Bike Steps
        mtb_frame_prep = ProductionStep(
            id="mtb_step1",
            name="Mountain Bike Frame Tube Preparation",
            required_skills={Skill.TUBE_CUTTING: SkillLevel.INTERMEDIATE},
            required_machines=["CuttingMachine"],
            required_materials={"aluminum_tube": 5},
            duration=45,
            quality_factor=0.9
        )
        
        mtb_frame_welding = ProductionStep(
            id="mtb_step2",
            name="Mountain Bike Frame Welding",
            required_skills={Skill.FRAME_WELDING: SkillLevel.ADVANCED},
            required_machines=["WeldingStation"],
            required_materials={},  # Already accounted for in tube prep
            duration=90,
            quality_factor=1.2
        )
        
        mtb_suspension_prep = ProductionStep(
            id="mtb_step3",
            name="Mountain Bike Suspension Installation",
            required_skills={Skill.SUSPENSION_TUNING: SkillLevel.INTERMEDIATE},
            required_machines=["AssemblyStation"],
            required_materials={"fork": 1, "rear_shock": 1},
            duration=60,
            quality_factor=1.1
        )
        
        mtb_wheel_building = ProductionStep(
            id="mtb_step4",
            name="Mountain Bike Wheel Building",
            required_skills={Skill.WHEEL_BUILDING: SkillLevel.ADVANCED},
            required_machines=["WheelStation"],
            required_materials={"rim": 2, "hub": 2, "spoke": 2, "tire": 2, "tube": 2},
            duration=75,
            quality_factor=1.0
        )
        
        mtb_assembly = ProductionStep(
            id="mtb_step5",
            name="Mountain Bike Component Assembly",
            required_skills={Skill.COMPONENT_ASSEMBLY: SkillLevel.INTERMEDIATE},
            required_machines=["AssemblyStation"],
            required_materials={
                "handlebar": 1, "stem": 1, "seat_post": 1, "saddle": 1, 
                "front_derailleur": 1, "rear_derailleur": 1, "brake_set": 1,
                "chain": 1, "cassette": 1, "bottom_bracket": 1, "crankset": 1
            },
            duration=120,
            quality_factor=1.0
        )
        
        mtb_paint = ProductionStep(
            id="mtb_step6",
            name="Mountain Bike Painting",
            required_skills={Skill.PAINTING: SkillLevel.INTERMEDIATE},
            required_machines=["PaintBooth"],
            required_materials={"paint": 2, "clear_coat": 1, "decal": 1},
            duration=90,
            quality_factor=0.9
        )
        
        mtb_qa = ProductionStep(
            id="mtb_step7",
            name="Mountain Bike Quality Assurance",
            required_skills={Skill.QUALITY_CONTROL: SkillLevel.INTERMEDIATE},
            required_machines=["QAStation"],
            required_materials={},
            duration=30,
            quality_factor=1.5
        )
        
        mtb_packaging = ProductionStep(
            id="mtb_step8",
            name="Mountain Bike Packaging",
            required_skills={Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE},
            required_machines=[],
            required_materials={"box": 1, "manual": 1, "toolkit": 1},
            duration=20,
            quality_factor=0.7
        )
        
        # Road Bike Steps
        road_frame_prep = ProductionStep(
            id="road_step1",
            name="Road Bike Frame Tube Preparation",
            required_skills={Skill.TUBE_CUTTING: SkillLevel.ADVANCED, Skill.MACHINING: SkillLevel.INTERMEDIATE},
            required_machines=["CuttingMachine", "CNCMachine"],
            required_materials={"carbon_tube": 5},
            duration=60,
            quality_factor=1.2
        )
        
        road_frame_assembly = ProductionStep(
            id="road_step2",
            name="Road Bike Frame Assembly",
            required_skills={Skill.FRAME_WELDING: SkillLevel.EXPERT, Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED},
            required_machines=["AssemblyStation"],
            required_materials={},
            duration=100,
            quality_factor=1.3
        )
        
        road_wheel_building = ProductionStep(
            id="road_step3",
            name="Road Bike Wheel Building",
            required_skills={Skill.WHEEL_BUILDING: SkillLevel.EXPERT},
            required_machines=["WheelStation"],
            required_materials={"rim": 2, "hub": 2, "spoke": 2, "tire": 2, "tube": 2},
            duration=90,
            quality_factor=1.2
        )
        
        road_assembly = ProductionStep(
            id="road_step4",
            name="Road Bike Component Assembly",
            required_skills={Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED},
            required_machines=["AssemblyStation"],
            required_materials={
                "handlebar": 1, "stem": 1, "seat_post": 1, "saddle": 1, 
                "front_derailleur": 1, "rear_derailleur": 1, "brake_set": 1,
                "chain": 1, "cassette": 1, "bottom_bracket": 1, "crankset": 1
            },
            duration=90,
            quality_factor=1.1
        )
        
        road_paint = ProductionStep(
            id="road_step5",
            name="Road Bike Painting and Finishing",
            required_skills={Skill.PAINTING: SkillLevel.EXPERT},
            required_machines=["PaintBooth"],
            required_materials={"paint": 1, "clear_coat": 2, "decal": 1},
            duration=120,
            quality_factor=1.2
        )
        
        road_qa = ProductionStep(
            id="road_step6",
            name="Road Bike Quality Assurance",
            required_skills={Skill.QUALITY_CONTROL: SkillLevel.EXPERT},
            required_machines=["QAStation"],
            required_materials={},
            duration=45,
            quality_factor=1.5
        )
        
        road_packaging = ProductionStep(
            id="road_step7",
            name="Road Bike Packaging",
            required_skills={Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE},
            required_machines=[],
            required_materials={"box": 1, "manual": 1, "toolkit": 1},
            duration=20,
            quality_factor=0.7
        )
        
        # Electric Bike Steps
        ebike_frame_prep = ProductionStep(
            id="ebike_step1",
            name="E-Bike Frame Preparation",
            required_skills={Skill.TUBE_CUTTING: SkillLevel.INTERMEDIATE, Skill.MACHINING: SkillLevel.INTERMEDIATE},
            required_machines=["CuttingMachine", "CNCMachine"],
            required_materials={"aluminum_tube": 6},
            duration=60,
            quality_factor=1.0
        )
        
        ebike_frame_welding = ProductionStep(
            id="ebike_step2",
            name="E-Bike Frame Welding",
            required_skills={Skill.FRAME_WELDING: SkillLevel.ADVANCED},
            required_machines=["WeldingStation"],
            required_materials={},
            duration=100,
            quality_factor=1.1
        )
        
        ebike_electronics = ProductionStep(
            id="ebike_step3",
            name="E-Bike Electronics Installation",
            required_skills={Skill.ELECTRONICS: SkillLevel.ADVANCED},
            required_machines=["ElectronicsStation"],
            required_materials={"motor": 1, "battery": 1, "controller": 1, "display": 1},
            duration=90,
            quality_factor=1.3
        )
        
        ebike_wheel_building = ProductionStep(
            id="ebike_step4",
            name="E-Bike Wheel Building",
            required_skills={Skill.WHEEL_BUILDING: SkillLevel.ADVANCED},
            required_machines=["WheelStation"],
            required_materials={"rim": 2, "hub": 2, "spoke": 2, "tire": 2, "tube": 2},
            duration=60,
            quality_factor=1.0
        )
        
        ebike_assembly = ProductionStep(
            id="ebike_step5",
            name="E-Bike Component Assembly",
            required_skills={Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED},
            required_machines=["AssemblyStation"],
            required_materials={
                "handlebar": 1, "stem": 1, "seat_post": 1, "saddle": 1, 
                "front_derailleur": 1, "rear_derailleur": 1, "brake_set": 1,
                "chain": 1, "cassette": 1, "bottom_bracket": 1, "crankset": 1
            },
            duration=120,
            quality_factor=1.0
        )
        
        ebike_paint = ProductionStep(
            id="ebike_step6",
            name="E-Bike Painting",
            required_skills={Skill.PAINTING: SkillLevel.INTERMEDIATE},
            required_machines=["PaintBooth"],
            required_materials={"paint": 2, "clear_coat": 1, "decal": 1},
            duration=90,
            quality_factor=0.9
        )
        
        ebike_electronics_testing = ProductionStep(
            id="ebike_step7",
            name="E-Bike Electronics Testing",
            required_skills={Skill.ELECTRONICS: SkillLevel.EXPERT, Skill.QUALITY_CONTROL: SkillLevel.INTERMEDIATE},
            required_machines=["QAStation", "ElectronicsStation"],
            required_materials={},
            duration=45,
            quality_factor=1.4
        )
        
        ebike_qa = ProductionStep(
            id="ebike_step8",
            name="E-Bike Quality Assurance",
            required_skills={Skill.QUALITY_CONTROL: SkillLevel.ADVANCED},
            required_machines=["QAStation"],
            required_materials={},
            duration=30,
            quality_factor=1.2
        )
        
        ebike_packaging = ProductionStep(
            id="ebike_step9",
            name="E-Bike Packaging",
            required_skills={Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE},
            required_machines=[],
            required_materials={"box": 1, "manual": 1, "toolkit": 1},
            duration=25,
            quality_factor=0.7
        )
        
        # Create bike models
        mountain_bike = BikeModel(
            id="mountain",
            name="Trail Crusher Mountain Bike",
            type="mountain",
            steps=[mtb_frame_prep, mtb_frame_welding, mtb_suspension_prep, 
                   mtb_wheel_building, mtb_assembly, mtb_paint, mtb_qa, mtb_packaging],
            base_price=899.99
        )
        
        road_bike = BikeModel(
            id="road",
            name="Speed Demon Road Bike",
            type="road",
            steps=[road_frame_prep, road_frame_assembly, road_wheel_building, 
                   road_assembly, road_paint, road_qa, road_packaging],
            base_price=1299.99
        )
        
        electric_bike = BikeModel(
            id="electric",
            name="PowerGlide Electric Bike",
            type="electric",
            steps=[ebike_frame_prep, ebike_frame_welding, ebike_electronics, 
                   ebike_wheel_building, ebike_assembly, ebike_paint, 
                   ebike_electronics_testing, ebike_qa, ebike_packaging],
            base_price=1899.99
        )
        
        factory.add_bike_model(mountain_bike)
        factory.add_bike_model(road_bike)
        factory.add_bike_model(electric_bike)
        
        return factory
    
    def produce_bike(self, order_id: str, bike_index: int, bike_model: BikeModel) -> Any:
        """SimPy process for producing a single bike within an order"""
        total_time = 0
        
        for step in bike_model.steps:
            # Find needed resources
            needed_employees = []
            for skill, level in step.required_skills.items():
                suitable_employees = [e for e in self.factory.employees if e.has_skill(skill, level)]
                if suitable_employees:
                    needed_employees.append(suitable_employees[0])
            
            needed_machines = []
            for machine_type in step.required_machines:
                machine_resource = self.machine_resources.get(machine_type)
                if machine_resource:
                    needed_machines.append(machine_resource)
            
            # Request employee(s)
            with self.human_resources.get(step.required_skills[Skill.FRAME_WELDING]) as employee_request:
                yield employee_request
                
                # Request machine(s) if needed
                machine_requests = []
                for machine in needed_machines:
                    machine_requests.append(machine.request())
                
                for request in machine_requests:
                    yield request
                
                # Process production step
                step_time = step.duration
                total_time += step_time
                yield self.env.timeout(step_time)
                
                # Release machine resources
                for i, machine in enumerate(needed_machines):
                    machine.release(machine_requests[i])
                
                # Log step completion
                print(f"{self.env.now}: Completed {step.name} for order {order_id}, bike {bike_index}")
        
        # Log bike completion
        self.simulation_stats["bikes_produced"] += 1
        self.simulation_stats["total_production_time"] += total_time
        print(f"{self.env.now}: Completed bike {bike_index} for order {order_id}")
        return total_time
    
    def process_order(self, order: Order) -> Any:
        """SimPy process for handling an order"""
        # Log order receipt
        self.simulation_stats["orders_received"] += 1
        print(f"{self.env.now}: Received order {order.id} for {order.quantity} {order.bike_model.name}(s)")
        
        # Check material availability
        material_requirements = {}
        for step in order.bike_model.steps:
            for material_id, quantity in step.required_materials.items():
                material_requirements[material_id] = material_requirements.get(material_id, 0) + quantity * order.quantity
        
        for material_id, needed_quantity in material_requirements.items():
            if material_id not in self.factory.inventory or self.factory.inventory[material_id].quantity < needed_quantity:
                print(f"{self.env.now}: Order {order.id} cancelled due to insufficient materials")
                self.simulation_stats["orders_cancelled"] += 1
                return
        
        # Reserve materials
        for material_id, needed_quantity in material_requirements.items():
            self.factory.inventory[material_id].quantity -= needed_quantity
        
        # Start production for each bike
        order.status = OrderStatus.IN_PRODUCTION
        bike_processes = []
        for i in range(order.quantity):
            process = self.env.process(self.produce_bike(order.id, i+1, order.bike_model))
            bike_processes.append(process)
        
        # Wait for all bikes to be completed
        yield self.env.all_of(bike_processes)
        
        # Mark order as completed
        order.status = OrderStatus.COMPLETED
        self.simulation_stats["orders_completed"] += 1
        print(f"{self.env.now}: Completed order {order.id}")
    
    def order_generator(self, order_rate: float, max_orders: int) -> Any:
        """Generate random orders at specified rate"""
        for i in range(max_orders):
            # Create a random order
            customer = f"Customer {i+1}"
            bike_model_id = random.choice(list(self.factory.bike_models.keys()))
            bike_model = self.factory.bike_models[bike_model_id]
            quantity = random.randint(1, 5)
            due_date = datetime.now() + timedelta(days=random.randint(3, 14))
            
            order = Order.create(customer, bike_model, quantity, due_date)
            
            # Start processing order
            self.env.process(self.process_order(order))
            
            # Wait until next order
            interarrival_time = random.expovariate(1.0 / order_rate)
            yield self.env.timeout(interarrival_time)
    
    def run_simulation(self, duration: int, order_rate: float, max_orders: int) -> Dict:
        """Run the simulation for specified duration"""
        self.env.process(self.order_generator(order_rate, max_orders))
        self.env.run(until=duration)
        
        # Add some calculated statistics
        if self.simulation_stats["bikes_produced"] > 0:
            self.simulation_stats["avg_production_time"] = self.simulation_stats["total_production_time"] / self.simulation_stats["bikes_produced"]
        else:
            self.simulation_stats["avg_production_time"] = 0
            
        return self.simulation_stats


def run_simulation():
    """Run a bike factory simulation"""
    print("Starting Bike Factory Simulation")
    
    # Create SimPy environment
    env = simpy.Environment()
    
    # Create and run simulation
    simulation = FactorySimulation(env)
    
    # Run for 480 minutes (8 hours) with orders arriving every 90 minutes on average
    stats = simulation.run_simulation(duration=480, order_rate=90, max_orders=10)
    
    # Print results
    print("\nSimulation Results:")
    print(f"Orders received: {stats['orders_received']}")
    print(f"Orders completed: {stats['orders_completed']}")
    print(f"Orders cancelled: {stats['orders_cancelled']}")
    print(f"Bikes produced: {stats['bikes_produced']}")
    print(f"Average production time per bike: {stats['avg_production_time']:.1f} minutes")
    
    return stats


if __name__ == "__main__":
    run_simulation()