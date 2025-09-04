# Prefect flow
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from prefect import flow, task
from core_sync.implementations.state_manager import RedisStateManager
from core_sync.implementations.sync_engine import SimpleSyncEngine
from core_sync.implementations.adapters.vsphere import VSphereAdapter
from core_sync.implementations.adapters.netbox import NetboxAdapter
from core_sync.strategies.conservative import ConservativeSyncStrategy
from core_sync.config import config
from core_sync.utils.logging import get_logger

logger = get_logger(__name__)

@task
def create_state_manager() -> RedisStateManager:
    """Создание StateManager"""
    return RedisStateManager()

@task
def create_vsphere_adapter() -> VSphereAdapter:
    """Создание адаптера для vSphere"""
    return VSphereAdapter(
        host=config.VSPHERE_HOST,
        username=config.VSPHERE_USERNAME,
        password=config.VSPHERE_PASSWORD
    )

@task
def create_netbox_adapter() -> NetboxAdapter:
    """Создание адаптера для Netbox"""
    return NetboxAdapter()

@task
def create_sync_engine(state_manager: RedisStateManager) -> SimpleSyncEngine:
    """Создание SyncEngine"""
    return SimpleSyncEngine(state_manager)

@task
def create_sync_strategy() -> ConservativeSyncStrategy:
    """Создание стратегии синхронизации"""
    return ConservativeSyncStrategy()

@task
def execute_sync(sync_engine: SimpleSyncEngine, 
                source_adapter: VSphereAdapter, 
                target_adapter: NetboxAdapter,
                strategy: ConservativeSyncStrategy) -> dict:
    """Выполнение синхронизации"""
    return sync_engine.sync(source_adapter, target_adapter, strategy)

@flow(name="core-sync-flow")
def core_sync_flow():
    """Основной flow синхронизации"""
    logger.info("Starting core sync flow")
    
    # Создание компонентов
    state_manager = create_state_manager()
    vsphere_adapter = create_vsphere_adapter()
    netbox_adapter = create_netbox_adapter()
    sync_engine = create_sync_engine(state_manager)
    strategy = create_sync_strategy()
    
    # Выполнение синхронизации
    result = execute_sync(sync_engine, vsphere_adapter, netbox_adapter, strategy)
    
    logger.info(f"Sync flow completed with result: {result}")
    return result

if __name__ == "__main__":
    core_sync_flow()