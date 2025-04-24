from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Protocol, Self, Callable, Any, Set
from datetime import datetime, timedelta, time
import uuid
import simpy
import random
import math

# === Core Types Module ===
class SkillLevel(Enum):
    NOVICE = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()
    EXPERT = auto()

class Skill(Enum):
    FRAME_WELDING = auto()       # Welding bike frames
    TUBE_CUTTING = auto()        # Cutting and preparing tubes
    COMPONENT_ASSEMBLY = auto()  # Assembling bike components
    WHEEL_BUILDING = auto()      # Building and truing wheels
    PAINTING = auto()            # Painting and finishing
    QUALITY_CONTROL = auto()     # Testing and quality assurance
    ELECTRONICS = auto()         # Installing electrical components for e-bikes
    MACHINING = auto()           # Operating CNC machines
    SUSPENSION_TUNING = auto()   # Adjusting and tuning suspension systems
    MAINTENANCE = auto()         # Machine maintenance

class WorkerType(Enum):
    FULL_TIME = auto()
    PART_TIME = auto()
    CONTRACTOR = auto()
    APPRENTICE = auto()

class Shift(Enum):
    MORNING = auto()  # 6am - 2pm
    AFTERNOON = auto()  # 2pm - 10pm
    NIGHT = auto()  # 10pm - 6am

class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

class ResourceStatus(Enum):
    AVAILABLE = auto()
    BUSY = auto()
    UNAVAILABLE = auto()
    MAINTENANCE = auto()
    BREAKDOWN = auto()
    ON_BREAK = auto()
    OFF_SHIFT = auto()

class MaintenanceType(Enum):
    ROUTINE = auto()  # Regular scheduled maintenance
    PREVENTIVE = auto()  # Preventive maintenance based on usage
    CORRECTIVE = auto()  # Fix after breakdown
    EMERGENCY = auto()  # Critical repair

class OrderStatus(Enum):
    RECEIVED = auto()
    SCHEDULED = auto()
    IN_PRODUCTION = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    DELAYED = auto()

# === Resource Module ===
@dataclass
class Resource(Protocol):
    id: str
    name: str
    status: ResourceStatus
    
    def is_available(self, start_time: datetime, duration: int) -> bool: ...

@dataclass
class WorkSchedule:
    shifts: Dict[DayOfWeek, Optional[Shift]] = field(default_factory=dict)
    availability: Dict[datetime, bool] = field(default_factory=dict)
    vacation_days: Set[datetime] = field(default_factory=set)
    sick_days: Set[datetime] = field(default_factory=set)
    
    def __post_init__(self):
        # Default to no shifts assigned
        for day in DayOfWeek:
            if day not in self.shifts:
                self.shifts[day] = None
    
    def is_available(self, dt: datetime) -> bool:
        # Check if date is in vacation or sick days
        if dt.date() in self.vacation_days or dt.date() in self.sick_days:
            return False
        
        # Check if time is within assigned shift
        day_of_week = DayOfWeek(dt.weekday())
        shift = self.shifts.get(day_of_week)
        
        if shift is None:  # Not scheduled to work this day
            return False
            
        # Check shift hours
        hour = dt.hour
        if shift == Shift.MORNING and 6 <= hour < 14:
            return True
        elif shift == Shift.AFTERNOON and 14 <= hour < 22:
            return True
        elif shift == Shift.NIGHT and (hour >= 22 or hour < 6):
            return True
        
        return False

