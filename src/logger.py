"""Logger config for project"""
import logzero
import logging


def get_logger(name: str) -> None:
    """Init logger"""
    _formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    logger = logzero.setup_logger(
        name=name,
        logfile="logfile.log",
        level=logging.DEBUG,
        disableStderrLogger=True,
        formatter=_formatter,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    return logger
