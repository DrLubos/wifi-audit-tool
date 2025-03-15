import os
import binascii
import threading
import time
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_terminal import terminal_blueprint

from config import get_config
from logger import get_logger
from system_hardware import get_interfaces_info
from dotenv import load_dotenv

if os.path.exists('.env'):
	load_dotenv('.env')
else:
	print("Warning: .env file not found. No user authentication data loaded.")

# Expected format in .env: USERS=admin:password123,user:pass456
users_env = os.getenv("USERS", "")
USERS = {}
if users_env:
	for user_entry in users_env.split(","):
		try:
			username, password = user_entry.split(":")
			USERS[username.strip()] = password.strip()
		except Exception as e:
			print(f"Error parsing user entry '{user_entry}': {e}")

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(
	CONFIG["logger"]["name"],
	CONFIG["logger"]["file"],
	CONFIG["logger"]["file_level"],
	CONFIG["logger"]["console_level"]
)

app = Flask(__name__)
app.secret_key = binascii.hexlify(os.urandom(24)).decode()

# Secure session cookie settings
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True with HTTPS in production
app.permanent_session_lifetime = timedelta(days=7)

# Enforce login on all routes except for login and static assets.
@app.before_request
def require_login():
	if request.endpoint not in ['login', 'static']:
		if 'user' not in session:
			return redirect(url_for('login', next=request.url))
		
@app.context_processor
def inject_user():
	return dict(logged_in_user=session.get('user'))

@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.endpoint in ['login', 'static']:
		if 'user' in session:
			return redirect(url_for('home'))
	if request.method == 'POST':
		username = request.form.get('username')
		password = request.form.get('password')
		remember = request.form.get('remember') == 'on'
		
		if username in USERS and USERS[username] == password:
			session['user'] = username
			session.permanent = remember  # If "Remember Me" is checked, the session becomes permanent.
			flash("Logged in successfully.")
			next_url = request.form.get('next')
			if next_url == "None":
				next_url = url_for('home')
			else:
				next_url = next_url or url_for('home')
			LOGGER.info(f"{username} - Logged in.")
			return redirect(next_url)
		else:
			flash("Invalid username or password.", category="error")
	return render_template('login.html')

@app.route('/logout')
def logout():
	session.pop('user', None)
	flash("Logged out successfully.")
	return redirect(url_for('login'))

@app.route('/')
def index():
	return redirect(url_for('home'))

@app.route('/config', methods=['GET', 'POST'])
def config():
	if request.method == 'POST':
		# Update configuration with form values
		CONFIG['interface']['monitoring'] = request.form.get('interface_monitoring')
		CONFIG['interface']['scanning'] = request.form.get('interface_scanning')
		CONFIG['logger']['name'] = request.form.get('logger_name')
		CONFIG['logger']['file'] = request.form.get('logger_file')
		CONFIG['logger']['console_level'] = request.form.get('logger_console_level')
		CONFIG['logger']['file_level'] = request.form.get('logger_file_level')
		CONFIG['kismet']['file'] = request.form.get('kismet_file')
		CONFIG['scan_type'] = int(request.form.get('scan_type') or 1)
		CONFIG['recheck'] = int(request.form.get('recheck') or 600)
		CONFIG['main_sleep'] = int(request.form.get('main_sleep') or 2)
		CONFIG['max_ap_distance'] = int(request.form.get('max_ap_distance') or 50)
		CONFIG['errors_threshold'] = int(request.form.get('errors_threshold') or 5)
		CONFIG['enable_terminal'] = request.form.get('enable_terminal') == 'on'

		CONFIG_INSTANCE.save_config()
		LOGGER.info(f"{session.get('user', 'Unknown user')} - Configuration saved.")
		flash("Configuration saved successfully!")
		return redirect(url_for('home'))

	interfaces_list = get_interfaces_info()
	return render_template('config.html', config=CONFIG, wifi_interfaces=interfaces_list)

@app.route('/home')
def home():
	return render_template('home.html', config=CONFIG)

@app.route('/audit')
def audit():
	return render_template('temp.html')

@app.route('/report')
def report():
	return render_template('temp.html')

@app.route('/log')
def log():
	"""Render the log page."""
	with open(CONFIG['logger']['file'], 'r') as log_file:
		log_content = log_file.read()
	return render_template('log.html', log_content=log_content)

@app.route('/log_data')
def log_data():
	"""Return the log file content as plain text (for AJAX updating)."""
	with open(CONFIG['logger']['file'], 'r') as log_file:
		log_content = log_file.read()
	return log_content

@app.route('/ping')
def ping():
	"""
	Respond to a ping request.

	"""
	try:
		return 'pong', 200
	except Exception as e:
		LOGGER.error(f"Error pinging: {e}")
		return "An error occurred", 500

@terminal_blueprint.before_request
def before_terminal_request():
	DISABLE_TERMINAL = True
	if DISABLE_TERMINAL:
		flash("Terminal is disabled by script.", category="error")
		return redirect(url_for('home'))
	if not CONFIG["enable_terminal"]:
		flash("Terminal is disabled in the configuration.", category="error")
		return redirect(url_for('home'))
		
app.register_blueprint(terminal_blueprint, url_prefix='/terminal')


def main():
	while True:
		time.sleep(5)
		msg = binascii.hexlify(os.urandom(5)).decode()
		LOGGER.debug(msg)
		time.sleep(5)

if __name__ == '__main__':
	#main_thread = threading.Thread(target=main)
	#main_thread.start()
	app.run(debug=True, host="0.0.0.0")

