# Базовый адаптер
from abc import ABC, abstractmethod
from typing import List, Dict
from ...interfaces import DataSource, Entity
from ...utils.logging import get_logger

logger = get_logger(__name__)

class BaseDataSource(DataSource, ABC):
    """Базовый класс для адаптеров источников данных"""
    
    def __init__(self, name: str):
        self.name = name
    
    def get_entities(self) -> List[Entity]:
        """Получение всех entities из источника"""
        logger.info(f"Fetching entities from {self.name}")
        raw_data = self._fetch_raw_data()
        return self._convert_to_entities(raw_data)
    
    def apply_changes(self, changes: List[Entity]) -> bool:
        """Применение изменений к источнику"""
        logger.info(f"Applying {len(changes)} changes to {self.name}")
        return self._apply_changes_impl(changes)
    
    @abstractmethod
    def _fetch_raw_data(self) -> List[Dict]:
        """Абстрактный метод для получения сырых данных"""
        pass
    
    @abstractmethod
    def _convert_to_entities(self, raw_data: List[Dict]) -> List[Entity]:
        """Абстрактный метод для преобразования сырых данных в entities"""
        pass
    
    @abstractmethod
    def _apply_changes_impl(self, changes: List[Entity]) -> bool:
        """Абстрактный метод для применения изменений"""
        pass
