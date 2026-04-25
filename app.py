import sys
import os
import time
import signal
import threading

from config import get_config
from logger import get_logger

from audit_modules.audit import control_audit
from cracking_modules.cracking import stop as stop_cracking

CONFIG_INSTANCE = get_config()
CONFIG = CONFIG_INSTANCE.CONFIG
USERS = CONFIG_INSTANCE.USERS

LOGGER = get_logger(*CONFIG_INSTANCE.get_logger_settings())

def signal_handler(sig, frame):
    LOGGER.info("Shutdown signal received, stopping audit and cracking processes...")
    control_audit("stop")
    stop_cracking()
    sys.exit(0)

def main():
    LOGGER.info("Starting Wi-Fi Audit Headless Sensor...")
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Wait for interfaces or other background services to be ready
    time.sleep(2)
    
    # Optionally start Kismet and the audit loop immediately
    # Uncomment the following line to start auditing on boot:
    # control_audit("start", enable_cracking=False, handshake_capture_time=60, cracking_type="aircrack")
    
    LOGGER.info("Sensor is running in background. Ready for remote commands.")
    
    # Keep the main thread alive so background threads can run
    while True:
        time.sleep(5)

if __name__ == '__main__':
    main()
