import sys
import os
import binascii
import threading
import time
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_terminal import terminal_blueprint # Import the terminal blueprint /terminal

from config import get_config
from logger import get_logger
from system_hardware import get_interfaces_info

# Do not turn on terminal if you not gonna use it.
DISABLE_TERMINAL = False 

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG
USERS = CONFIG_INSTANCE.USERS

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

app = Flask(__name__)
app.template_folder = "web_ui/templates"
app.static_folder = "web_ui/static"
app.secret_key = "1b13068a8084656dfe156ecc8a26d3d05"

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # Set to True with HTTPS in production
app.permanent_session_lifetime = timedelta(days=7)

from audit_modules.audit import audit_bp
app.register_blueprint(audit_bp) # {{url}}}/audit
from report import report_bp
app.register_blueprint(report_bp) # {{url}}}/report
from cracking_modules.cracking import cracking_bp
app.register_blueprint(cracking_bp) # {{url}}}/cracking

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
    from audit_modules.audit import get_audit_details
    if get_audit_details()[0]: # [0] is audit running status
        flash("Configuration editing is disabled while audit is running.", category="error")
        return redirect(url_for('audit.audit'))
    from cracking_modules.cracking import get_crack_status
    if get_crack_status()['running']:
        flash("Configuration editing is disabled while cracking is running.", category="error")
        return redirect(url_for('cracking.cracking'))
    
    white_list_path = "./config/whiteList.txt"
    black_list_path = "./config/blackList.txt"
    white_black_list_path = "./config/whiteBlackList.txt"
    custom_password_list_path = "./config/customPasswordList.txt"

    if request.method == 'POST':
        # Update configuration with form values
        CONFIG['interface']['monitoring'] = request.form.get('interface_monitoring')
        CONFIG['interface']['cracking'] = request.form.get('interface_cracking')
        CONFIG['logger']['console_level'] = request.form.get('logger_console_level')
        CONFIG['logger']['file_level'] = request.form.get('logger_file_level')
        CONFIG['scan_type'] = int(request.form.get('scan_type') or 1)
        CONFIG['main_sleep'] = int(request.form.get('main_sleep') or 2)
        CONFIG['max_ap_distance'] = int(request.form.get('max_ap_distance') or 50)
        CONFIG['enable_terminal'] = request.form.get('enable_terminal') == 'on'

        CONFIG_INSTANCE.save_config()
        CONFIG_INSTANCE.load_config()

        white_list_text = request.form.get('white_list', '')
        black_list_text = request.form.get('black_list', '')
        white_black_list_text = request.form.get('white_black_list', '')
        custom_password_list_text = request.form.get('custom_password_list', '')

        try:
            with open(white_list_path, 'w') as f:
                f.write(white_list_text)
            with open(black_list_path, 'w') as f:
                f.write(black_list_text)
            with open(white_black_list_path, 'w') as f:
                f.write(white_black_list_text)
            with open(custom_password_list_path, 'w') as f:
                f.write(custom_password_list_text)
            LOGGER.info(
                f"{session.get('user', 'Unknown user')} - Configuration and list files saved.")
            flash("Configuration and list files saved successfully!")
        except Exception as e:
            LOGGER.error(f"Error writing list files: {e}")
            flash("Error writing one or more list files.", category="error")
        threading.Thread(target=restart_app).start()
        return redirect(url_for('home'))

    interfaces_list = get_interfaces_info()

    # Read in the current contents of each list file to display in <textarea>
    white_list_content = ""
    black_list_content = ""
    white_black_list_content = ""
    custom_password_list_content = ""

    try:
        with open(white_list_path, 'r') as f:
            white_list_content = f.read()
    except Exception as e:
        LOGGER.error(f"Error reading whiteList.txt: {e}")

    try:
        with open(black_list_path, 'r') as f:
            black_list_content = f.read()
    except Exception as e:
        LOGGER.error(f"Error reading blackList.txt: {e}")

    try:
        with open(white_black_list_path, 'r') as f:
            white_black_list_content = f.read()
    except Exception as e:
        LOGGER.error(f"Error reading whiteBlackList.txt: {e}")

    try:
        with open(custom_password_list_path, 'r') as f:
            custom_password_list_content = f.read()
    except Exception as e:
        LOGGER.error(f"Error reading customPasswordList.txt: {e}")
    # Render the config page, passing in config and the file contents
    return render_template(
        'config.html',
        config=CONFIG,
        wifi_interfaces=interfaces_list,
        white_list=white_list_content,
        black_list=black_list_content,
        white_black_list=white_black_list_content,
        custom_password_list=custom_password_list_content
    )

