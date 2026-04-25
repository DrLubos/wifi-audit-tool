#!/usr/bin/env bash
set -e
trap 'echo "Error on line $LINENO"; exit 1' ERR

# — ensure root
if [[ $EUID -ne 0 ]]; then
    echo "Please run with sudo"
    exit 1
fi

# — check ethernet link
if ! ip link show eth0 | grep -qq "state UP"; then
    echo "Ethernet (eth0) is not up. Please connect via Ethernet." >&2
    exit 1
fi

# — initialize flags
FULL=false
GPSD=false
AIRCRACK=false
KISMET=false
APP=false

usage() {
    cat <<EOF
Usage: $0 [--full|-f] [--gpsd|-g] [--aircrack|-a] [--kismet|-k] [--app|-p]
  --full,      -f   full install (all modules)
  --gpsd,      -g   gpsd
  --aircrack,  -a   aircrack-ng
  --kismet,    -k   kismet
  --app,       -p   wifi_audit_tool application
  --help,      -h   show this help message
EOF
    exit 1
}

# — parse short and long options via getopt
PARSED=$(getopt --options fgakph --long full,gpsd,aircrack,kismet,app,help --name "$0" -- "$@")
if [[ $? -ne 0 ]]; then
    usage
fi
eval set -- "$PARSED"

while true; do
    case "$1" in
        -f|--full)
            FULL=true; shift ;;
        -g|--gpsd)
            GPSD=true; shift ;;
        -a|--aircrack)
            AIRCRACK=true; shift ;;
        -k|--kismet)
            KISMET=true; shift ;;
        -p|--app)
            APP=true; shift ;;
        --)
            shift; break ;;
        -h|--help)
            usage ;;
        *)
            usage ;;
    esac
done

if $FULL; then
    GPSD=true
    AIRCRACK=true
    KISMET=true
    APP=true
fi

if ! $GPSD && ! $AIRCRACK && ! $KISMET && ! $APP; then
    usage
fi

# — prompt for credentials
if $KISMET || $FULL || $APP; then
    read -p "Enter username for app user: " USER_GLOBAL
    read -s -p "Enter password for app user: " PASS_GLOBAL
    echo
fi


echo "Updating package lists..."
apt update -y -qq
apt upgrade -y -qq
apt autoremove -y -qq

# —— MODULE: GPSD
if $GPSD; then
    echo "Installing GPSD..."
    apt install -y -qq gpsd

    # auto-detect device
    if [[ -e /dev/ttyACM0 ]]; then
        DEV="/dev/ttyACM0"
    elif [[ -e /dev/ttyACM1 ]]; then
        DEV="/dev/ttyACM1"
    else
        echo "No GPS device (/dev/ttyACM0 or /dev/ttyACM1) found." >&2
        exit 1
    fi

    cat > /etc/default/gpsd <<EOF
DEVICES="$DEV"
GPSD_OPTIONS="-n -G -b"
USBAUTO="true"
EOF

    echo "GPSD configured for $DEV"
fi

# —— MODULE: Aircrack-ng
 if $AIRCRACK; then
    echo "Installing aircrack-ng..."
    apt install -qq -y aircrack-ng
    echo "Downloading rockyou.txt wordlist (zip)..."
    apt install -qq -y unzip
    mkdir -p /usr/share/wordlists
    if [[ ! -f /usr/share/wordlists/rockyou.txt ]]; then
        wget -qO /tmp/rockyou.zip https://github.com/kkrypt0nn/wordlists/raw/refs/heads/main/wordlists/famous/rockyou.zip
        unzip -p /tmp/rockyou.zip rockyou.txt > /usr/share/wordlists/rockyou.txt
        rm /tmp/rockyou.zip
    fi
 fi

