import base64
import io
import os
import matplotlib.pyplot as plt
import json
from datetime import datetime
from db_handler import DatabaseReader
from config import get_config
from logger import get_logger

from flask import Blueprint, render_template, request, redirect, flash, send_from_directory, url_for

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

report_bp = Blueprint('report', __name__, url_prefix='/report')


@report_bp.route('/', methods=['GET'])
def report():
    # Check for avaiable reports
    # if folder "reports" exists, get all files in it and sort them by system time.
    # If folder does not exist skip this step.
    reports_folder = "reports"
    report_files = []
    if os.path.exists(reports_folder):
        report_files = [f for f in os.listdir(reports_folder) if f.endswith(".html")]
        report_files.sort(key=lambda x: os.path.getmtime(
            os.path.join(reports_folder, x)), reverse=True)

    # Get list of available database files from CONFIG["kismet"] folder
    db_folder = CONFIG["kismet"]
    if not os.path.exists(db_folder):
        flash("Database folder does not exist.", category="error")
        return redirect(url_for('report.report'))

    # Get all .sqlite3 files in the folder and sort them by system time.
    db_files = [f for f in os.listdir(db_folder) if f.endswith(".sqlite3")]
    db_files.sort(key=lambda x: os.path.getmtime(
        os.path.join(db_folder, x)), reverse=True)
    selected_db = request.args.get('db_file')
    if not selected_db:
        return render_template("report.html", db_files=db_files, step=1, reports=report_files)

    # Otherwise, open the selected database and get available devices.
    db_path = os.path.join(db_folder, selected_db)
    try:
        db_reader = DatabaseReader(db_path)
        cursor = db_reader.get_cursor()
        if not cursor:
            flash("Please try again", category="error")
            return redirect(url_for('report.report'))
        cursor.execute("SELECT ID, ssid, mac_address FROM devices ORDER BY ssid")
        devices = cursor.fetchall()
    except Exception as e:
        flash(f"Error opening database: {e}", category="error")
        devices = []
    return render_template("report.html", db_files=db_files, step=2, selected_db=selected_db, devices=devices, reports=report_files)


@report_bp.route('/help', methods=['GET'])
def report_help():
    return render_template("report_help.html")


