# Абстрактные классы и интерфейсы
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel

class Entity(BaseModel):
    """Базовый класс для всех сущностей"""
    id: str
    source: str
    source_id: str
    last_updated: datetime
    checksum: str
    data: Dict[str, Any]

class StateManager(ABC):
    """Абстрактный класс для управления состоянием"""
    
    @abstractmethod
    def get_entity(self, source: str, source_id: str) -> Optional[Entity]:
        pass
    
    @abstractmethod
    def save_entity(self, entity: Entity) -> bool:
        pass
    
    @abstractmethod
    def delete_entity(self, source: str, source_id: str) -> bool:
        pass
    
    @abstractmethod
    def get_all_entities(self, source: Optional[str] = None) -> List[Entity]:
        pass

class DataSource(ABC):
    """Абстрактный класс для источников данных"""
    
    @abstractmethod
    def get_entities(self) -> List[Entity]:
        pass
    
    @abstractmethod
    def apply_changes(self, changes: List[Entity]) -> bool:
        pass

class SyncStrategy(ABC):
    """Абстрактный класс для стратегий синхронизации"""
    
    @abstractmethod
    def execute(self, source_entities: List[Entity], target_entities: List[Entity]) -> Dict[str, int]:
        pass

class SyncEngine(ABC):
    """Абстрактный класс для движка синхронизации"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    @abstractmethod
    def sync(self, source: DataSource, target: DataSource, strategy: SyncStrategy) -> Dict[str, Any]:
        pass