# —— MODULE: Kismet
if $KISMET; then
    echo "Installing Kismet dependencies..."
    apt install -y -qq build-essential git libwebsockets-dev pkg-config \
        zlib1g-dev libnl-3-dev libnl-genl-3-dev libcap-dev libpcap-dev \
        libnm-dev libdw-dev libsqlite3-dev libprotobuf-dev libprotobuf-c-dev \
        protobuf-compiler protobuf-c-compiler libsensors4-dev libusb-1.0-0-dev \
        python3 python3-setuptools python3-protobuf python3-requests \
        python3-numpy python3-serial python3-usb python3-dev python3-websockets \
        librtlsdr0 libubertooth-dev libbtbb-dev libmosquitto-dev librtlsdr-dev

    BASE="/opt/kismet"
    GITDIR="$BASE/kismet_github"
    INSTDIR="$BASE/kismet_install"
    mkdir -p "$BASE"

    if [[ ! -d "$GITDIR" ]]; then
        echo "Cloning Kismet..."
        git clone --recursive https://github.com/kismetwireless/kismet.git "$GITDIR"
    else
        echo "Updating Kismet repo..."
        cd "$GITDIR" && git pull
    fi

    rm -rf "$INSTDIR"
    cp -r "$GITDIR" "$INSTDIR"
    cd "$INSTDIR"

    echo "Configuring Kismet..."
    ./configure

    # compile with up to 4 cores
    PROC=$(nproc --ignore=1)
    (( PROC<1 )) && PROC=1
    (( PROC>4 )) && PROC=4
    echo "Building Kismet (-j$PROC)"
    make -j"$PROC" --silent

    echo "Installing Kismet (suid)..."
    make suidinstall

    usermod -aG kismet "${SUDO_USER:-$USER}"

    # configure confs if gpsd is running
    if pgrep -x gpsd &>/dev/null; then
        echo "Writing Kismet GPS site config..."
        cat > /usr/local/etc/kismet_site.conf <<EOF
gps=gpsd:host=localhost,port=2947
EOF
        chmod 644 /usr/local/etc/kismet_site.conf

        echo "Appending Kismet logging prefs..."
        {
            echo "kis_log_data_packets=false"
            echo "kis_log_duplicate_packets=false"
        } >> /usr/local/etc/kismet_logging.conf

        echo "Appending Kismet HTTPd credentials..."
        {
            echo "httpd_username=$USER_GLOBAL"
            echo "httpd_password=$PASS_GLOBAL"
        } >> /usr/local/etc/kismet_httpd.conf
    else
        echo "gpsd not running; skipping Kismet GPS config"
    fi
fi

# —— MODULE: wifi_audit_tool Application
if $APP; then
    # assume script is run from inside app directory
    APP_DIR="$(cd "$(dirname "$0")" && pwd)"

    # preinstall Python and venv
    echo "Installing Python prerequisites..."
    apt install -y python3 python3-pip python3-venv

    # set up virtual environment
    echo "Creating virtual environment..."
    python3 -m venv "$APP_DIR/venv"
    "$APP_DIR/venv/bin/pip" install --upgrade pip

    # install required Python packages
    echo "Installing Python packages..."
    "$APP_DIR/venv/bin/pip" install aiohttp certifi colorama cryptography docutils geographiclib \
        geopy haversine IPython jinja2 keyring numba numpy pandas Pillow psutil pytest python-nmap \
        pytz redis requests requests-oauthlib scipy setuptools tqdm urllib3 wheel wmi yarl python-dotenv \
       

    # write .env
    cat > "$APP_DIR/.env" <<EOF
USERS=$USER_GLOBAL:$PASS_GLOBAL
KISMET_USER=$USER_GLOBAL
KISMET_PASS=$PASS_GLOBAL
EOF

    # install and enable systemd service
    cat > /etc/systemd/system/wifi_audit_tool.service <<EOF
[Unit]
Description=Wifi Audit Tool Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python app.py
ExecStop=/bin/kill -SIGINT \$MAINPID
Restart=on-failure
TimeoutStopSec=10
StandardOutput=append:/var/log/wifi_audit_tool.log
StandardError=append:/var/log/wifi_audit_tool.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable --now wifi_audit_tool.service
fi

# change ownership of app directory
chown -R "$SUDO_USER:$SUDO_USER" "$APP_DIR"
chmod -R 755 "$APP_DIR"

# update system - some packages may missing after installation
echo "Updating system packages..."
apt update -y -qq
apt upgrade -y -qq
apt autoremove -y -qq

read -p "Reboot required. Do you want to reboot now? (y/n): " REBOOT
if [[ $REBOOT =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    reboot
else
    echo "Installation complete. Please reboot the system to apply changes."
fi