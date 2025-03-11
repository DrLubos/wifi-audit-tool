import logging
import logging.handlers as handlers
import sys
import os

if os.path.isdir('/var/www/html/logs') == False:
    os.mkdir('/var/www/html/logs')

LOG_FILENAME = "/var/www/html/logs/logging.log"
LOG_FORMAT = '%(asctime)-15s %(levelname)s: %(message)s'
FORMATTER = logging.Formatter(LOG_FORMAT)

# Nasetupovat handler na konzolovy vystup
STREAM_HANDLER = logging.StreamHandler()
STREAM_HANDLER.setLevel(logging.DEBUG)
STREAM_HANDLER.setStream(sys.stdout)
STREAM_HANDLER.setFormatter(FORMATTER)

# Nasetupovat handler na suborovy vystup
FILE_HANDLER = handlers.RotatingFileHandler(filename=LOG_FILENAME,
                                            maxBytes=1048576,   # 1 MB
                                            backupCount=3)
FILE_HANDLER.setLevel(logging.WARNING)
FILE_HANDLER.setFormatter(FORMATTER)


def setup_logger(logger):
    logger.setLevel(logging.DEBUG)
    logger.addHandler(FILE_HANDLER)
    logger.addHandler(STREAM_HANDLER)

#os.system("ln /home/pi/pythonProject/{} /var/www/html/{}".format(LOG_FILENAME,LOG_FILENAME))