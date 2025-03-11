import json
import os
import shutil

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
		self.load_config()

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

		self.CONFIG = config

	def save_config(self) -> None:
		"""Saves the current configuration to file."""
		config = self.CONFIG
		with open(self._config_file, "w") as f:
			json.dump(config, f, indent=4)


def get_config() -> Config:
	"""
	Returns a Config instance.
	
	Returns:
		Config: Config instance
	"""
	return Config()
