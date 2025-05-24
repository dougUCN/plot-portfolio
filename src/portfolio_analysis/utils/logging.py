import logging
import logging.config
import os
from pathlib import Path
from typing import Union

from portfolio_analysis.utils.constants import ROOT_DIR


def _setup_logging(
    default_path: Union[str, Path] = ROOT_DIR / "logging_config.ini",
    default_level: int = logging.INFO,
    env_key: str = "LOG_CFG",
):
    """Setup logging configuration from an INI file.

    This function is automatically called when this module is imported.
    DO NOT call this function directly in your code unless you want to
    override the default logging configuration.

    Args:
        default_path (str or Path, optional): Path to the logging configuration file.
            Defaults to ROOT_DIR/"logging_config.ini".
        default_level (int, optional): Default logging level if config file is not found.
            Defaults to logging.INFO.
        env_key (str, optional): Environment variable that can override the config path.
            Defaults to "LOG_CFG".
    """
    value = os.getenv(env_key, None)
    if value is not None:
        path = Path(value)
    elif isinstance(default_path, str):
        path = Path(default_path)
    else:
        path = default_path

    if path.is_file():
        logging.config.fileConfig(path, disable_existing_loggers=False)
    else:
        logging.basicConfig(
            level=default_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name.

    This is the primary function you should use to obtain a logger in your module.
    Typically, you should pass `__name__` as the parameter to get a logger that
    shows your module's name in the logs.

    Args:
        name (str): Name of the logger.

    Returns:
        logging.Logger: Logger instance.

    Examples:
        >>> from cvi.ds.utils.logging import get_logger
        >>> logger = get_logger("my_logger")
        >>> logger.info("This is an info message.")
        >>> logger.error("This is an error message.")
    """
    return logging.getLogger(name)


# Initialize logging configuration when module is imported
# This happens only once when the module is first imported
_setup_logging()
