import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("my_app")
logger.setLevel(logging.DEBUG)  

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)   
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler("app.log", maxBytes=2000000, backupCount=3, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)     
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger.debug("This is a debug message")
logger.info("Program started")
logger.warning("This is a warning")
logger.error("An error occurred")
logger.critical("Critical issue!")
