import sqlite3
from geopy.geocoders import Nominatim
import os
import datetime

if os.path.isdir('/var/www/html/testmap') == False:
    os.mkdir('/var/www/html/testmap')


def connect_to_database(database_name):
    connection = sqlite3.connect('kismet/' + database_name)
    return connection


def getDevices(database_name, device_ssid):
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
    f = open("/home/kali/PycharmProjects/pythonProject/maps/{}.html".format(report_name), "w")
    f.write(iframe)
    f.close()


def open_street_map_create_HTML_body(SSID, suradnice):
    sur = suradnice.split(" ")
    longtitude = sur[0]
    latitude = sur[1]
    ssid = SSID
    address = return_address(suradnice)
    issues = "none"
    body = '''<html><head>
	<title>AP locations displyed on Open Street Map </title>

	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	
	<link rel="shortcut icon" type="image/x-icon" href="docs/images/favicon.ico">

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" integrity="sha512-xodZBNTC5n17Xt2atTPuE1HxjVMSvLVW9ocqUKLsCC5CXdbqCmblAshOMAS6/keqq/sMZMZ19scR4PsZChSR7A==" crossorigin="">
    <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js" integrity="sha512-XQoYMqMTK8LvdxXYG3nZ448hOEQiglfqkJs1NOQV44cWnUrBc8PkAOcXy20w0vlaXaVUearIOBhiXZ5V3ynxwA==" crossorigin=""></script>'''
    body += '''<script>
	/*Potrebné meniť iba tieto parametre*/
		var longtitude = {};
		var latitude = {};
		var ssid = '{}';
		var address = '{}';
		var issues = '{}';
		var gpsCords = {} + ' ' + {};		
    </script>'''.format(longtitude, latitude, ssid, address, issues, longtitude, latitude)
    body += '''</head><body>
	<table>
		<tr><th>SSID:</th><td id="ssid"></td></tr>
		<tr><th>GPS coords:</th><td id="cords"></td></tr>
		<tr><th>Address:</th><td id="address"></td></tr>
		<tr><th valign="top">Map:</th><td>
			<div id="mapid" style="width: 750px; height: 600px; position: relative;" class="leaflet-container leaflet-touch leaflet-fade-anim leaflet-grab leaflet-touch-drag leaflet-touch-zoom" tabindex="0"><div class="leaflet-pane leaflet-map-pane" style="transform: translate3d(0px, 0px, 0px);"><div class="leaflet-pane leaflet-tile-pane"><div class="leaflet-layer " style="z-index: 1; opacity: 1;"><div class="leaflet-tile-container leaflet-zoom-animated" style="z-index: 18; transform: translate3d(0px, 0px, 0px) scale(1);"><img alt="" role="presentation" src="https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/12/2046/1361?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw" class="leaflet-tile leaflet-tile-loaded" style="width: 512px; height: 512px; transform: translate3d(-200px, -347px, 0px); opacity: 1;"><img alt="" role="presentation" src="https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/12/2047/1361?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw" class="leaflet-tile leaflet-tile-loaded" style="width: 512px; height: 512px; transform: translate3d(312px, -347px, 0px); opacity: 1;"><img alt="" role="presentation" src="https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/12/2046/1362?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw" class="leaflet-tile leaflet-tile-loaded" style="width: 512px; height: 512px; transform: translate3d(-200px, 165px, 0px); opacity: 1;"><img alt="" role="presentation" src="https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/12/2047/1362?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw" class="leaflet-tile leaflet-tile-loaded" style="width: 512px; height: 512px; transform: translate3d(312px, 165px, 0px); opacity: 1;"></div></div></div><div class="leaflet-pane leaflet-shadow-pane"><img src="https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png" class="leaflet-marker-shadow leaflet-zoom-animated" style="margin-left: -12px; margin-top: -41px; width: 41px; height: 41px; transform: translate3d(300px, 247px, 0px);" alt=""></div><div class="leaflet-pane leaflet-overlay-pane"><svg pointer-events="none" class="leaflet-zoom-animated" width="720" height="480" style="transform: translate3d(-60px, -40px, 0px);" viewBox="-60 -40 720 480"><g><path class="leaflet-interactive" stroke="red" stroke-opacity="1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="#f03" fill-opacity="0.5" fill-rule="evenodd" d="M141.20355555554852,171.94704600190744a42,42 0 1,0 84,0 a42,42 0 1,0 -84,0 "></path><path class="leaflet-interactive" stroke="#3388ff" stroke-opacity="1" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="#3388ff" fill-opacity="0.2" fill-rule="evenodd" d="M358 163L474 219L550 153z"></path></g></svg></div><div class="leaflet-pane leaflet-marker-pane"><img src="https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png" class="leaflet-marker-icon leaflet-zoom-animated leaflet-interactive" style="margin-left: -12px; margin-top: -41px; width: 25px; height: 41px; transform: translate3d(300px, 247px, 0px); z-index: 247;" alt="" tabindex="0"></div><div class="leaflet-pane leaflet-tooltip-pane"></div><div class="leaflet-pane leaflet-popup-pane"><div class="leaflet-popup  leaflet-zoom-animated" style="opacity: 1; transform: translate3d(301px, 213px, 0px); bottom: -7px; left: -57px;"><div class="leaflet-popup-content-wrapper"><div class="leaflet-popup-content" style="width: 74px;"><b>Hello world!</b><br>I am a popup.</div></div><div class="leaflet-popup-tip-container"><div class="leaflet-popup-tip"></div></div><a class="leaflet-popup-close-button" href="#close">×</a></div></div><div class="leaflet-proxy leaflet-zoom-animated" style="transform: translate3d(1048050px, 697379px, 0px) scale(4096);"></div></div><div class="leaflet-control-container"><div class="leaflet-top leaflet-left"><div class="leaflet-control-zoom leaflet-bar leaflet-control"><a class="leaflet-control-zoom-in" href="#" title="Zoom in" role="button" aria-label="Zoom in">+</a><a class="leaflet-control-zoom-out" href="#" title="Zoom out" role="button" aria-label="Zoom out">−</a></div></div><div class="leaflet-top leaflet-right"></div><div class="leaflet-bottom leaflet-left"></div><div class="leaflet-bottom leaflet-right"><div class="leaflet-control-attribution leaflet-control"><a href="https://leafletjs.com" title="A JS library for interactive maps">Leaflet</a> | Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a></div></div></div></div>
		</td></tr>
		<tr><th>Issues:</th><td id="issues"></td></tr>
	</table>
	<script>
		document.getElementById("ssid").innerHTML = ssid;
		document.getElementById("cords").innerHTML = gpsCords;
		document.getElementById("address").innerHTML = address;
		document.getElementById("issues").innerHTML = issues;
		var mymap = L.map('mapid').setView([longtitude, latitude], 13);
	
		L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw', {
			maxZoom: 25,
			attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, ' +
				'Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
			id: 'mapbox/streets-v11',
			tileSize: 512,
			zoomOffset: -1
		}).addTo(mymap);
	
		L.marker([longtitude, latitude]).addTo(mymap);
	
	</script>
</body>
</html>'''

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
    f = open("/home/kali/PycharmProjects/pythonProject/maps/%s.html" % (SSID), "w")
    f.write(iframe)
    f.close()

# getDevices()
