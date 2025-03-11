import scan
import testing
import time
import logger
import logging

LOGGER = logging.getLogger(__name__)
logger.setup_logger(LOGGER)

ERRORS_THRESHOLD = 8    # Number of exceptions that the program can catch in a row before closing itself.

# scan.setup()
#scan.kismet_run() 
scan.monitoring_mode()


def log_and_exit_creator():
    number_of_errors = 0

    def log_and_exit(exception):
        """
            Logs the exception as an error and increases counter of caught exceptions.
            If case of reaching the threshold stops the program.
        """
        nonlocal number_of_errors
        LOGGER.error(exception)
        LOGGER.exception(exception)
        if number_of_errors == ERRORS_THRESHOLD:
            exit(1)
        number_of_errors += 1

    return log_and_exit


log_and_exit = log_and_exit_creator()

while True:
    default_sleep = 1
    try:
        LOGGER.info("Scanning is started")
        scan.parse()
        LOGGER.info("Scanning has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during scanning")
        log_and_exit(e)
        continue

    time.sleep(default_sleep)

    try:
        LOGGER.info("Creating testing table is started")
        testing.init_testing_module()
        LOGGER.info("Creating testing table has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during Creating testing")
        log_and_exit(e)
        continue

    time.sleep(default_sleep)

    try:
        LOGGER.info("Checking SSID is started")
        testing.check_ssid()
        LOGGER.info("Checking SSID has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during checking SSID")
        log_and_exit(e)
        continue

    time.sleep(default_sleep)

    try:
        LOGGER.info("Checking MAC addresses is started")
        testing.check_mac_address()
        LOGGER.info("Checking MAC addresses has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during checking MAC addresses")
        log_and_exit(e)
        continue

    time.sleep(default_sleep)

    try:
        LOGGER.info("Scanning all SSID is started")
        testing.check_wpa2()
        LOGGER.info("Scanning all SSID has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during scanning all SSID")
        log_and_exit(e)
        continue

    time.sleep(default_sleep)

    try:
        LOGGER.info("Testing GPS location of devices is started")
        testing.check_gps()
        LOGGER.info("Testing GPS location of devices has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during testing GPS location of devices")
        log_and_exit(e)
        continue

    time.sleep(default_sleep)

    try:
        LOGGER.info("Testing fast aircrack is started")
        testing.start_fast_aircrack()
        LOGGER.info("Testing fast aircrack has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during testing fast aircrack")
        log_and_exit(e)
        continue

    # time.sleep(default_sleep)

    # try:
    #     LOGGER.info("Testing long aircrack is started")
    #     testing.start_long_aircrack()
    #     LOGGER.info("Testing long aircrack has been performed")
    # except Exception as e:
    #     LOGGER.error("ERROR problem during testing long aircrack")
    #     log_and_exit(e)
    #     continue

    # time.sleep(default_sleep)

    try:
        LOGGER.info("Testing WiFi connection is started")
        testing.checkConnection()
        LOGGER.info("Testing WiFi connection has been performed")
    except Exception as e:
        LOGGER.error("ERROR problem during testing WiFi connection")
        log_and_exit(e)
        continue

    scan.sleep()
    log_and_exit = log_and_exit_creator()   # Restart the counter of errors
