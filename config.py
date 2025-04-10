import json
import os
import shutil
from dotenv import load_dotenv

"""
Usage:
	from config import get_config

	CONFIG_INSTANCE = get_config()
	CONFIG = CONFIG_INSTANCE.CONFIG
	CONFIG["key"] = "value"
"""


class Config:
	def __init__(self) -> None:
		"""Initializes the configuration."""
		self._config_file = "config/config.json"
		self._template_file = "config/config.init.json"
		self.VARIABLES = {}
		self.CONFIG = {}
		self.load_config()
		self.parse_env()

	def load_config(self) -> None:
		"""Loads configuration from file. If it doesn't exist, copies from template."""
		directory = os.path.dirname(self._config_file)
		if directory and not os.path.exists(directory):
			os.makedirs(directory)

		if not os.path.exists(self._config_file):
			if not os.path.exists(self._template_file):
				raise FileNotFoundError(f"Template file {self._template_file} not found!")
			shutil.copy(self._template_file, self._config_file)

		with open(self._config_file, "r") as f:
			config = json.load(f)

		config["kismet"] = "kismet"
		self.CONFIG.clear()
		self.CONFIG.update(config)

	def save_config(self) -> None:
		"""Saves the current configuration to file."""
		config = self.CONFIG
		with open(self._config_file, "w") as f:
			json.dump(config, f, indent=4)

	def parse_env(self) -> None:
		"""Parses environment variables and updates the configuration."""
		# Expected format in .env: USERS=admin:password123,user:pass456
		if os.path.exists('.env'):
			load_dotenv('.env')
		else:
			print("Warning: .env file not found. No user authentication data loaded.")
		users_env = os.getenv("USERS", "")
		self.USERS = {}
		if users_env:
			for user_entry in users_env.split(","):
				try:
					username, password = user_entry.split(":")
					self.USERS[username.strip()] = password.strip()
				except Exception as e:
					print(f"Error parsing user entry '{user_entry}': {e}")
		self.KISMET_USER = os.getenv("KISMET_USER", "")
		self.KISMET_PASSWORD = os.getenv("KISMET_PASS", "")

	def get_logger_settings(self) -> tuple:
		"""
		Returns the logger settings.
		
		Returns:
			tuple: Logger settings name, log file path, file level, console level
		"""
		return (
			"app",
			"logs/app.log",
			self.CONFIG["logger"]["file_level"],
			self.CONFIG["logger"]["console_level"]
		)


_config_instance = None

def get_config() -> Config:
	"""
	Returns a singleton Config instance.
	
	Returns:
		Config: Config instance
	"""
	global _config_instance
	if _config_instance is None:
		_config_instance = Config()
	return _config_instance
