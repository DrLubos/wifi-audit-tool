from distutils.core import setup
from setuptools import find_packages
import os

current_directory = os.path.dirname(os.path.abspath(__file__))

setup(
    name="Raspberry sniffer",
    packages=find_packages(),
    version="1.0",
    install_requires=["haversine >= 2.3.0", "psutil", "geopy"],
)