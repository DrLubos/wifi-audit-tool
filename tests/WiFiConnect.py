import os
import nmap
from pprint import pprint

from tests.TestResult import TestResult


def connection(name, password, interface):
	if password == "":
		pom = os.popen("nmcli d wifi connect {} ifname {}".format(name, interface))
	else:
		pom = os.popen("nmcli d wifi connect {} password {} ifname {}".format(name, password, interface))
	result = pom.read()
	return_code = pom.close()
	if "Error:" in result or return_code is not None:
		print("Couldn't connect to name: {}".format(name))
		return "",TestResult.OK
	else:
		print("Successfully connected to {} followed by running of Nmap port scan".format(name))
		return nmapScan(getDefaultGateway()), TestResult.CONNECTION_SUCCESS


def nmapScan(target):
    nmScan = nmap.PortScanner()
    nmScan.scan(target, '1-1024', arguments='-sV')
    print(nmScan.__dict__)

    for host in nmScan.all_hosts():
        print('Host : %s (%s)' % (host, nmScan[host].hostname()))
        print('State : %s' % nmScan[host].state())
        for proto in nmScan[host].all_protocols():
            print('----------')
            print('Protocol : %s' % proto)

            ports = nmScan[host][proto].keys()
            print("Vypisujem tu ",ports)
            nmapallresult=""

            for port in ports:
                vulnerability = ""
                vysledokNmap=('port : %s\tstate : %s' % (port, nmScan[host][proto][port]['state']))
                if "script" in nmScan[host][proto][port]:
                    vulnerability="Vulnerability: {} \n".format(nmScan[host][proto][port]['script']["fingerprint-strings"])
                nmapallresult += vysledokNmap+ "\n" +vulnerability
            print(nmapallresult)
    return nmapallresult


def getDefaultGateway():
    Gateway = os.popen("sudo ip r | grep default").read().split(" ")
    return Gateway[2]


# this connection is made to enable the user to connect to this device
if __name__ == "__main__":
    name = "Argo-2G"
    password = "Arginko913"
    interface = "wlan0"

#connection(name, password, interface)

