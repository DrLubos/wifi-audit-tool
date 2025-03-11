import sqlite3
from geopy.geocoders import Nominatim
import os
import datetime

reports_path = '/var/www/html/reports/maps'

if not os.path.isdir(reports_path):
    os.makedirs(reports_path, exist_ok=True)


def connect_to_database(database_name):
    connection = sqlite3.connect('kismet/' + database_name)
    return connection


def getDevices(reports_folder_path, database_name, device_ssid):
    global reports_path
    reports_path = reports_folder_path
    with connect_to_database(database_name) as conn:
        cursor = conn.cursor()
        if device_ssid is not None:
            # Select devices with the specified name
            cursor.execute("select * from ownTableOfWifiAP where SSID == ?", (device_ssid,))
        else:
            # Select all the devices
            cursor.execute("select * from ownTableOfWifiAP")
        result = cursor.fetchall()

        if len(result) == 0:
            print("There is no the database ")
            exit(0)

        for d in result:
            open_street_map_create_HTML_file(d[4], open_street_map_create_HTML_body(d[4], d[7]), database_name)
            # os.system('cp /home/pi/pythonProject/maps/{}.html /var/www/html/testmap/'.format(d[4]))
            # vytvorenieHTMLsubor(d[4], vytvorenieBody(d[4], d[7]))


def open_street_map_create_HTML_file(SSID, iframe, database_name):
    now = str(datetime.datetime.now()).replace(' ', '_')
    now = now.replace(':', '-')
    report_name = "%s_%s_%s" % (database_name, SSID, now)
    f = open(reports_path + "/{}.html".format(report_name), "w")
    f.write(iframe)
    f.close()


def open_street_map_create_HTML_body(SSID, suradnice):
    sur = suradnice.split(" ")
    latitude = sur[0]
    longitude = sur[1]
    ssid = SSID
    address = return_address(suradnice)
    issues = "none"

    body = '''<html>
<head>
    <title>AP Locations - Open Street Map</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
</head>
<body>
    <table>
        <tr><th>SSID:</th><td id="ssid"></td></tr>
        <tr><th>GPS Coordinates:</th><td id="cords"></td></tr>
        <tr><th>Address:</th><td id="address"></td></tr>
        <tr><th>Map:</th><td>
            <div id="mapid" style="width: 750px; height: 600px;"></div>
        </td></tr>
        <tr><th>Issues:</th><td id="issues"></td></tr>
    </table>

    <script>
        var latitude = {lat};
        var longitude = {lon};
        var ssid = "{ssid}";
        var address = "{address}";
        var issues = "{issues}";
        var gpsCords = latitude + ', ' + longitude;

        document.getElementById("ssid").innerHTML = ssid;
        document.getElementById("cords").innerHTML = gpsCords;
        document.getElementById("address").innerHTML = address;
        document.getElementById("issues").innerHTML = issues;

        var mymap = L.map('mapid').setView([latitude, longitude], 13);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }}).addTo(mymap);

        L.marker([latitude, longitude]).addTo(mymap)
            .bindPopup("<b>" + ssid + "</b><br>" + address)
            .openPopup();
    </script>
</body>
</html>'''.format(lat=latitude, lon=longitude, ssid=ssid, address=address, issues=issues)

    return body


# vratenie adresy na zaklade gps suradnic
def return_address(suradnice):
    geolocator = Nominatim(user_agent="Diplo")
    adresa = geolocator.reverse(suradnice)
    return adresa


def google_map_create_URL(suradnice):
    xy = suradnice.split(" ")
    link = "https://maps.google.com/maps?q="
    link += xy[0]
    link += ","
    link += xy[1]
    link += "&t=&z=19&ie=UTF8&iwloc=&output=embed"
    return link


def google_map_create_Iframe(link):
    iframe = ''' <div class="mapouter"><div class="gmap_canvas"><iframe width="600" height="500" id="gmap_canvas" src="{}" frameborder="0" scrolling="no" marginheight="0" marginwidth="0"></iframe><a href="https://123movies-to.org"></a><br><style>.mapouter'''.format(
        link)
    iframe += '''{position:relative;text-align:right;height:500px;width:600px;}</style><a href="https://www.embedgooglemap.net"></a><style>.gmap_canvas {overflow:hidden;background:none!important;height:500px;width:600px;}</style></div></div>'''
    return iframe


def create_table_content(coordinates):
    content = """
	<tr><th>Address:</th><td>{}</td></tr>
	<tr><th valign="top">map:</th><td>
	{}
	</td></tr>
""".format(return_address(coordinates), google_map_create_Iframe(google_map_create_URL(coordinates)))
    return content


def google_map_create_HTML_file(SSID, iframe):
    f = open(reports_path + "/%s.html" % (SSID), "w")
    f.write(iframe)
    f.close()

# getDevices()
