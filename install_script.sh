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
TOOLS=false
KISMET=false
KISMET_BIN=false
APP=false

usage() {
    cat <<EOF
Usage: $0 [--full|-f] [--gpsd|-g] [--tools|-t] [--kismet|-k] [--kismet-bin|-b] [--app|-p]
  --full,      -f   full install (all modules)
  --gpsd,      -g   gpsd
  --tools,     -t   tools (aircrack-ng, hcxdumptool, hcxtools)
  --kismet,    -k   kismet (build from source)
  --kismet-bin,-b   kismet (prebuilt via apt)
  --app,       -p   wifi_audit_tool application
  --help,      -h   show this help message
EOF
    exit 1
}

configure_kismet() {
    local CONF_DIR="$1"
    
    # configure confs if gpsd is running
    if pgrep -x gpsd &>/dev/null; then
        echo "Writing Kismet GPS site config..."
        cat > "$CONF_DIR/kismet_site.conf" <<EOF
gps=gpsd:host=localhost,port=2947
EOF
        chmod 644 "$CONF_DIR/kismet_site.conf"
    else
        echo "gpsd not running; skipping Kismet GPS config"
    fi

    echo "Appending Kismet logging prefs..."
    {
        echo "kis_log_data_packets=false"
        echo "kis_log_duplicate_packets=false"
    } >> "$CONF_DIR/kismet_logging.conf"

    echo "Appending Kismet HTTPd credentials..."
    {
        echo "httpd_username=$USER_GLOBAL"
        echo "httpd_password=$PASS_GLOBAL"
    } >> "$CONF_DIR/kismet_httpd.conf"
}

# — parse short and long options via getopt
PARSED=$(getopt --options fgakbpt --long full,gpsd,tools,kismet,kismet-bin,app,help --name "$0" -- "$@")
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
        -t|--tools)
            TOOLS=true; shift ;;
        -k|--kismet)
            KISMET=true; shift ;;
        -b|--kismet-bin)
            KISMET_BIN=true; shift ;;
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
    TOOLS=true
    APP=true

    read -p "Do you want to build latest Kismet from source? (y/N): " BUILD_KISMET
    if [[ $BUILD_KISMET =~ ^[Yy]$ ]]; then
        KISMET=true
    else
        KISMET_BIN=true
    fi
fi

if ! $GPSD && ! $TOOLS && ! $KISMET && ! $KISMET_BIN && ! $APP; then
    usage
fi

# — prompt for credentials
if $KISMET || $KISMET_BIN || $FULL || $APP; then
    read -p "Enter username for app user: " USER_GLOBAL
    read -s -p "Enter password for app user: " PASS_GLOBAL
    echo
fi


echo "Updating package lists..."
apt update -y -qq
apt upgrade -y -qq
apt autoremove -y -qq

# —— MODULE: GPSD
if $FULL || $GPSD; then
    # auto-detect device before installing
    if [[ -e /dev/ttyACM0 ]]; then
        DEV="/dev/ttyACM0"
    elif [[ -e /dev/ttyACM1 ]]; then
        DEV="/dev/ttyACM1"
    elif [[ -e /dev/ttyUSB0 ]]; then
        DEV="/dev/ttyUSB0"
    else
        DEV=""
    fi

    if [[ -z "$DEV" ]]; then
        echo "No GPS device (/dev/ttyACM0, /dev/ttyACM1, /dev/ttyUSB0) found." >&2
        echo "Skipping GPS installation because no antenna is connected."
        GPSD=false
    fi

    if $GPSD; then
        echo "Installing GPSD..."
        apt install -y -qq gpsd

        cat > /etc/default/gpsd <<EOF
DEVICES="$DEV"
GPSD_OPTIONS="-n -G -b"
USBAUTO="true"
EOF
        echo "GPSD configured for $DEV"
        systemctl restart gpsd || true

        # configure Kismet if it's already installed
        if [[ -d "/etc/kismet" ]]; then
            echo "Writing Kismet GPS site config to /etc/kismet..."
            echo "gps=gpsd:host=localhost,port=2947" >> /etc/kismet/kismet_site.conf
            chmod 644 /etc/kismet/kismet_site.conf
        elif [[ -d "/usr/local/etc" && -f "/usr/local/etc/kismet_logging.conf" ]]; then
            echo "Writing Kismet GPS site config to /usr/local/etc..."
            echo "gps=gpsd:host=localhost,port=2947" >> /usr/local/etc/kismet_site.conf
            chmod 644 /usr/local/etc/kismet_site.conf
        fi
    fi
fi

# —— MODULE: TOOLS
 if $TOOLS; then
    echo "Installing aircrack-ng, hcxdumptool, hcxtools..."
    apt install -qq -y aircrack-ng hcxdumptool hcxtools
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

    configure_kismet "/usr/local/etc"
fi

# —— MODULE: Kismet (Prebuilt via apt)
if $KISMET_BIN; then
    echo "Installing prebuilt Kismet..."
    apt install -y -qq wget lsb-release gnupg
    wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key | gpg --dearmor --yes -o /usr/share/keyrings/kismet-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/kismet-archive-keyring.gpg] https://www.kismetwireless.net/repos/apt/release/$(lsb_release -cs) $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/kismet.list
    apt update -y -qq
    apt install -y -qq kismet

    usermod -aG kismet "${SUDO_USER:-$USER}"

    configure_kismet "/etc/kismet"
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
    echo "Installing Python packages from requirements.txt..."
    "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

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
