# Утилиты логирования
import logging
import json
from pythonjsonlogger import jsonlogger
from ..config import config

def get_logger(name: str) -> logging.Logger:
    """Создание и настройка логгера"""
    logger = logging.getLogger(name)
    logger.setLevel(config.LOG_LEVEL)
    
    if not logger.handlers:
        # JSON форматтер
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        )
        
        # Обработчик для stdout
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger