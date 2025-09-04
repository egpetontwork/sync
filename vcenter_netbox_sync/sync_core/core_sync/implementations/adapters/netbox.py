# Адаптер для Netbox
import requests
import hashlib
import json
from datetime import datetime
from typing import List, Dict
from ...interfaces import Entity
from .base import BaseDataSource
from ...utils.logging import get_logger
from ...config import config

logger = get_logger(__name__)

class NetboxAdapter(BaseDataSource):
    """Адаптер для работы с Netbox"""
    
    def __init__(self):
        super().__init__("netbox")
        self.url = config.NETBOX_URL
        self.token = config.NETBOX_TOKEN
        self.headers = {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }
    
    def _fetch_raw_data(self) -> List[Dict]:
        """Получение сырых данных из Netbox"""
        try:
            logger.info("Fetching data from Netbox")
            response = requests.get(
                f"{self.url}/api/virtualization/virtual-machines/",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()["results"]
        except Exception as e:
            logger.error(f"Error fetching from Netbox: {e}")
            return []
    
    def _convert_to_entities(self, raw_data: List[Dict]) -> List[Entity]:
        """Преобразование сырых данных Netbox в entities"""
        entities = []
        for item in raw_data:
            # Создаем checksum на основе данных
            checksum_data = {
                "name": item["name"],
                "status": item["status"]["value"],
                "vcpus": item["vcpus"],
                "memory": item["memory"]
            }
            checksum = hashlib.md5(
                json.dumps(checksum_data, sort_keys=True).encode()
            ).hexdigest()
            
            entity = Entity(
                id=f"netbox-{item['id']}",
                source="netbox",
                source_id=str(item["id"]),
                last_updated=datetime.now(),
                checksum=checksum,
                data=item
            )
            entities.append(entity)
        
        return entities
    
    def _apply_changes_impl(self, changes: List[Entity]) -> bool:
        """Применение изменений к Netbox"""
        # В реальной реализации здесь будет код для применения изменений к Netbox
        logger.info(f"Would apply {len(changes)} changes to Netbox")
        return True