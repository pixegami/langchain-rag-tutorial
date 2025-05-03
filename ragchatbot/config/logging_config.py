# logging_config.py remains the same
from colorama import Fore, Style
import logging

class CustomFormatter(logging.Formatter):
    def format(self, record):
        log_colors = {
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.MAGENTA,
            "DEBUG": Fore.CYAN
        }
        color = log_colors.get(record.levelname, Fore.WHITE)
        return f"{color}{record.levelname}:{Style.RESET_ALL}     {record.getMessage()}"  # Reset after level
