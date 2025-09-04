# Конфигурация приложения
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # vSphere
    VSPHERE_HOST: str = os.getenv("VSPHERE_HOST", "vcenter.example.com")
    VSPHERE_USERNAME: str = os.getenv("VSPHERE_USERNAME", "admin")
    VSPHERE_PASSWORD: str = os.getenv("VSPHERE_PASSWORD", "password")
    
    # Netbox
    NETBOX_URL: str = os.getenv("NETBOX_URL", "http://netbox.example.com")
    NETBOX_TOKEN: str = os.getenv("NETBOX_TOKEN", "token")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"

config = Settings()