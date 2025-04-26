# Používateľská príručka - install.md

## Úvod  
Skript `install_script.sh` slúži na inštaláciu a konfiguráciu **Wi-Fi Audit Tool** a súvisiacich komponentov na zariadení Raspberry Pi / Debian. Automatizuje stiahnutie potrebných balíkov, kompiláciu a nastavenie nástrojov pre aplikáciu Wi-Fi Audit Tool. Pomocou tohto skriptu môžete jednoducho nainštalovať moduly ako GPSD, Aircrack-ng alebo Kismet a zároveň nastaviť zariadenie ako Wi-Fi prístupový bod (AP) s captive portalom.

## Predpoklady
- **Debian:** Skript je určený pre systémy založené na Debian (využíva balíčkovací systém `apt`).  
- **Práva root (alebo sudo):** Na inštaláciu balíčkov a zmenu systémových nastavení sú potrebné administrátorské práva. Skript spustite s `sudo` alebo ako root používateľ.  
- **Ethernetové pripojenie:** Zariadenie musí byť pripojené na internet káblom cez sieťové rozhranie (štandardne `eth0`). Skript skontroluje, či je rozhranie aktívne (stav UP).  
- **Pripojenie na internet:** Počas inštalácie sa sťahujú balíky a repozitáre z internetu, preto sa uistite, že máte fungujúce pripojenie.  
- **Nástroj Git:** Na stiahnutie (klonovanie) repozitára WiFi Audit Tool sa používa `git`. Ak ho ešte nemáte, nainštalujte ho príkazom:  
  ```bash
  sudo apt install git
  ```  
- **Zálohovanie nastavení (voliteľné):** Skript prepisuje existujúce sieťové konfigurácie (napríklad hostapd, systemd-networkd atď.). Odporúča sa mať zálohu dôležitých konfiguračných súborov alebo alternatívny spôsob prístupu k zariadeniu v prípade problémov (napríklad pripojenie klávesnice a monitora priamo k zariadeniu).

## Postup inštalácie  
1. **Klonovanie repozitára:** Stiahnite repozitár WiFi Audit Tool pomocou Git príkazu:  
   ```bash
   git clone https://bitbucket.org/kis-fri/wifi-audit-tool.git
   ```  
2. **Prechod do priečinka:** V termináli prejdite do práve stiahnutého priečinka:  
   ```bash
   cd wifi-audit-tool
   ```  
3. **Spustenie skriptu:** Skript spustite s požadovanými parametrami:
   ```bash
   sudo bash ./install_script.sh [možnosti]
   ```  
   - Skript sa musí spustiť s `sudo` alebo ako root.  
   - Namiesto `[možnosti]` zadajte parametre podľa toho, ktoré moduly chcete nainštalovať (viď nasledujúcu sekciu **Parametre skriptu**).  
4. **Inštalácia a konfigurácia:** Skript spustí aktualizáciu systému, nainštaluje vybrané moduly a vykoná potrebné konfigurácie. Po dokončení inštalácie vás zariadenie vyzve na reštart systému.

## Parametre skriptu  
Skript podporuje tieto parametre (prepínače), ktoré určujú, aké komponenty sa nainštalujú:  
- `--full` alebo `-f`: **úplná inštalácia** všetkých modulov. Zahrňuje GPSD, Aircrack-ng, Kismet, AP režim (captive portal) a webovú aplikáciu WiFi Audit Tool.  
- `--gpsd` alebo `-g`: Inštaluje **GPSD** (GPS Daemon) pre prácu s GPS zariadeniami. Skript automaticky vyhľadá pripojený GPS adaptér (`/dev/ttyACM0` alebo `/dev/ttyACM1`) a nakonfiguruje ho pre použitie.  
- `--aircrack` alebo `-a`: Inštaluje **Aircrack-ng**, sadu nástrojov pre bezpečnostný audit WiFi sietí (napríklad prelomenie WEP/WPA hesiel).  
- `--kismet` alebo `-k`: Inštaluje **Kismet**, pokročilý analyzátor bezdrôtových sietí. Skript nainštaluje všetky potrebné závislosti, stiahne zdrojový kód Kismet z oficiálneho repozitára a skompiluje ho. Tiež vytvorí používateľskú skupinu pre Kismet a zapíše prihlasovacie údaje do jeho konfigurácie.  
- `--repeater` alebo `-r`: **Access Point + Captive Portal.** Nastaví zariadenie ako Wi-Fi prístupový bod (AP) s chytením autentifikácie cez captive portal pomocou `hostapd` a `nodogsplash`. Po zadaní tejto voľby vás skript vyzve na zadanie názvu (SSID) a hesla pre novú Wi-Fi sieť (prístupový bod) a tiež názvu a hesla existujúcej Wi-Fi siete, ku ktorej sa zariadenie pripojí ako klient.  
- `--app` alebo `-p`: Inštaluje samotnú **WiFi Audit Tool aplikáciu** (webové rozhranie). Skript vytvorí Python virtuálne prostredie, nainštaluje všetky potrebné Python knižnice a spustí aplikáciu ako systémovú službu. Prihlasovacie údaje, ktoré ste zadali pri inštalácii, sa následne používajú na prístup do webovej administrácie aplikácie.  

