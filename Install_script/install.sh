#!/bin/bash

set -e  # Exit script on any error

NEWLINE=$'\n'

# Reset getopts
OPTIND=1

# Check for root privileges
if [[ $EUID -ne 0 ]]; then
    echo "Please run as root"
    exit 1
fi

# Check for arguments
if [ $# -eq 0 ]; then
    echo "No argument provided."
    $0 -h
    exit 1
fi

while getopts "haAkswf" opt; do
    case "$opt" in
        h)
            echo "
    Usage: sudo ./install.sh -argument
    Recommended: sudo ./install.sh -f

    Arguments:
    -h   Show this help message
    -a   Install Aircrack-ng from Debian repository
    -A   Install & compile Aircrack-ng from source (GitHub)
    -k   Install Kismet (removes ~/kismet, clones latest version)
    -s   Create custom kismet_site.conf for GPS support
    -w   Install WiFi Audit tool
    -f   Full installation (Aircrack-ng, Kismet, GPS support, WiFi Audit tool)
        "
            ;;

        k)
            echo "Installing required dependencies for Kismet..."
            apt update -q
            apt install -y librtlsdr-dev build-essential git libwebsockets-dev pkg-config \
                zlib1g-dev libnl-3-dev libnl-genl-3-dev libcap-dev libpcap-dev \
                libnm-dev libdw-dev libsqlite3-dev libprotobuf-dev libprotobuf-c-dev \
                protobuf-compiler protobuf-c-compiler libsensors4-dev libusb-1.0-0-dev \
                python3 python3-setuptools python3-protobuf python3-requests \
                python3-numpy python3-serial python3-usb python3-dev python3-websockets \
                librtlsdr0 libubertooth-dev libbtbb-dev libmosquitto-dev

            INSTALL_DIR="/opt/kismet"
            GITHUB_DIR="$INSTALL_DIR/kismet_github"
            INSTALL_DIR_COPY="$INSTALL_DIR/kismet_install"

            # Ensure /opt/kismet exists
            mkdir -p "$INSTALL_DIR"

            if [[ ! -d "$GITHUB_DIR" ]]; then
                echo "Cloning Kismet repository for the first time..."
                git clone --recursive https://github.com/kismetwireless/kismet.git "$GITHUB_DIR"
            else
                echo "Updating Kismet repository..."
                cd "$GITHUB_DIR"
                git pull
            fi

            # Remove old installation directory and create a fresh copy
            rm -rf "$INSTALL_DIR_COPY"
            cp -r "$GITHUB_DIR" "$INSTALL_DIR_COPY"

            cd "$INSTALL_DIR_COPY"


            echo "Configuring Kismet..."
            if ! ./configure; then
                echo "Error: Kismet configuration failed. Missing dependencies or incorrect environment."
                echo "Check the output above for missing packages and install them manually."
                exit 1
            fi

            TOTAL_TASKS=$(find . -name '*.c' -o -name '*.cpp' | wc -l)
            COUNTER=0

            PROCNUM=$(nproc --ignore=1)
            [[ $PROCNUM -gt 4 ]] && PROCNUM=4
            [[ $PROCNUM -lt 1 ]] && PROCNUM=1

            echo "Compiling Kismet with -j$PROCNUM --silent"
            echo "This may take a while..."
            echo "Ignore any warnings."
            echo "If errors occur, check the output above for missing packages."
            make -j"$PROCNUM" --silent

            echo "Installing Kismet (suid)..."
            make suidinstall
            echo "Adding user to Kismet group..."
            usermod -aG kismet $SUDO_USER

            echo "Kismet installation complete!"
            ;;

        s)
            echo "Configuring Kismet for GPS support..."

            # check if gpsd is running on system
            if pgrep -x "gpsd" > /dev/null; then
                echo "Error: gpsd is running on the system! Skipping for potentional missconfiguration."
                exit 1
            fi

            DIR="/usr/local/etc/"
            DIR1="/etc/kismet/"

            # Detect correct GPS device (ACM0 or ACM1)
            if dmesg | grep -q "ttyACM0"; then
                DEVICE="ACM0"
            else
                DEVICE="ACM1"
            fi

            CONFIG_FILE="kismet_site.conf"
            GPS_CONFIG="gps=serial:device=/dev/tty$DEVICE,reconnect=true"

            if [[ -d "$DIR1" ]]; then
                CONFIG_PATH="/etc/kismet/$CONFIG_FILE"
            elif [[ -d "$DIR" ]]; then
                CONFIG_PATH="/usr/local/etc/$CONFIG_FILE"
            else
                echo "Error: Kismet config directories not found!"
                exit 1
            fi

            echo "Creating $CONFIG_PATH with GPS support..."
            echo "$GPS_CONFIG" > "$CONFIG_PATH"
            chmod 644 "$CONFIG_PATH"

            echo "GPS configuration for Kismet complete!"
            ;;

        a)
            echo "Installing Aircrack-ng from Debian repository..."
            apt update -q
            apt install -y aircrack-ng
            echo "Aircrack-ng installation complete!"
            ;;

        A)
            echo "Installing Aircrack-ng from source..."

            apt update -q
            apt install -y build-essential autoconf automake libtool pkg-config libnl-3-dev libnl-genl-3-dev libssl-dev ethtool shtool rfkill zlib1g-dev libpcap-dev libsqlite3-dev libpcre2-dev libhwloc-dev libcmocka-dev hostapd wpasupplicant tcpdump screen iw usbutils expect

            echo "Cloning Aircrack-ng repository..."
            git clone https://github.com/aircrack-ng/aircrack-ng ~/aircrack-ng
            cd ~/aircrack-ng

            echo "Configuring Aircrack-ng..."
            autoreconf -i
            ./configure

            echo "Compiling Aircrack-ng..."
            make

            echo "Installing Aircrack-ng..."
            make install

            echo "Aircrack-ng installation complete!"
            ;;

        w)
            echo "Installing WiFi Audit tool..."
            apt update -q
            apt install -y python3 python3-pip python3-venv apache2

            rm /var/www/html/index.html
			echo "AddDefaultCharset utf-8" >> /etc/apache2/apache2.conf
			systemctl restart apache2
            
            # Allow user to specify directory or use default
            TOOL_DIR=${WIFI_AUDIT_DIR:-"$(pwd)"}
            read -p "Enter the WiFi Audit tool directory (default: $TOOL_DIR): " USER_INPUT
            TOOL_DIR=${USER_INPUT:-$TOOL_DIR}
            
            if [[ ! -d "$TOOL_DIR" ]]; then
                echo "Error: Directory $TOOL_DIR does not exist!"
                exit 1
            fi

            cd "$TOOL_DIR"
            if [[ ! -f "setup.py" ]]; then
                echo "Error: setup.py not found in $TOOL_DIR!"
                exit 1
            fi
            
            echo "Setting up Python virtual environment..."
            python3 -m venv venv
            source venv/bin/activate
            
            echo "Running setup.py in virtual environment..."
            pip install --upgrade pip
            pip install .
            
            deactivate
            echo "WiFi Audit tool installation complete!"
            ;;

        f)
            echo "Performing full installation: Kismet, Aircrack-ng, WiFi Audit tool"
            $0 -a  # Install Aircrack-ng from repository
            $0 -k  # Install Kismet
            $0 -w  # Install WiFi Audit tool
            echo "Full installation complete!"
            ;;

        *)
            echo "Invalid option."
            $0 -h
            exit 1
            ;;
    esac
done
