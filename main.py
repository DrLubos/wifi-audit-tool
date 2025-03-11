from typing import Callable
import time
import sys

from config import get_config
from logger import get_logger


CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(CONFIG["logger"]["name"], CONFIG["logger"]["file"])


start_time = time.time()


def log_and_exit_creator() -> Callable[[Exception], None]:
	"""
	Creates a function that logs exceptions and exits the program if a threshold is reached.
	"""
	number_of_errors = 0

	def log_and_exit(exception: Exception) -> None:
		"""
		logs the exception as an error and increases counter of caught exceptions.
		If case of reaching the threshold stops the program.
		"""
		nonlocal number_of_errors
		LOGGER.critical(str(exception))
		number_of_errors += 1

		if number_of_errors >= CONFIG["errors_threshold"]:
			LOGGER.critical("Error threshold reached! Exiting...")
			sys.exit(1)

	return log_and_exit


log_and_exit = log_and_exit_creator()

end_time = start_time  # Initialize end_time to avoid unbound error

while True:
	try:
		LOGGER.info("Scanning started")
		print("Scanning started")
		LOGGER.info("Scanning completed")
		end_time = time.time()
	except KeyboardInterrupt:
		LOGGER.info("KeyboardInterrupt Exiting...")
		break
	except Exception as e:
		LOGGER.error("SCAN - Problem during scanning")
		log_and_exit(e)
		continue

	try:
		LOGGER.debug(f'Sleeping for {CONFIG["main_sleep"]} seconds')
		time.sleep(CONFIG["main_sleep"])
	except KeyboardInterrupt:
		LOGGER.info("KeyboardInterrupt Exiting...")
		break
	break

run_time = end_time - start_time
LOGGER.debug(f"Program ran for {run_time} seconds.")
