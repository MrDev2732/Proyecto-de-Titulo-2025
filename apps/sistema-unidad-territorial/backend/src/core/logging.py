import logging
import os
from datetime import datetime


class CustomFormatter(logging.Formatter):
    def format(self, record):
        record.created_datetime = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M')
        return super().format(record)


def configure_logging():
    formatter = CustomFormatter('%(created_datetime)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(name)s - %(message)s')

    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Add standard stream handler
    root_handler = logging.StreamHandler()
    root_handler.setFormatter(formatter)
    root_logger.addHandler(root_handler)

    # Configurar loggers específicos de la aplicación
    for logger_name in ['src', 'src.features']:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(root_handler)
        logger.propagate = False

    # Configurar uvicorn para usar nuestro formateador personalizado
    for logger_name in ['uvicorn', 'uvicorn.error', 'uvicorn.access']:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(root_handler)
        logger.propagate = False


def get_logger(name):
    os.makedirs('logs', exist_ok=True)
    log_file = os.path.join('logs', 'logs.log')

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # File handler for local logs
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        formatter = CustomFormatter('%(created_datetime)s | %(levelname)s | [%(filename)s:%(lineno)d] | %(name)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        logger.propagate = False

    return logger


configure_logging()
