# Реализация SyncEngine
from typing import Dict, Any, List
from ..interfaces import SyncEngine, DataSource, SyncStrategy, Entity
from ..utils.logging import get_logger

logger = get_logger(__name__)

class SimpleSyncEngine(SyncEngine):
    """Простая реализация SyncEngine"""
    
    def sync(self, source: DataSource, target: DataSource, strategy: SyncStrategy) -> Dict[str, Any]:
        """Выполнение синхронизации между источником и целью"""
        logger.info("Starting synchronization process")
        
        # Получение entities из источника и цели
        source_entities = source.get_entities()
        target_entities = target.get_entities()
        
        logger.info(f"Retrieved {len(source_entities)} source entities and {len(target_entities)} target entities")
        
        # Выполнение стратегии синхронизации
        result = strategy.execute(source_entities, target_entities)
        
        # Применение изменений к цели
        changes = self._calculate_changes(result, source_entities, target_entities)
        if changes:
            target.apply_changes(changes)
        
        logger.info(f"Synchronization completed: {result}")
        return result
    
    def _calculate_changes(self, result: Dict[str, Any], 
                          source_entities: List[Entity], 
                          target_entities: List[Entity]) -> List[Entity]:
        """Вычисление изменений для применения"""
        changes = []
        
        # Создаем словари для быстрого поиска
        source_map = {e.source_id: e for e in source_entities}
        target_map = {e.source_id: e for e in target_entities}
        
        # Добавляем новые и измененные entities
        for source_id, entity in source_map.items():
            if source_id not in target_map or entity.checksum != target_map[source_id].checksum:
                changes.append(entity)
        
        return changes