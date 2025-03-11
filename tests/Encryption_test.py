from tests.TestResult import TestResult


def perform_test(device):
    """
    :param device: A row from the table ownTableOfWifiAp
    :return: TestResult
    """

    #return TestResult.OK if "WPA" in device[5] else TestResult.WEP
    if "WPA" in device[5] :
        return TestResult.OK
    elif "Open" in device[5]:
        return TestResult.OPEN
    else:
        return TestResult.WEP