@dataclass
class Employee:
    id: str
    name: str
    skills: Dict[Skill, SkillLevel]
    worker_type: WorkerType
    schedule: WorkSchedule = field(default_factory=WorkSchedule)
    status: ResourceStatus = ResourceStatus.AVAILABLE
    hourly_rate: float = 20.0
    fatigue_level: int = 0  # 0-100 scale
    experience_years: float = 1.0
    error_rate: float = 0.05  # Base error rate
    
    def has_skill(self, skill: Skill, level: SkillLevel) -> bool:
        return skill in self.skills and self.skills[skill].value >= level.value
    
    def is_available(self, start_time: datetime, duration: int) -> bool:
        if self.status not in (ResourceStatus.AVAILABLE, ResourceStatus.ON_BREAK):
            return False
            
        # Check entire duration of task
        end_time = start_time + timedelta(minutes=duration)
        current = start_time
        
        while current < end_time:
            if not self.schedule.is_available(current):
                return False
            current += timedelta(minutes=15)  # Check in 15-minute intervals
            
        return True
    
    def calculate_error_probability(self) -> float:
        """Calculate probability of errors based on fatigue, experience, etc."""
        # Base error rate adjusted by experience (decreases with experience)
        base = self.error_rate / math.sqrt(self.experience_years)
        
        # Fatigue increases error rate exponentially
        fatigue_factor = 1.0 + (self.fatigue_level / 50.0)**2
        
        return min(0.95, base * fatigue_factor)  # Cap at 95%
    
    def increase_fatigue(self, work_duration: int) -> None:
        """Increase fatigue based on work duration (in minutes)"""
        # More fatigue for longer tasks
        self.fatigue_level += int(work_duration / 30)
        self.fatigue_level = min(100, self.fatigue_level)
    
    def take_break(self, break_duration: int) -> None:
        """Reduce fatigue when taking a break"""
        # Breaks reduce fatigue
        self.fatigue_level -= int(break_duration / 15)
        self.fatigue_level = max(0, self.fatigue_level)

@dataclass
class MaintenanceLog:
    maintenance_id: str
    machine_id: str
    type: MaintenanceType
    performed_by: str  # Employee ID
    start_time: datetime
    duration: int  # minutes
    issues_found: List[str] = field(default_factory=list)
    parts_replaced: List[str] = field(default_factory=list)
    success: bool = True

@dataclass
class MaintenanceSchedule:
    routine_interval: int  # operating hours until routine maintenance
    last_routine: datetime = field(default_factory=datetime.now)
    preventive_checks: List[datetime] = field(default_factory=list)
    upcoming_maintenance: List[datetime] = field(default_factory=list)

@dataclass
class MachineCondition:
    wear_level: int = 0  # 0-100 scale
    last_inspection: Optional[datetime] = None
    known_issues: List[str] = field(default_factory=list)
    critical_threshold: int = 80  # Wear level at which breakdown risk increases dramatically
    
    def risk_of_failure(self) -> float:
        """Calculate probability of machine failure based on condition"""
        if self.wear_level >= self.critical_threshold:
            # Exponential increase in failure risk past threshold
            return min(0.90, 0.1 + ((self.wear_level - self.critical_threshold) / 20.0)**2)
        else:
            # Linear increase up to threshold
            return self.wear_level / (self.critical_threshold * 10)

