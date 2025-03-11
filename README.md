# Prenosný systém pre automatizovaný audit Wi-Fi sietí v organizáciách
## Návod na spojazdnenie riešenia - DP_Róbert_Dobis_2021_code

Riešenie bolo overené na zariadení **Raspberry Pi 4B 8GB** s operačným systémom **Raspberry Pi OS (64-bit) 19.11.2024** (resp. **Debian GNU/Linux 12 / bookworm**).  
Odporúčaná minimálna HW konfigurácia:  
- **4 GB RAM**  
- **32 GB SD karta**

> Na testovanie a beh skriptov bol použitý **Python 3.11**; kompatibilita so staršími verziami Pythonu nebola overená.


### Zmeny v riešení
- **Aktualizácia inštalačného skriptu** (`./Install_script/install.sh`)  
- **Aktualizácia a oprava kódu** v jednotlivých moduloch


### Inštalácia

Spustite inštalačný skript (vyžaduje **sudo** práva) príkazom:

```bash
sudo ./Install_script/install.sh -h | -a | -A | -k | -s | -w | -f
```

**Dostupné parametre:**
- **`-h`**  
  Zobrazí prehľadný help s popisom použitia a argumentov.
- **`-a`**  
  Nainštaluje Aircrack-ng z Debian repozitára.
- **`-A`**  
  Nainštaluje a skompiluje Aircrack-ng zo zdrojových kódov [GitHub aircrack-ng](https://github.com/aircrack-ng/aircrack-ng).
- **`-k`**  
  Nainštaluje a skompiluje Kismet zo zdrojových kódov [GitHub kismet](https://github.com/kismetwireless/kismet).
- **`-s`**  
  Nastaví podporu GPS v Kismete (vytvorí konfiguračný súbor s GPS parametrami).
- **`-w`**  
  Nainštaluje WiFi Audit tool vrátane vytvorenia Python virtual environmentu.
- **`-f`**  
  Spustí kompletnú inštaláciu (Aircrack-ng, Kismet a WiFi Audit tool) v jednom kroku.


### Konfiguračný súbor
Konfigurácia systému sa nastavuje v súbore **config/config.cfg**, kde sú definované nasledujúce parametre:

- `IFACE` - Monitorovací Wi-Fi interface. (napr. `wlan1`)
- `IFACE2` - Interface určený na crackovanie/test overenia pripojenia. (napr. `wlan2`)
- `SCAN_TYPE`:
  - `1` = WhiteList - zoznam prístupových bodov, ktoré chceme testovať
  - `2` = BlackList - a zoznam prístupových bodov, ktoré nechceme testovať
  - `3` = WhiteBlackList - zoznam prístupových bodov, ktoré chceme testovať, ako aj zoznam tých, ktoré nechceme testovať.
  > WhiteBlackList: Chceme otestovať všetky zariadenia, ktoré začínajú EDU ale nechceme tie, ktorú sú EDU-guest.


### Spustenie programu
Po úspešnej inštalácii a nastavení konfiguračných parametrov je možné spustiť hlavný program príkazom:

```bash
sudo python3 app.py main.py
```

### Vytvorenie reportu

Na generovanie reportu z nazbieraných dát slúži skript `report.py`:

```bash
sudo python3 app.py report.py [-h] [--csv] [--osm] [-device device_ssid] <database>
```
- **--csv** – vytvorí CSV súbor.
- **--osm** – vytvorí HTML report (1 zariadenie → 1 HTML stránka) s využitím OpenStreetMap.
- *(bez argumentov)* – vytvorí HTML stránku so zariadeniami s využitím Google Maps (iframe).

#### Príklady:
```bash
sudo python3 app.py report.py Kismet-20210401-07-30-00-1.sqlite3
sudo python3 app.py report.py Kismet-20210401-07-30-00-1.sqlite3 --osm
sudo python3 app.py report.py Kismet-20210401-07-30-00-1.sqlite3 --osm -device "Tp-link2G"
```

Výsledný report je dostupný vo webovom prehliadači na adrese:
```
http://<ip_adresa_zariadenia>/reports/maps/
```

### Príklad použitia
V typickej konfigurácii na zariadení Raspberry Pi je potrebné do konfiguračného súboru nastaviť:
- **IFACE**=`wlan1` (monitorovací Wi-Fi interface),  
- **IFACE2**=`wlan2` (interface určený na crackovanie alebo test overenia pripojenia).
- **SCAN_TYPE**=`3` (podľa požiadaviek potrebné upraviť súbory v **config** priečinku)

> Vstavaný interface `wlan0` na Raspberry Pi nepodporuje monitorovací režim a zároveň má slabší dosah.

**Očakávaný výsledok**:
- Po spustení auditu pomocou skriptu `app.py` sa spustí aplikácia kismet, ktorá monitoruje na Wi-Fi interface `IFACE`. Z kismet databázy sa preparsujú potrebné dáta a vytvorí sa sqlite3 databáza, z ktorej sa následne robia reporty.
- Následne, po spustení skriptu `report.py`, na základe týchto uložených údajov sa vygeneruje report.

### Troubleshooting / Riešenie problémov
Ak aplikácia nefunguje korektne, môže to byť spôsobené napríklad problémami s ovládačmi pre Wi-Fi alebo GPS zariadenie. Pre overenie podpory konkrétneho hardvéru v Linuxe je možné využiť webovú stránku:
- [linux-hardware.org](https://linux-hardware.org/?view=search)

Táto stránka vám pomôže identifikovať, či operačný systém Linux podporuje dané zariadenie alebo či bude potrebné doinštalovať špeciálny ovládač.  
