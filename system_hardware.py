import os
import subprocess
from typing import List, Dict


def get_wifi_interfaces() -> List[str]:
	"""Retrieve a list of Wi-Fi network interfaces available on the system.

	Returns:
		List[str]: A list of Wi-Fi interface names that start with "wlan".
	"""
	interfaces = os.listdir("/sys/class/net")
	wifi_interfaces = [iface for iface in interfaces if iface.startswith("wlan")]
	wifi_interfaces = [iface for iface in wifi_interfaces if iface.endswith("mon") == False]
	return wifi_interfaces


def get_mac_address(interface: str) -> str:
	"""Retrieve the MAC address of a network interface.

	Args:
		interface (str): The name of the network interface.

	Returns:
		str: The MAC address of the network interface.
	"""
	try:
		with open(f"/sys/class/net/{interface}/address", "r") as f:
			return f.read().strip()
	except Exception:
		return "Unknown"


def get_factory_name(interface: str) -> str:
	"""Retrieve the factory name of a network interface using udev.

	Args:
		interface (str): The name of the network interface.

	Returns:
		str: The factory name of the network interface.
	"""
	try:
		cmd = ["udevadm", "info", "-q", "property",
				"-p", f"/sys/class/net/{interface}"]
		output = subprocess.check_output(cmd, universal_newlines=True)
		cmd = ["udevadm", "info", "-q", "property",
				"-p", f"/sys/class/net/{interface}/device"]
		output += subprocess.check_output(cmd, universal_newlines=True)
		properties: Dict[str, str] = {}
		for line in output.splitlines():
				if "=" in line:
					key, value = line.split("=", 1)
					properties[key] = value

		# Prefer the full product name if available
		if "ID_MODEL_FROM_DATABASE" in properties:
			return properties["ID_MODEL_FROM_DATABASE"]
		else:
			vendor = properties.get("ID_VENDOR", "Unknown Vendor")
			model = properties.get("ID_MODEL", "Unknown Model")
			return f"{vendor} {model}"
	except Exception:
		raise Exception("get_factory_name() Failed to run command")


def get_interfaces_info() -> List[Dict[str, str]]:
	"""Retrieve information about all Wi-Fi network interfaces on the system.

	Returns:
		List[Dict[str, str]]: A list of dictionaries containing information about each Wi-Fi interface.
	"""
	results: List[Dict[str, str]] = []
	wifi_ifaces = get_wifi_interfaces()
	# remove wlan0 from wifi_ifaces
	if "wlan0" in wifi_ifaces:
		wifi_ifaces.remove("wlan0")
	wifi_ifaces.sort()
	for iface in wifi_ifaces:
		info = {
			"interface": iface,
			"name": get_factory_name(iface),
			"mac-address": get_mac_address(iface)
		}
		results.append(info)
	return results

"""
USAGE:

if __name__ == "__main__":

	import json
	interfaces_info = get_interfaces_info()
	print(json.dumps(interfaces_info, indent=4))
"""