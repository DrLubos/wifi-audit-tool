#!/bin/bash
NEWLINE=`echo -e "\n"`

#reset getopts
OPTIND=1

if (( $EUID != 0 )); then
    echo "Please run as root"
    exit
fi

while getopts "ahdisp" opt; do
	case "$opt" in
		h)
	echo "
	USAGE: ./install.sh -argument

	Arguments:
	-h help
	-a Install Aircrack-ng and all Dependencies
	-d Install Kismets Dependencies
	-i Install Kismet. Remove ~/kismet, Git clone current release
	-s Create your custom kismet_site.conf
	-p Update your system "
	echo $NEWLINE
		;;
		i)
			echo "Removing previous Kismet git clone"
			cd ~
			rm -rf kismet
			git clone --recursive https://github.com/kismetwireless/kismet.git
			cd kismet/
			git pull
			echo "Next steps: configure, make and make suidinstall"
			PROCNUM=`nproc`
			echo "Hint: use make -j$PROCNUM to utilizes all available cores"
			echo "Configure time"
			./configure --disable-libwebsockets
			./configure
			echo "Make with -j$PROCNUM"
			make -j$PROCNUM
			echo "Make suidinstall"
			make suidinstall
			usermod -aG kismet $USER
			#logout
			groups
		;;
		d)
			apt-get update
			apt-get install build-essential git libwebsockets-dev pkg-config zlib1g-dev libnl-3-dev libnl-genl-3-dev libcap-dev libpcap-dev libnm-dev libdw-dev libsqlite3-dev libprotobuf-dev libprotobuf-c-dev protobuf-compiler protobuf-c-compiler libsensors4-dev libusb-1.0-0-dev python3 python3-setuptools python3-protobuf python3-requests python3-numpy python3-serial python3-usb python3-dev python3-websockets librtlsdr0 libubertooth-dev libbtbb-dev gpsd  -y
		;;
		s)
			DIR="/usr/local/etc/"
			DIR1="/etc/kismet/"
			if [sudo dmesg | grep tty | grep -c ACM0  ]; then
			DEVICE = "ACM0"
			echo $DEVICE
			else 
			DEVICE = "ACM1"
			fi
			if [ -d "$DIR1" ]; then
				echo "Creating kismet_site configuration"
				cd /etc/kismet
				touch kismet_site.conf
				chmod 644 kismet_site.conf
				echo "gps=serial:device=/dev/ttyACM0,reconnect=true" >> /etc/kismet/kismet_site.conf
				echo "Done"
				exit 1
			elif [ -d "$DIR" ]; then
				echo "Creating kismet_site configuration"
				cd /usr/local/etc/
				touch kismet_site.conf
				chmod 644 kismet_site.conf
				echo "gps=serial:device=/dev/ttyACM0,reconnect=true" >> /usr/local/etc/kismet_site.conf
				echo "Done"	
			fi
		;;
		p)
			echo "Updating you system"
			apt-get update
		;;
		a)
			echo "Installing Aircrack-ng tool with all dependencies"
			apt-get update
			apt-get install build-essential autoconf automake libtool pkg-config libnl-3-dev libnl-genl-3-dev libssl-dev ethtool shtool rfkill zlib1g-dev libpcap-dev libsqlite3-dev libpcre3-dev libhwloc-dev libcmocka-dev hostapd wpasupplicant tcpdump screen iw usbutils  -y
			git clone https://github.com/aircrack-ng/aircrack-ng
			cd aircrack-ng
			autoreconf -i
			./configure 
			make
			make install
			echo "Done"
		;;
	esac
done
