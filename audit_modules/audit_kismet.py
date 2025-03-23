import os
import subprocess

from config import get_config
from logger import get_logger

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

def start_kismet():
	"""
	Starts kismet in daemon mode.

	Returns:
		str: "Message"
		int: http status code
	"""
	monitoring_interface = CONFIG['interface']['monitoring']
	command = f"kismet -c {monitoring_interface} --daemonize --silent"
	#create folder CONFIG['kismet']['file'] if it does not exist
	if not os.path.exists(CONFIG['kismet']['file']):
		os.makedirs(CONFIG['kismet']['file'])
	try:
		subprocess.Popen(
			command,
			shell=True,
			cwd=CONFIG['kismet']['file'],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL
		)
		LOGGER.info("Kismet started.")
		return "Started", 200
	except Exception as e:
		LOGGER.error(f"Failed to start kismet: {e}")
		return "Failed to start kismet", 500

def stop_kismet():
	"""
	Stops kismet. For simplicity, we stop kismet using a kill -9 command.
	"""
	try:
		# Find the PID of the kismet process
		pid = subprocess.check_output("pgrep kismet", shell=True).split()[0]
		kill_output = subprocess.check_call(f"sudo kill -9 {pid.decode('utf-8')}", shell=True)
		if kill_output != 0:
			LOGGER.error("Failed to stop kismet.")
		LOGGER.info("Kismet stopped.")
	except subprocess.CalledProcessError as e:
		LOGGER.error(f"Failed to stop kismet: {e}")
	except Exception as e:
		LOGGER.error(f"An error occurred while stopping kismet: {e}")
	finally:
		# remove any .kismet-journal files from CONFIG['kismet']['file'] directory
		subprocess.call(f"rm {CONFIG['kismet']['file']}/*.kismet-journal", shell=True)

def get_kismet_status():
	"""
	Checks if kismet is running by trying to find its process.

	Returns:
		bool: True if kismet is running, False otherwise
	"""
	try:
		# Find the PID of the kismet process
		pid = subprocess.check_output("pgrep kismet", shell=True).split()
		if pid:
			return True
		return False
	except subprocess.CalledProcessError:
		# pgrep did not find any process
		return False
	except Exception as e:
		LOGGER.error(f"Failed to get kismet status: {e}")
		return False