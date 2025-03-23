import threading
import time
from config import get_config
from logger import get_logger

from flask import Blueprint, jsonify, render_template, request
from audit_modules.audit_kismet import get_kismet_status, start_kismet, stop_kismet
from audit_modules.audit_parser import get_parser_status, parse, stop_parser
from audit_modules.audit_testing import get_testing_status, test, stop_testing

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')

audit_loop_running = False
audit_loop_thread = None

@audit_bp.route('/', methods=['POST', 'GET'])
def audit():
	global audit_loop_running, audit_loop_thread
	if request.method == 'POST':
		action = request.form.get('action')
		if action == "start":
			if not audit_loop_running:
				start_kismet()
				time.sleep(5) # wait for Kismet to start
				audit_loop_running = True
				audit_loop_thread = threading.Thread(target=audit_loop, daemon=True) 
				audit_loop_thread.start()
				LOGGER.info("Audit started.")
		elif action == "stop":
			stop_kismet()
			stop_parser()
			stop_testing()
			audit_loop_running = False
			audit_loop_thread = None
			LOGGER.info("Audit stopped.")
		return jsonify({"running": audit_loop_running})
	return render_template('audit.html')

@audit_bp.route('/status', methods=['GET'])
def get_audit_status():
	running, modules = get_audit_details()
	return jsonify({"running": running, "modules": modules})

def get_audit_details() -> tuple[bool, dict[str, bool]]:
	"""
	Get the status of all audit modules.

	Returns:
		tuple: (bool, dict[str, bool]) - running, modules
	"""
	kismet_running = get_kismet_status()
	parser_running = get_parser_status()
	testing_running = get_testing_status()
	running = any([kismet_running, parser_running, testing_running[0]])
	modules = {
		"kismet": kismet_running,
		"parser": parser_running,
		"testing": testing_running,
	}
	return running, modules

def audit_loop():
	"""
	Main audit loop. Runs the audit modules in a loop."
	"""
	global audit_loop_running
	while audit_loop_running:
		parse()
		time.sleep(0.1)
		test()
		time.sleep(CONFIG["main_sleep"])