@report_bp.route('/create_report', methods=['POST'])
def create_report():
    report_type = request.form.get('report_type')
    db_file = request.form.get('db_file')
    device_id = request.form.get('device_id')

    if not report_type or not db_file or not device_id:
        flash("Please select a report type and a device.", category="error")
        return redirect(url_for('report.report'))

    db_folder = CONFIG["kismet"]
    db_path = os.path.join(db_folder, db_file)
    if not os.path.exists(db_path):
        flash("Database file does not exist.", category="error")
        return redirect(url_for('report.report'))

    try:
        db_reader = DatabaseReader(db_path)
        conn = db_reader.get_conn()
        cursor = db_reader.get_cursor()
    except Exception as e:
        flash(f"Error opening database: {e}", category="error")
        return redirect(url_for('report.report'))

    if not cursor:
        flash("Please try again", category="error")
        return redirect(url_for('report.report'))
    device_name = ""
    report = ""

    time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    if report_type == "one":
        cursor.execute("SELECT * FROM devices WHERE ID = ?", (device_id,))
        device = cursor.fetchone()
        if not device:
            flash("Device not found.", category="error")
            return redirect(url_for('report.report'))
        # get tests from device
        cursor.execute("SELECT * FROM tests WHERE device_id = ?", (device_id,))
        tests = cursor.fetchall()
        cursor.execute(
            "SELECT * FROM cracked_passwords WHERE device_id = ?", (device[0],))
        cracked_passwords = cursor.fetchall()
        device_name = device[1]
        if not device:
            flash("Device not found.", category="error")
            return redirect(url_for('report.report'))
        # ["48", "36", "40", "44"]
        # Sort channels ascendingly
        ssid_channels = json.loads(device[4])
        ssid_channels = sorted(ssid_channels, key=int)
        ssid_channels = ", ".join(ssid_channels)

        device_info = {
            "device": device,
            "freq_chart": create_frequency_map(device[5]),
            "ssid_channels": ssid_channels,
            "tests": build_tests_string(tests, cursor, cracked_passwords),
        }
        report_filename = f"{device_name}_{time_now}.html"
        report = render_template("report_type_one.html", data=device_info, file_name=report_filename)

    elif report_type == "separate":
        cursor.execute("SELECT * FROM devices ORDER BY ssid")
        devices = cursor.fetchall()
        device_info_list = []
        for device in devices:
            cursor.execute("SELECT * FROM tests WHERE device_id = ?", (device[0],))
            tests = cursor.fetchall()
            cursor.execute(
                "SELECT * FROM cracked_passwords WHERE device_id = ?", (device[0],))
            cracked_passwords = cursor.fetchall()
            ssid_channels = json.loads(device[4])
            ssid_channels = sorted(ssid_channels, key=int)
            ssid_channels = ", ".join(ssid_channels)
            info = {
                "device": device,
                "freq_chart": create_frequency_map(device[5]),
                "ssid_channels": ssid_channels,
                "tests": build_tests_string(tests, cursor, cracked_passwords)
            }
            device_info_list.append(info)

        report_filename = f"{report_type}_{time_now}.html"
        report = render_template(
            "report_type_separate.html", devices=device_info_list, file_name=report_filename)
    elif report_type == "combined":
        cursor.execute("SELECT * FROM devices ORDER BY ssid")
        devices = cursor.fetchall()
        device_info_list = []
        for device in devices:
            cursor.execute("SELECT * FROM tests WHERE device_id = ?", (device[0],))
            tests = cursor.fetchall()
            cursor.execute("SELECT * FROM cracked_passwords WHERE device_id = ?", (device[0],))
            cracked_passwords = cursor.fetchall()
            ssid_channels = json.loads(device[4])
            ssid_channels = sorted(ssid_channels, key=int)
            ssid_channels = ", ".join(ssid_channels)
            info = {
                "device": device,
                "freq_chart": create_frequency_map(device[5]),
                "ssid_channels": ssid_channels,
                "tests": build_tests_string(tests, cursor, cracked_passwords)
            }
            device_info_list.append(info)
            
        report_filename = f"{report_type}_{time_now}.html"
        report = render_template(
            "report_type_combined.html", devices=device_info_list, file_name=report_filename)
        
    elif report_type == "csv":
        import pandas as pd
        df_devices = pd.read_sql_query("SELECT * FROM devices", conn)
        df_tests = pd.read_sql_query("SELECT * FROM tests", conn)
        csv_content = "Devices\n" + df_devices.to_csv(index=False) + "\nTests\n" + df_tests.to_csv(index=False)
        report_filename = f"{report_type}_{time_now}.html"
        report = render_template(
            "report_csv.html", csv_content=csv_content, file_name=report_filename)
        
    else:
        flash("Invalid report type.", category="error")
        return redirect(url_for('report.report'))

    # Save the report to a file in the reports folder
    reports_folder = "reports"
    file_path = os.path.join(reports_folder, report_filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    if conn is not None:
        conn.close()

    return redirect(url_for('report.get_report', filename=report_filename))


def create_frequency_map(freq_map):
    freq_map = json.loads(freq_map)
    x = sorted(freq_map.keys(), key=int)
    y = [freq_map[i] for i in x]
    if len(x) == 0 or len(y) == 0:
        return None
    if len(x) < 4:
        figsize_x = len(x) + 1
    else:
        figsize_x = 6
    plt.figure(figsize=(figsize_x, 3))
    plt.bar(x, y)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Number of Packets")
    plt.title("Frequency Map")
    plt.xticks(rotation=45)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()  # Close the figure to free memory.
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def build_tests_string(tests, cursor, cracked_passwords):
    """
    Lists all tests from db, builds string that will explain the test and its result.
    Parameters:
        tests: List of tests from db
        cursor: Cursor to the database
        cracked_passwords: List of cracked passwords from db
    Returns:
        str: String with all tests and their results
    """
    from audit_modules.audit_testing import TestType, TestResult
    return_string = ""
    for test in tests:
        test_type = TestType[test[2]].name
        test_result = TestResult[test[3]].value
        tested_with_device_id = test[4]
        time_stamp = test[5]
        if tested_with_device_id is not None:
            cursor.execute("SELECT ssid, mac_address FROM devices WHERE ID = ?", (tested_with_device_id,))
            other_device = cursor.fetchone()
            if other_device:
                other_device_name = f"{other_device[0]} ({other_device[1]})"
            else:
                other_device_name = "Unknown device"
        else:
            other_device_name = ""
        return_string += f"Time: {time_stamp} - Type: {test_type} - Result: {test_result}{other_device_name}<br>"
    if len(cracked_passwords) == 0:
        return return_string
    for cracked_password in cracked_passwords:
        id, device_id, password, cracked_at = cracked_password
        return_string += f"Time: {cracked_at} - Cracked password: <strong>{password}</strong><br>"
    return return_string

@report_bp.route('/reports/<path:filename>')
def get_report(filename):
    """
    Serve the report files from the reports folder.
    Parameters:
        filename: Name of the report file to serve
    Returns:
        str: HTML report as a string (rendered_template)
    """
    reports_folder = "reports"
    return send_from_directory(reports_folder, filename)