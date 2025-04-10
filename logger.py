from datetime import datetime
import logging
import os
from logging.handlers import RotatingFileHandler

levels = {
	"DEBUG": logging.DEBUG,
	"INFO": logging.INFO,
	"WARNING": logging.WARNING,
	"ERROR": logging.ERROR,
	"CRITICAL": logging.CRITICAL
}


class ColoredFormatter(logging.Formatter):
	COLORS = {
		logging.DEBUG: "\033[32m",		# Green
		logging.INFO: "\033[34m",		# Blue
		logging.WARNING: "\033[33m",  	# Yellow
		logging.ERROR: "\033[31m",		# Red
		logging.CRITICAL: "\033[1;31;47m"  # Red bold on white background
	}

	RESET = "\033[0m"

	def format(self, record: logging.LogRecord) -> str:
		"""
		Formats the log message with color.
		
		Parameters:
			record (LogRecord): Log record

		Returns:
			str: Formatted log message
		"""
		color = self.COLORS.get(record.levelno, self.RESET)
		message = logging.Formatter.format(self, record)
		return f"{color}{message}{self.RESET}"


class Logger:
	def __init__(self, name: str, log_file: str, file_level: int, console_level: int) -> None:
		"""
		Initializes the logger.
		
		Parameters:
			name (str): Name of the logger
			log_file (str): Path to the log file
			file_level (int): Log level for the file
			console_level (int): Log level for the console
		"""
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)  # Lower level to capture all messages
		self._log_file = log_file

		if not self.logger.handlers:
			if log_file:
				os.makedirs(os.path.dirname(log_file), exist_ok=True)

			# Rotating file handler with max 5MB per file and 3 backups
			file_handler = RotatingFileHandler(
				log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
			file_handler.setLevel(file_level)
			file_formatter = logging.Formatter(
				'%(asctime)s %(levelname)s - %(message)s')
			file_handler.setFormatter(file_formatter)

			# Console handler with colored output
			console_handler = logging.StreamHandler()
			console_handler.setLevel(console_level)
			console_formatter = ColoredFormatter(
				'%(asctime)s %(levelname)s - %(message)s')
			console_handler.setFormatter(console_formatter)

			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)

		# Disable propagation to avoid duplicate logs
		self.logger.propagate = False

	def debug(self, message: str) -> None:
		self.logger.debug(message)

	def info(self, message: str) -> None:
		self.logger.info(message)

	def warning(self, message: str) -> None:
		self.logger.warning(message)

	def error(self, message: str) -> None:
		self.logger.error(message)

	def critical(self, message: str) -> None:
		self.logger.critical(message)

	def exception(self, message: str) -> None:
		self.logger.exception(message)

	def get_file_path(self) -> str:
		"""
		Returns the path of the log file.
		
		Returns:
			str: Path to the log file
		"""
		return self._log_file


def get_logger(logger_name: str = "app", log_file: str = "logs/app.log", file_level: str = "WARNING", console_level: str = "DEBUG") -> Logger:
	"""
	Returns a logger instance.
	
	Parameters:
		logger_name (str): Name of the logger
		log_file (str): Path to the log file
		file_level (str): Log level for the file
		console_level (str): Log level for the console

	Returns:
		Logger: Logger instance
	"""
	return Logger(logger_name, log_file, file_level=levels[file_level], console_level=levels[console_level])
