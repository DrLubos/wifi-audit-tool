import os
import glob

from config import get_config
from logger import get_logger

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(CONFIG["logger"]["name"])

allowed_file_extensions = ["kismet", ".sqlite"]


class FileHandler:
	@staticmethod
	def get_last_file(file_type: str, file_name: str = "*") -> str:
		"""
		Returns the last file in the directory based on given extension.
		
		Parameters:
			file_type (str): Extension of the file
			file_name (str): Name of the file

		Returns:
			str: Path to the last file
		"""
		if file_type not in allowed_file_extensions:
			message = f"File type {file_type} is not allowed. Allowed types are {allowed_file_extensions}"
			LOGGER.critical(message)
			return ""

		file_folder = CONFIG["kismet"]["file"]
		file = glob.glob(os.path.join(file_folder, f"{file_name}.{file_type}"))
		if not file:
			message = f"No {file_type} files found in {file_folder}"
			LOGGER.critical(message)
			return ""

		return max(file, key=os.path.getctime)
