import enum


class TestResult(enum.Enum):
    OK = 0
    AIRCRACK_NOT_PERFORMED = 1
    SAME_MAC = 3
    SAME_SSID = 4
    WEP = 5
    GPS = 2
    AIRCRACK_SUCCESS = 9
    OPEN = 10
    CONNECTION_SUCCESS = 11
