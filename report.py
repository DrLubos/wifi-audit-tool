import sqlite3
import argparse
import csv
import datetime
from io import StringIO

import Visualization
import os

# For running the report.py program we can pass several arguments. The 'database' argument is obligatory.
# All the other are optional ones.
parser = argparse.ArgumentParser(description='Generator of reports. Reports can be generated as html and csv files.')
parser.add_argument('--csv', action='store_true', help='Generate a csv file with report instead of an html file.')
parser.add_argument('database', type=str, metavar='B', help='Name of database from which the report is generated.')
parser.add_argument('-device', type=str, metavar='D', help='Name of device for which the report is generated.')
parser.add_argument('--osm', action='store_true', help='Generate a report with openStreet Map instead of an Google Map.')
args = parser.parse_args()

if os.path.isdir('/var/www/html/test') == False:
    os.mkdir('/var/www/html/test')

# Connects to the database specified by the 'database_name' parameter in the kismet/ directory.
def connect_to_database(database_name):
    connection = sqlite3.connect('kismet/' + database_name)
    return connection


# Generates string with a report in the csv format.
def generate_csv_report(device, tests):
    (_, mac, manufacturer, ssid_channel, ssid, encryption, signal, coordinates) = device

    with StringIO() as s:
        writer = csv.writer(s)
        writer.writerow(['Device SSID', ssid])
        writer.writerow(['MAC address', mac])
        writer.writerow(['SSID channel', ssid_channel])
        writer.writerow(['Encryption', encryption])
        writer.writerow(['Signal strength', signal])
        writer.writerow(['Coordinates', coordinates])

        writer.writerow([])

        writer.writerow(['Issues:', 'Test type', 'Result description', 'Timestamp'])
        for test in tests:
            if test[3] == 0:
                continue
            writer.writerow(['', test[2].replace('_', ' '), test[4], test[5]])
        writer.writerow([])

        return s.getvalue()


# Generates string with a report in the html format.
def generate_html_report(device, tests):
    (_, mac, manufacturer, ssid_channel, ssid, encryption, signal, coordinates) = device

    tests_html = ""
    for test in tests:
        if test[4] == '':
            continue
        tests_html += "{}: {} &nbsp; &nbsp; {} <br>" \
            .format(test[2].replace('_', ' '), test[4], test[5])

    style = "{border: 1px solid black;}"
    data = '''
<!DOCTYPE html>
<html>
    <head>
        <style>
            table, th, td {}
        </style>
        <title>{} report</title>
    </head>
    <body>
        <h1>{}</h1>
        <table>
          <tr>
            <th>MAC address</th>
            <td>{}</td>
          </tr>
          <tr>
            <th>SSID channel</th>
            <td>{}</td>
          </tr>
          <tr>
            <th>Encryption</th>
            <td>{}</td>
          </tr>
          <tr>
            <th>Signal strength</th>
            <td>{}</td>
          </tr>
          <tr>
            <th>Coordinates</th>
            <td>{}</td>
          </tr>
          {}
          <tr>
            <th>Issues:</th>
            <td>
            {}
            </td>
            <br>
          </tr>
        </table>
        <br>
    </body>
</html>'''.format(style, ssid, ssid, mac, ssid_channel, encryption, signal, coordinates,
                  Visualization.create_table_content(coordinates), tests_html)
    return data


def colored_print(r,g,b,text):
    return "\033[38;2;{};{};{}m{} \033[38;2;255;255;255m".format(r, g, b, text)


if __name__ == '__main__':
    database_name = args.database
    device_ssid = args.device
    is_csv = args.csv
    is_osm = args.osm

    if is_csv and is_osm:
        print(colored_print(255,0,0, "Please set only csv parameter or osm parameter"))
        exit(0)

    with connect_to_database(database_name) as conn:
        cursor = conn.cursor()
        if device_ssid is not None:
            # Select devices with the specified name
            cursor.execute("select * from ownTableOfWifiAP where SSID == ?", (device_ssid, ))
        else:
            # Select all the devices
            cursor.execute("select * from ownTableOfWifiAP")
        result = cursor.fetchall()

        if len(result) == 0:
            print("There is no the device in the database %s" % (database_name,))
            exit(0)

        data = ''
        if is_osm :
            #generate_report = Visualization.newVorenieBody(device_ssid,pole[0][7])
            #generate_report = Visualization.getDevices(database_name)
            Visualization.getDevices(database_name,device_ssid)
            exit(0)
        elif is_csv:
            generate_report = generate_csv_report
        else:
            generate_report = generate_html_report
        #generate_report = generate_csv_report if is_csv else generate_html_report
        for d in result:
            device_id = d[0]

            # Get only the last test of each test type.
            tests = cursor.execute("select * from tests where Device = ? group by TestType HAVING max(TimeStamp)",
                                   (device_id,)).fetchall()

            data += generate_report(d, tests)

        now = str(datetime.datetime.now()).replace(' ', '_')
        now = now.replace(':', '-')
        extension = 'csv' if is_csv else 'html'
        if device_ssid is not None:
            report_name = "%s_%s_%s.%s" % (database_name, device_ssid, now, extension)
        else:
            report_name = "%s_%s.%s" % (database_name, now, extension)
        with open('reports/' + report_name, 'w', newline='') as report_file:
            report_file.write(data)
        #os.system('cp /home/pi/pythonProject/reports/{} /var/www/html/test/'.format(report_name))