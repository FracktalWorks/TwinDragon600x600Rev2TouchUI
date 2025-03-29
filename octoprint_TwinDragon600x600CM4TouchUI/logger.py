import logging
import os
import time
import glob
from datetime import datetime, timedelta

def setup_logger():
    # Create a logger object.
    logger = logging.getLogger(__name__)

    # Set the level of the logger. This can be DEBUG, INFO, WARNING, ERROR, or CRITICAL.
    logger.setLevel(logging.DEBUG)

    # Create a file handler for outputting log messages to a file.
    # Include the current date in the filename.
    handler = logging.FileHandler('/home/pi/.octoprint/logs/TouchUI_{}.log'.format(datetime.now().strftime('%Y-%m-%d-%H-%M')))

    # Set the level of the file handler. This can be DEBUG, INFO, WARNING, ERROR, or CRITICAL.
    handler.setLevel(logging.DEBUG)

    # Create a formatter.
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add the formatter to the handler.
    handler.setFormatter(formatter)

    # Add the handler to the logger.
    logger.addHandler(handler)

    # Create a stream handler for outputting log messages to the console.
    console_handler = logging.StreamHandler()

    # Set the level of the console handler. This can be DEBUG, INFO, WARNING, ERROR, or CRITICAL.
    console_handler.setLevel(logging.DEBUG)

    # Add the formatter to the console handler.
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger.
    logger.addHandler(console_handler)

    return logger


def delete_old_logs(logs_path='/home/pi/.octoprint/logs/{}', startsWith='TouchUI_'):
    """
    Deletes log files in the given directory that starts with a particular string if the number of
    files exceeds 5, starting with the oldest.
    """
    # Get a list of log files in the directory.
    log_files = sorted(glob.glob(logs_path.format(startsWith) + '*'), key=os.path.getmtime)

    # Delete the oldest log files if there are more than 5.
    for log_file in log_files[:-5]:
        os.remove(log_file)