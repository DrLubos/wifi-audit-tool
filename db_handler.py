import json
import sqlite3
import requests
from config import get_config
from logger import get_logger

class DatabaseHandler:
	"""
	Handles the connection to the Kismet API and the SQLite database.

	Attributes:
		api_session (requests.Session): Session with the Kismet API.
		conn (sqlite3.Connection): Connection to the SQLite database.
		cursor (sqlite3.Cursor): Cursor for the SQLite database.
	"""
	def __init__(self):
		self.config_instance = get_config()
		self.config = self.config_instance.CONFIG
		self.logger = get_logger(*self.config_instance.get_logger_settings())

		# Instance variables for API session and database connection.
		self.api_session = None
		self.conn = None
		self.cursor = None
		self.connect_to_kismet_api()
		self.init_db()

	def connect_to_kismet_api(self) -> None:
		"""
		Initialize a session with the Kismet API.
		"""
		self.api_session = requests.Session()
		login_url = (f'http://{self.config_instance.KISMET_USER}:'
					 f'{self.config_instance.KISMET_PASSWORD}@0.0.0.0:2501/session/check_session')
		response = self.api_session.get(login_url, timeout=10)
		if response.status_code == 200:
			self.logger.debug("Logged in successfully to Kismet API.")
			token = self.api_session.cookies.get('KISMET')
			self.logger.debug(f"Session cookies: {self.api_session.cookies.get_dict()}")
			self.api_session.cookies.set('KISMET', token, path='/')  # type: ignore
		else:
			self.logger.debug(f"Login failed with status code {response.status_code}")

	def init_db(self) -> None:
		"""
		Initialize the SQLite database with the Kismet logfile name.
		"""
		# Get the logfile data from the API (expects a list; take the first element).
		logfile_data = self.send_to_kismet_api("/logging/active.json")[0]
		file_name = logfile_data["kismet.logfile.path"]
		file_name = file_name[3:-7] # Remove ".//" from start and ".kismet" from the end.

		db_path = self.config["kismet"]["file"] + "/" + file_name + ".sqlite3"
		self.conn = sqlite3.connect(db_path)
		self.cursor = self.conn.cursor()

		# Create the 'devices' table.
		query_devices = (
			"CREATE TABLE IF NOT EXISTS devices ("
			"ID INTEGER PRIMARY KEY AUTOINCREMENT, "
			"ssid VARCHAR(255), "
			"mac_address VARCHAR(64), "
			"manufacturer VARCHAR(255), "
			"ssid_channel VARCHAR(255), "
			"encryption VARCHAR(64), "
			"signal_strength INTEGER, "
			"latitude_avg REAL, "
			"longitude_avg REAL)"
		)
		self.cursor.execute(query_devices)

		# Create the 'gps_coordinates' table.
		query_gps = (
			"CREATE TABLE IF NOT EXISTS gps_coordinates ("
			"ID INTEGER PRIMARY KEY AUTOINCREMENT, "
			"device_id INTEGER, "
			"latitude REAL, "
			"longitude REAL)"
		)
		self.cursor.execute(query_gps)
		
		# Create the 'tests' table.
		query_tests = (
			"CREATE TABLE IF NOT EXISTS tests ("
			"ID INTEGER PRIMARY KEY AUTOINCREMENT, "
			"device_id INTEGER, "
			"testType TEXT, "
			"testResult TEXT, "
			"description TEXT, "
			"timeStamp DATETIME DEFAULT CURRENT_TIMESTAMP)"
		)
		self.cursor.execute(query_tests)
		self.conn.commit()

	def send_to_kismet_api(self, api_request: str) -> dict:
		"""
		Send a GET request to the Kismet API and return the response as a dictionary.

		Parameters:
			api_request (str): API endpoint to request.

		Returns:
			dict: The response as a dictionary.
		"""
		if self.api_session is None:
			self.logger.error("Kismet API session not initialized.")
			return {}
		url = f"http://0.0.0.0:2501/{api_request}"
		response = self.api_session.get(url=url)
		if response.status_code == 200:
			json_data = json.loads(response.text)
			return json_data
		else:
			self.logger.error(
				f"API request failed with status code {response.status_code}")
			return {}

	def get_conn(self):
		"""
		Returns the active SQLite database connection.
		"""
		return self.conn

	def get_cursor(self):
		"""
		Returns the active SQLite cursor.
		"""
		return self.cursor
	
	def get_api_session(self):
		"""
		Returns the active Kismet API session.
		"""
		return self.api_session

_database_handler_instance = None

def get_database_handler() -> DatabaseHandler:
	"""
	Returns a singleton DatabaseHandler instance.
	
	Returns:
		DatabaseHandler: DatabaseHandler instance
	"""
	global _database_handler_instance
	if _database_handler_instance is None:
		_database_handler_instance = DatabaseHandler()
	return _database_handler_instance
