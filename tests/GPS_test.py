from tests.TestResult import TestResult
import scan
import haversine
from haversine import Unit


def perform_test(device1: str, device2: str):
    """
    :param device1: string "latitude longitude"
    :param device2: string "latitude longitude"
    :return: TestResult value. TestResult.Ok in case of passing the test and TestResult.GPS in case of failing.
    """
    d1 = device1.split(' ')
    d2 = device2.split(' ')
    lat1, lon1 = float(d1[0]), float(d1[1])
    lat2, lon2 = float(d2[0]), float(d2[1])
    max_acceptable_dist = scan.SETUP[4]
    dist = find_difference(lat1, lon1, lat2, lon2)

    if dist > max_acceptable_dist:
        return TestResult.GPS

    return TestResult.OK


def find_difference(lat1, lon1, lat2, lon2):
    return haversine.haversine((lat1, lon1), (lat2, lon2), unit=Unit.METERS)