@app.route('/home')
def home():
    return render_template('home.html', config=CONFIG)

@app.route('/log')
def log():
    """Render the log page."""
    return render_template('log.html', log_content=log_data())

@app.route('/log_data')
def log_data():
    """Return the log file content as plain text (for AJAX updating)."""
    with open(LOGGER.get_file_path(), 'r') as log_file:
        log_content = log_file.read()
    return log_content

# ++++++++++++++++++++++KISMET++++++++++++++++++++++
@app.route('/kismet')
def kismet():
    """Redirect to kismet web server that is hosted on the port 2501."""
    next_url = request.args.get('next', 'None')
    if next_url == "None":
        next_url = url_for('home')
    return redirect(f"http://{next_url}:2501")

# ----------------------KISMET----------------------

def restart_app():
    time.sleep(1)
    try:
        LOGGER.info(f"{session.get('user', 'Unknown user')} - Restarting wifi_audit_tool.service")
        os.system("sudo systemctl restart wifi_audit_tool.service")

    except Exception as e:
        LOGGER.error(f"Error during self restart: {e}")

@app.route('/self_restart', methods=['GET', 'POST'])
def self_restart():
    # Restart application
    # If systemctl status wifi_audit_tool.service is running, restart the service.
    # Otherwise, restart the application.
    if request.method == 'POST':
        confirmation = request.form.get('confirmation')
        if confirmation == 'yes':
            threading.Thread(target=restart_app).start()
            return '', 204  # Return empty success response
        else:
            flash("Application restart canceled.", category="info")
            return redirect(url_for('home'))
    return render_template('confirm_self_restart.html')


@app.route('/system_restart', methods=['GET', 'POST'])
def system_restart():
    """Restart the system."""
    if request.method == 'POST':
        confirmation = request.form.get('confirmation')
        if confirmation == 'yes':
            LOGGER.info(f"{session.get('user', 'Unknown user')} - System restart.")
            os.system("sudo reboot")
            return redirect(url_for('home'))
        else:
            flash("System restart canceled.", category="info")
            return redirect(url_for('home'))
    return render_template('confirm_restart.html')

@app.route('/system_shutdown', methods=['GET', 'POST'])
def system_shutdown():
    """Shutdown the system."""
    if request.method == 'POST':
        confirmation = request.form.get('confirmation')
        if confirmation == 'yes':
            LOGGER.info(f"{session.get('user', 'Unknown user')} - System shutdown.")
            os.system("sudo shutdown now")
            return redirect(url_for('home'))
        else:
            flash("System shutdown canceled.", category="info")
            return redirect(url_for('home'))
    return render_template('confirm_shutdown.html')


@app.route('/clear_kismet')
def clear_kismet():
    # remove all files in CONFIG['kismet']['file'] folder
    try:
        for file in os.listdir(CONFIG["kismet"]):
            os.remove(os.path.join(CONFIG["kismet"], file))
        flash("Kismet files cleared successfully!", category="info")
    except Exception as e:
        LOGGER.error(f"Failed to clear kismet files: {e}")
        flash("Failed to clear kismet files.", category="error")
    return redirect(url_for('home'))

@app.route('/clear_reports')
def clear_reports():
    try:
        for file in os.listdir("reports"):
            os.remove(os.path.join("reports", file))
        flash("Reports cleared successfully!", category="info")
    except Exception as e:
        LOGGER.error(f"Failed to clear reports: {e}")
        flash("Failed to clear reports.", category="error")
    return redirect(url_for('home'))

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


def start_http_redirect():
    redirect_app = Flask("redirect_http")

    @redirect_app.route('/', defaults={'path': ''})
    @redirect_app.route('/<path:path>')
    def redirect_to_https(path):
        print(f"https://{request.host}{request.full_path}")
        return redirect(f"https://{request.host}{request.full_path}", code=301)

    redirect_app.run(host="0.0.0.0", port=80, debug=False, threaded=True, use_reloader=False)


if __name__ == '__main__':
    #print(app.url_map)
    # openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
    # Start HTTP redirect server in background
    threading.Thread(target=start_http_redirect, daemon=True).start()
    app.run(debug=False, use_reloader=False, host="0.0.0.0", port=443, ssl_context=("config/cert.pem", "config/key.pem"))
    #app.run(debug=True, host="0.0.0.0", port=443, ssl_context=("config/cert.pem", "config/key.pem"))