@dataclass
class Machine:
    id: str
    name: str
    machine_type: str
    skills_required: Dict[Skill, SkillLevel]
    status: ResourceStatus = ResourceStatus.AVAILABLE
    maintenance_schedule: MaintenanceSchedule = field(default_factory=lambda: MaintenanceSchedule(routine_interval=480))
    condition: MachineCondition = field(default_factory=MachineCondition)
    maintenance_history: List[MaintenanceLog] = field(default_factory=list)
    operating_hours: int = 0
    installation_date: datetime = field(default_factory=datetime.now)
    expected_lifetime: int = 43800  # hours (5 years at 24/7 operation)
    maintenance_duration: Dict[MaintenanceType, int] = field(default_factory=lambda: {
        MaintenanceType.ROUTINE: 120,     # 2 hours
        MaintenanceType.PREVENTIVE: 240,  # 4 hours
        MaintenanceType.CORRECTIVE: 360,  # 6 hours
        MaintenanceType.EMERGENCY: 480    # 8 hours
    })
    
    def is_available(self, start_time: datetime, duration: int) -> bool:
        # Basic availability check
        if self.status not in (ResourceStatus.AVAILABLE, ResourceStatus.MAINTENANCE):
            return False
            
        # Check if maintenance is due soon
        hours_since_maintenance = (datetime.now() - self.maintenance_schedule.last_routine).total_seconds() / 3600
        if hours_since_maintenance >= self.maintenance_schedule.routine_interval:
            return False
            
        return True
    
    def needs_maintenance(self) -> bool:
        """Check if machine needs scheduled maintenance"""
        hours_since_maintenance = (datetime.now() - self.maintenance_schedule.last_routine).total_seconds() / 3600
        return hours_since_maintenance >= self.maintenance_schedule.routine_interval
    
    def increase_wear(self, operating_time: int) -> None:
        """Increase wear level based on operating time (minutes)"""
        # Convert minutes to hours
        hours = operating_time / 60
        self.operating_hours += hours
        
        # Calculate wear increase based on operating time
        # Machines wear faster as they age
        age_factor = self.operating_hours / self.expected_lifetime
        wear_increase = hours * (1 + age_factor)
        
        self.condition.wear_level += int(wear_increase)
        self.condition.wear_level = min(100, self.condition.wear_level)
    
    def perform_maintenance(self, maintenance_type: MaintenanceType, employee: Employee) -> MaintenanceLog:
        """Perform maintenance on the machine"""
        start_time = datetime.now()
        duration = self.maintenance_duration[maintenance_type]
        
        # Create maintenance log
        log = MaintenanceLog(
            maintenance_id=str(uuid.uuid4()),
            machine_id=self.id,
            type=maintenance_type,
            performed_by=employee.id,
            start_time=start_time,
            duration=duration
        )
        
        # Update machine state based on maintenance type
        if maintenance_type in (MaintenanceType.ROUTINE, MaintenanceType.PREVENTIVE):
            self.condition.wear_level = max(0, self.condition.wear_level - 30)
            self.maintenance_schedule.last_routine = start_time
            
        elif maintenance_type == MaintenanceType.CORRECTIVE:
            self.condition.wear_level = max(0, self.condition.wear_level - 50)
            self.status = ResourceStatus.AVAILABLE
            
        elif maintenance_type == MaintenanceType.EMERGENCY:
            self.condition.wear_level = max(0, self.condition.wear_level - 70)
            self.status = ResourceStatus.AVAILABLE
            
        # Add to history
        self.maintenance_history.append(log)
        return log
    
    def check_for_failure(self) -> bool:
        """Check if machine fails during operation"""
        failure_probability = self.condition.risk_of_failure()
        return random.random() < failure_probability

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
    error_prone: bool = False  # Whether this step is particularly error-prone
    fatigue_factor: float = 1.0  # How much this task contributes to fatigue
    
    def can_be_performed_by(self, employee: Employee) -> bool:
        return all(employee.has_skill(skill, level) for skill, level in self.required_skills.items())
    
    def calculate_actual_duration(self, employee: Employee) -> int:
        """Calculate actual duration based on worker skill and fatigue"""
        # Base duration
        duration = self.duration
        
        # Skill factor - higher skill reduces time
        skill_factor = 1.0
        for skill, required_level in self.required_skills.items():
            if skill in employee.skills:
                employee_level = employee.skills[skill]
                # Expert is 30% faster than novice
                skill_factor = min(skill_factor, 1.0 - (employee_level.value - required_level.value) * 0.1)
        
        # Fatigue factor - higher fatigue increases time
        fatigue_factor = 1.0 + (employee.fatigue_level / 100.0) * 0.3  # Up to 30% slower when fatigued
        
        # Calculate and return the adjusted duration
        return int(duration * skill_factor * fatigue_factor)

