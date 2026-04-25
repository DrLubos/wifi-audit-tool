import os
import json
import pandas as pd
from datetime import datetime
from db_handler import DatabaseReader
from config import get_config
from logger import get_logger

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

def create_report(report_type="csv", db_file=None, device_id=None):
    if not report_type or not db_file:
        return {"error": "Please provide a report type and a db_file."}

    db_folder = CONFIG["kismet"]
    db_path = os.path.join(db_folder, db_file)
    if not os.path.exists(db_path):
        return {"error": "Database file does not exist."}

    try:
        db_reader = DatabaseReader(db_path)
        conn = db_reader.get_conn()
    except Exception as e:
        return {"error": f"Error opening database: {e}"}

    time_now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    reports_folder = "reports"
    if not os.path.exists(reports_folder):
        os.makedirs(reports_folder)
        
    report_filename = ""
    file_path = ""
    
    if report_type == "csv":
        try:
            df_devices = pd.read_sql_query("SELECT * FROM devices", conn)
            df_tests = pd.read_sql_query("SELECT * FROM tests", conn)
            csv_content = "Devices\n" + df_devices.to_csv(index=False) + "\nTests\n" + df_tests.to_csv(index=False)
            report_filename = f"report_csv_{time_now}.csv"
            file_path = os.path.join(reports_folder, report_filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(csv_content)
        except Exception as e:
            if conn:
                conn.close()
            return {"error": f"Error generating CSV report: {e}"}
    else:
        if conn:
            conn.close()
        return {"error": "Only 'csv' report type is currently supported in headless mode."}

    if conn:
        conn.close()

    return {"status": "Success", "file": file_path}