## Prihlasovacie údaje a konfigurácia AP  
Počas inštalácie vás skript vyzve na zadanie dodatočných údajov:  
- **Užívateľské meno a heslo:** Ak ste zvolili inštaláciu Kismet servera (`--kismet`), AP režimu (`--repeater`) alebo aplikácie (`--app`), skript sa po vás bude pýtať prihlasovacie meno a heslo. Tieto údaje slúžia na prístup do webovej administrácie WiFi Audit Tool (dashboard) a do webového rozhrania Kismetu. Zadajte nové bezpečné meno a heslo, ktoré si zapamätáte.  
- **Nastavenie Wi-Fi siete (AP):** Ak používate parameter `--repeater` (alebo `--full`), skript vás vyzve na konfiguráciu prístupového bodu:  
  - **AP SSID:** Zadajte názov (SSID) novej Wi-Fi siete, ktorú zariadenie vytvorí.  
  - **AP WPA heslo:** Zadajte heslo pre túto sieť.  
  - **SSID existujúcej Wi-Fi:** Zadajte názov existujúcej Wi-Fi siete, ku ktorej sa má zariadenie pripojiť ako klient.  
  - **Heslo existujúcej Wi-Fi:** Zadajte heslo pre túto existujúcu sieť.  

Tieto údaje skript použije na zostavenie konfiguračných súborov (`hostapd.conf` a `wpa_supplicant-wlan0.conf`). Zadajte ich správne – inak prístupový bod alebo pripojenie k externej sieti nemusia fungovať.

## Príklady spustenia  
- **Len GPSD:** Inštalácia iba modulu GPSD.  
  ```bash
  sudo bash ./install_script.sh --gpsd
  ```  
- **Kompletná inštalácia:** (všetky moduly vrátane GPSD, Aircrack-ng, Kismet, AP režimu a aplikácie)  
  ```bash
  sudo bash ./install_script.sh --full
  ```  
- **Aircrack-ng a Kismet:** Inštalácia iba Aircrack-ng a Kismet.  
  ```bash
  sudo bash ./install_script.sh -a -k
  ```  
- **Len aplikácia:** Inštaluje sa iba webová aplikácia WiFi Audit Tool.  
  ```bash
  sudo bash ./install_script.sh --app
  ```  

## Časté chyby a ich riešenie  
- **„Please run with sudo“:** Znamená to, že skript bol spustený bez administrátorských práv. Riešenie: Spustite ho s `sudo`, napríklad:  
  ```bash
  sudo bash ./install_script.sh --full
  ```  
- **„Ethernet (eth0) is not up“:** Skript nenašiel aktívne pripojenie na rozhraní `eth0`. Riešenie:  
  - Skontrolujte, či je ethernetový kábel pripojený a či rozhranie `eth0` existuje.  
  - Na novších systémoch môže byť sieťové rozhranie pomenované inak (napr. `enp3s0`). V takom prípade upravte skript – všade, kde sa spomína `eth0`, nahraďte názov vášho rozhrania.  
- **Chyby pri klonovaní alebo inštalácii balíkov:** Môžu nastať kvôli chýbajúcemu internetu alebo neexistencii `git`. Riešenie:  
  - Skontrolujte internetové pripojenie a stav siete.  
  - Uistite sa, že máte nainštalovaný `git`.  
  - Spustite manuálne aktualizáciu a inštaláciu balíkov:  
    ```bash
    sudo apt update
    sudo apt upgrade
    sudo apt install -f
    ```  
    a potom zopakujte `git clone` alebo spustenie skriptu.  
- **Ďalšie problémy:** Ak sa vyskytne chyba pri inštalácii konkrétneho modulu, text chyby často pomôže určiť príčinu (napríklad chýbajúca knižnica). Overte chybové hlásenia a systémové logy. Podľa potreby skúste nainštalovať požadované balíky manuálne alebo hľadajte riešenie podľa konkrétnej chyby.  
- **Obnovenie nastavení (ak sa sieť pokazí):** Ak sa po inštalácii objavia problémy so sieťou, môžete skúsiť:  
  - Vrátiť záložné konfiguračné súbory (ak ste ich vytvorili).  
  - Pripojiť sa priamo k zariadeniu (monitor/klávesnica) a ručne upraviť konfiguračné súbory.  
  - V krajnom prípade preinštalovať operačný systém a spustiť skript odznova s korektnými nastaveniami.  

