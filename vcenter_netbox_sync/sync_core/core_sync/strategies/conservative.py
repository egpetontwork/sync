# Консервативная стратегия
from typing import Dict, List
from ..interfaces import SyncStrategy, Entity

class ConservativeSyncStrategy(SyncStrategy):
    """Консервативная стратегия синхронизации"""
    
    def execute(self, source_entities: List[Entity], target_entities: List[Entity]) -> Dict[str, int]:
        """Выполнение консервативной синхронизации"""
        result = {
            "created": 0,
            "updated": 0,
            "deleted": 0,
            "conflicts": 0
        }
        
        # Создаем словари для быстрого поиска
        source_map = {e.source_id: e for e in source_entities}
        target_map = {e.source_id: e for e in target_entities}
        
        # Определяем новые и измененные entities
        for source_id, entity in source_map.items():
            if source_id not in target_map:
                result["created"] += 1
            elif entity.checksum != target_map[source_id].checksum:
                result["updated"] += 1
        
        # В консервативной стратегии не удаляем entities
        return result