# === Simulation Module ===
class MaintenanceManager:
    def __init__(self, env: simpy.Environment, factory):
        self.env = env
        self.factory = factory
        self.maintenance_employees = [e for e in factory.employees 
                                     if Skill.MAINTENANCE in e.skills]
        self.scheduled_maintenance = []
        self.emergency_queue = []
        self.maintenance_stats = {
            "routine_performed": 0,
            "preventive_performed": 0,
            "corrective_performed": 0,
            "emergency_performed": 0,
            "total_downtime": 0
        }
        
        # Start the maintenance scheduling process
        self.env.process(self.maintenance_scheduler())
    
    def schedule_maintenance(self, machine: Machine, maintenance_type: MaintenanceType) -> None:
        """Schedule maintenance for a machine"""
        if maintenance_type in (MaintenanceType.EMERGENCY, MaintenanceType.CORRECTIVE):
            self.emergency_queue.append((machine, maintenance_type))
        else:
            self.scheduled_maintenance.append((machine, maintenance_type))
    
    def maintenance_scheduler(self):
        """SimPy process to manage maintenance activities"""
        while True:
            # First, handle emergency repairs
            if self.emergency_queue:
                machine, maint_type = self.emergency_queue.pop(0)
                
                # Find available maintenance employee
                available_employees = [e for e in self.maintenance_employees 
                                      if e.status == ResourceStatus.AVAILABLE 
                                      and e.has_skill(Skill.MAINTENANCE, SkillLevel.INTERMEDIATE)]
                
                if available_employees:
                    employee = available_employees[0]
                    employee.status = ResourceStatus.BUSY
                    machine.status = ResourceStatus.MAINTENANCE
                    
                    # Record start time for downtime calculation
                    start_time = self.env.now
                    
                    # Perform maintenance
                    duration = machine.maintenance_duration[maint_type]
                    yield self.env.timeout(duration)
                    
                    # Update stats
                    self.maintenance_stats["total_downtime"] += duration
                    if maint_type == MaintenanceType.EMERGENCY:
                        self.maintenance_stats["emergency_performed"] += 1
                    else:
                        self.maintenance_stats["corrective_performed"] += 1
                    
                    # Update machine and employee status
                    machine.perform_maintenance(maint_type, employee)
                    employee.status = ResourceStatus.AVAILABLE
                else:
                    # No available maintenance employee, try again later
                    yield self.env.timeout(30)  # Check again in 30 minutes
            
            # Handle scheduled maintenance
            elif self.scheduled_maintenance:
                machine, maint_type = self.scheduled_maintenance.pop(0)
                
                # Find available maintenance employee with appropriate skill
                skill_level = SkillLevel.NOVICE if maint_type == MaintenanceType.ROUTINE else SkillLevel.INTERMEDIATE
                available_employees = [e for e in self.maintenance_employees 
                                      if e.status == ResourceStatus.AVAILABLE 
                                      and e.has_skill(Skill.MAINTENANCE, skill_level)]
                
                if available_employees and machine.status == ResourceStatus.AVAILABLE:
                    employee = available_employees[0]
                    employee.status = ResourceStatus.BUSY
                    machine.status = ResourceStatus.MAINTENANCE
                    
                    # Record start time for downtime calculation
                    start_time = self.env.now
                    
                    # Perform maintenance
                    duration = machine.maintenance_duration[maint_type]
                    yield self.env.timeout(duration)
                    
                    # Update stats
                    self.maintenance_stats["total_downtime"] += duration
                    if maint_type == MaintenanceType.ROUTINE:
                        self.maintenance_stats["routine_performed"] += 1
                    else:
                        self.maintenance_stats["preventive_performed"] += 1
                    
                    # Update machine and employee status
                    machine.perform_maintenance(maint_type, employee)
                    employee.status = ResourceStatus.AVAILABLE
                else:
                    # Either machine is busy or no maintenance person available
                    # Put back in queue and try later
                    self.scheduled_maintenance.append((machine, maint_type))
                    yield self.env.timeout(60)  # Check again in 60 minutes
            
            # Check machines for needed maintenance
            for machine in self.factory.machines:
                if machine.needs_maintenance() and machine.status == ResourceStatus.AVAILABLE:
                    self.schedule_maintenance(machine, MaintenanceType.ROUTINE)
                    
                # Check for preventive maintenance based on condition
                elif (machine.condition.wear_level > 50 and 
                      machine.status == ResourceStatus.AVAILABLE and
                      not any(m[0].id == machine.id for m in self.scheduled_maintenance)):
                    self.schedule_maintenance(machine, MaintenanceType.PREVENTIVE)
            
            # Wait before next maintenance check
            yield self.env.timeout(60)  # Check every hour

class EmployeeManager:
    def __init__(self, env: simpy.Environment, factory):
        self.env = env
        self.factory = factory
        self.break_schedule = {}  # Scheduled breaks
        
        # Start the break scheduler
        self.env.process(self.manage_employee_schedules())
    
    def manage_employee_schedules(self):
        """Manage employee shifts, breaks, and fatigue"""
        while True:
            current_time = datetime.fromtimestamp(self.env.now * 60)  # Convert SimPy time to datetime
            
            for employee in self.factory.employees:
                # Check if employee should be on shift
                if employee.schedule.is_available(current_time):
                    if employee.status == ResourceStatus.OFF_SHIFT:
                        employee.status = ResourceStatus.AVAILABLE
                else:
                    if employee.status not in (ResourceStatus.OFF_SHIFT, ResourceStatus.UNAVAILABLE):
                        employee.status = ResourceStatus.OFF_SHIFT
                
                # Manage breaks based on fatigue
                if (employee.status == ResourceStatus.AVAILABLE and 
                    employee.fatigue_level > 70 and
                    employee.id not in self.break_schedule):
                    
                    # Schedule a break
                    break_duration = 30  # 30 minutes
                    employee.status = ResourceStatus.ON_BREAK
                    self.break_schedule[employee.id] = self.env.now + break_duration
                
                # Check if break is over
                if (employee.id in self.break_schedule and 
                    self.env.now >= self.break_schedule[employee.id]):
                    
                    employee.take_break(30)  # Reduce fatigue
                    employee.status = ResourceStatus.AVAILABLE
                    del self.break_schedule[employee.id]
                
                # Natural fatigue reduction during off-shift
                if employee.status == ResourceStatus.OFF_SHIFT:
                    employee.fatigue_level = max(0, employee.fatigue_level - 1)
            
            # Check every 15 minutes
            yield self.env.timeout(15)

