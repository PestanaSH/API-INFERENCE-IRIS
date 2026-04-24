import logging
import sys
from datetime import datetime
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Customized formatter that adds extra fields to each log.  
    """

    def add_fields(self, log_record, record, message_dict):
        log_record["timestamp"] = datetime.utcnow().isoformat() + 'Z'
        log_record["level"] = record.levelname
        log_record["service"] = 'api-iris'
        log_record["logger"] = record.name
         
        if not log_record.get('message'):
           log_record["message"] = record.getMessage()





def setup_logging(level: str = "INFO") -> logging.Logger:
     """
        Configures and returns a logger with JSON format.

        Args:

        level: Minimum log level (DEBUG, INFO, WARNING, ERROR)

        Returns:
        Configured JSON logger
    """
     logger = logging.getLogger("api")
     logger.setLevel(getattr(logging, level.upper()))
     handler = logging.StreamHandler(sys.stdout)
     handler.setFormatter(CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'))
     logger.handlers = []
     logger.addHandler(handler)
     logger.propagate = False
     
     return logger

logger = setup_logging()