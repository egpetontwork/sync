# Реализация StateManager
import redis
import json
from typing import List, Optional
from ..interfaces import StateManager, Entity
from ..config import config

class RedisStateManager(StateManager):
    """Реализация StateManager с использованием Redis"""
    
    def __init__(self):
        self.redis = redis.from_url(config.REDIS_URL)
    
    def _get_key(self, source: str, source_id: str) -> str:
        return f"entity:{source}:{source_id}"
    
    def get_entity(self, source: str, source_id: str) -> Optional[Entity]:
        key = self._get_key(source, source_id)
        data = self.redis.get(key)
        if data:
            return Entity.parse_raw(data)
        return None
    
    def save_entity(self, entity: Entity) -> bool:
        key = self._get_key(entity.source, entity.source_id)
        return self.redis.set(key, entity.json())
    
    def delete_entity(self, source: str, source_id: str) -> bool:
        key = self._get_key(source, source_id)
        return bool(self.redis.delete(key))
    
    def get_all_entities(self, source: Optional[str] = None) -> List[Entity]:
        pattern = "entity:*" if source is None else f"entity:{source}:*"
        keys = self.redis.keys(pattern)
        entities = []
        
        for key in keys:
            data = self.redis.get(key)
            if data:
                entities.append(Entity.parse_raw(data))
        
        return entities