# === Factory Simulation ===
class FactorySimulation:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.factory = self.create_realistic_factory()
        self.skill_resources = {}  # Resources by skill
        self.machine_resources = {}  # Resources by machine type
        self.maintenance_manager = MaintenanceManager(env, self.factory)
        self.employee_manager = EmployeeManager(env, self.factory)
        
        self.simulation_stats = {
            "orders_received": 0,
            "orders_completed": 0,
            "orders_cancelled": 0,
            "bikes_produced": 0,
            "total_production_time": 0,
            "machine_breakdowns": 0,
            "quality_issues": 0,
            "employee_errors": 0,
            "avg_employee_fatigue": 0
        }
        
        # Create SimPy resources for each skill
        for skill in Skill:
            skilled_employees = sum(1 for e in self.factory.employees if skill in e.skills)
            self.skill_resources[skill] = simpy.Resource(env, capacity=skilled_employees)
        
        # Create resources for each machine type
        machine_types = set(machine.machine_type for machine in self.factory.machines)
        for machine_type in machine_types:
            machines_of_type = sum(1 for m in self.factory.machines if m.machine_type == machine_type)
            self.machine_resources[machine_type] = simpy.Resource(env, capacity=machines_of_type)
    
    def create_realistic_factory(self) -> BikeFactory:
        # Create a factory with realistic employees, machines, etc.
        factory = BikeFactory("TechCycle Advanced Bikes")
        
        # Create realistic employees with varied skills, shift patterns, etc.
        employees = [
            # Welders
            ("John Smith", WorkerType.FULL_TIME, 
             {Skill.FRAME_WELDING: SkillLevel.EXPERT, Skill.TUBE_CUTTING: SkillLevel.ADVANCED, 
              Skill.MAINTENANCE: SkillLevel.INTERMEDIATE}, 28.50, 8.5),
              
            ("Maria Garcia", WorkerType.FULL_TIME, 
             {Skill.FRAME_WELDING: SkillLevel.ADVANCED, Skill.TUBE_CUTTING: SkillLevel.INTERMEDIATE}, 
             24.75, 5.2),
             
            ("Robert Chen", WorkerType.PART_TIME, 
             {Skill.FRAME_WELDING: SkillLevel.INTERMEDIATE, Skill.MAINTENANCE: SkillLevel.NOVICE}, 
             22.00, 2.8),
            
            # Assemblers
            ("Jamal Washington", WorkerType.FULL_TIME, 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.EXPERT, Skill.WHEEL_BUILDING: SkillLevel.ADVANCED}, 
             26.50, 7.3),
             
            ("Sarah Johnson", WorkerType.FULL_TIME, 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED, Skill.SUSPENSION_TUNING: SkillLevel.EXPERT}, 
             27.00, 6.5),
             
            ("Miguel Rodriguez", WorkerType.PART_TIME, 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.INTERMEDIATE, Skill.QUALITY_CONTROL: SkillLevel.INTERMEDIATE}, 
             20.50, 3.2),
            
            # Specialists
            ("Li Wei", WorkerType.FULL_TIME, 
             {Skill.WHEEL_BUILDING: SkillLevel.EXPERT, Skill.COMPONENT_ASSEMBLY: SkillLevel.INTERMEDIATE}, 
             25.75, 9.1),
             
            ("Aisha Patel", WorkerType.FULL_TIME, 
             {Skill.ELECTRONICS: SkillLevel.EXPERT, Skill.COMPONENT_ASSEMBLY: SkillLevel.ADVANCED}, 
             29.50, 4.8),
             
            ("Thomas Mueller", WorkerType.FULL_TIME, 
             {Skill.MACHINING: SkillLevel.EXPERT, Skill.MAINTENANCE: SkillLevel.EXPERT}, 
             31.00, 12.5),
            
            # Painters
            ("Sofia Russo", WorkerType.FULL_TIME, 
             {Skill.PAINTING: SkillLevel.EXPERT}, 24.00, 8.9),
             
            ("James Wilson", WorkerType.PART_TIME, 
             {Skill.PAINTING: SkillLevel.ADVANCED, Skill.MAINTENANCE: SkillLevel.NOVICE}, 
             21.50, 3.7),
            
            # QA/QC
            ("Emily Taylor", WorkerType.FULL_TIME, 
             {Skill.QUALITY_CONTROL: SkillLevel.EXPERT, Skill.SUSPENSION_TUNING: SkillLevel.ADVANCED}, 
             27.50, 9.2),
             
            ("David Kim", WorkerType.FULL_TIME, 
             {Skill.QUALITY_CONTROL: SkillLevel.ADVANCED, Skill.WHEEL_BUILDING: SkillLevel.INTERMEDIATE}, 
             25.00, 6.1),
            
            # Maintenance specialists
            ("Carlos Oliveira", WorkerType.FULL_TIME, 
             {Skill.MAINTENANCE: SkillLevel.EXPERT, Skill.MACHINING: SkillLevel.INTERMEDIATE, 
              Skill.ELECTRONICS: SkillLevel.INTERMEDIATE}, 30.00, 15.3),
              
            ("Fatima Hassan", WorkerType.FULL_TIME, 
             {Skill.MAINTENANCE: SkillLevel.ADVANCED, Skill.FRAME_WELDING: SkillLevel.NOVICE}, 
             26.00, 7.8),
             
            # Apprentices
            ("Tyler Robinson", WorkerType.APPRENTICE, 
             {Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE, Skill.TUBE_CUTTING: SkillLevel.NOVICE}, 
             17.50, 0.8),
             
            ("Nina Patel", WorkerType.APPRENTICE, 
             {Skill.WHEEL_BUILDING: SkillLevel.NOVICE, Skill.COMPONENT_ASSEMBLY: SkillLevel.NOVICE}, 
             17.50, 1.2)
        ]
        
        # Create schedules and add employees
        for i, (name, worker_type, skills, hourly_rate, experience) in enumerate(employees):
            # Create realistic work schedules
            schedule = WorkSchedule()
            
            if worker_type == WorkerType.FULL_TIME:
                # Full-time employees work 5 days a week
                shift = Shift.MORNING if i % 3 == 0 else (Shift.AFTERNOON if i % 3 == 1 else Shift.NIGHT)
                for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
                    schedule.shifts[day] = shift
                    
            elif worker_type == WorkerType.PART_TIME:
                # Part-time employees work 3 days a week
                shift = Shift.MORNING if i % 2 == 0 else Shift.AFTERNOON
                days = [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY] if i % 2 == 0 else [DayOfWeek.TUESDAY, DayOfWeek.THURSDAY, DayOfWeek.SATURDAY]
                for day in days:
                    schedule.shifts[day] = shift
                    
            elif worker_type == WorkerType.APPRENTICE:
                # Apprentices work 4 days a week, morning shift
                shift = Shift.MORNING
                for day in [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.THURSDAY, DayOfWeek.FRIDAY]:
                    schedule.shifts[day] = shift
            
            # Add random vacation days
            for _ in range(random.randint(0, 10)):
                vacation_day = datetime.now() + timedelta(days=random.randint(1, 180))
                schedule.vacation_days.add(vacation_day.date())
            
            # Calculate error rate based on experience
            error_rate = max(0.01, 0.1 - (experience / 100))
            
            # Create and add employee
            employee = Employee(
                id=f"emp-{i+1}",
                name=name,
                skills=skills,
                worker_type=worker_type,
                schedule=schedule,
                hourly_rate=hourly_rate,
                experience_years=experience,
                error_rate=error_rate
            )
            factory.add_employee(employee)
        
        # Rest of factory creation (machines, materials, etc.)
        # [...]
        
        return factory
    
    def produce_bike(self, order_id: str, bike_index: int, bike_model: BikeModel) -> Any:
        """SimPy process for producing a single bike within an order"""
        # Implementation with realistic employee scheduling, machine failures, etc.
        # [...]
        
    def process_order(self, order: Order) -> Any:
        """SimPy process for handling an order with realistic constraints"""
        # Implementation with material checks, scheduling based on shifts, etc.
        # [...]
        
    def run_simulation(self, duration: int, order_rate: float, max_orders: int) -> Dict:
        """Run the simulation for specified duration with realistic time management"""
        # [...]
        return self.simulation_stats