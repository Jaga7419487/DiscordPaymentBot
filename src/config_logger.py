import logging

import colorlog

from constants import LOG_LEVEL


class LogFormatter(colorlog.ColoredFormatter):
    def format(self, record: logging.LogRecord) -> str:
        message = f"{self.formatTime(record)} - {record.levelname} - {record.module}:{record.lineno} - {record.getMessage()}"
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        escapes = self._escape_code_map(record.levelname)
        return self._append_reset(f"{escapes['log_color']}{message}", escapes)


handler = colorlog.StreamHandler()
handler.setFormatter(
    LogFormatter(
        "%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)

logger = logging.getLogger("DiscordPaymentBot")  # custom logger for the dc bot only
logger.setLevel(LOG_LEVEL)
logger.addHandler(handler)
logger.propagate = (
    False  # prevent log messages from being propagated to the root logger
)


def get_logger(name: str) -> logging.Logger:
    return logger.getChild(name)


if __name__ == "__main__":
    logger.debug("Debug logging")
    logger.info("Info logging")
    logger.warning("Warning logging")
    logger.error("Error logging")
    logger.critical("Critical logging")
