# Obsah
- [1  Prihlasovacia stránka](/#1--prihlasovacia-stranka-login)
- [2  Domovská stránka](/#2--domovská-stránka-home)
- [3  Konfiguračná stránka](/#3--konfiguračná-stránka-config)
- [4  Audit stránka](/#4--audit-stránka-audit)
- [5  Cracking stránka](/#5--cracking-stránka-cracking)
- [6  Report stránka](/#6--report-stránka-report)
- [7  Logs stránka](/#7--logs-stránka-log)
- [8  Terminal stránka](/#8--terminal-stránka-terminal)


# 1  Prihlasovacia stránka (`/login`)

Prihlasovacia stránka je prvým krokom k používaniu **Wi‑Fi Audit Tool**. Umožňuje overiť identitu používateľa v aplikácii.

---

## 1.1  Čo na nej nájdete

| Prvok           | Popis                                                                                                    |
|-----------------|-----------------------------------------------------------------------------------------------------------|
| **Username**    | Textové pole na zadanie používateľského mena. Vzniká pri inštalácii (zadáva ho skript `install.sh`). |
| **Password**    | Pole pre heslo.|
| **Remember Me** | Prepínač, ktorý po začiarknutí udrží prihlásenie aktívne 7 dní.   |
| **Login**       | Tlačidlo, ktoré odošle údaje na server a v prípade správnej kombinácie **Username + Password** používateľa prihlási. |

---

## 1.2  Ako sa prihlásiť
1. Otvorte prehliadač a zadajte adresu zariadenia, napr. `http://192.168.4.1`.  
2. Do poľa **Username** napíšte svoje používateľské meno.  
3. Do poľa **Password** zadajte príslušné heslo.  
4. **Remember Me** týždeň uchová prihlásenie.  
5. Kliknite **Login**.

Po úspešnom prihlásení budete presmerovaní na domovskú stránku (**Home**). Ak bol pokus neúspešný, zobrazí sa hláška *Invalid username or password*.

---

# 2  Domovská stránka (`/home`)

Po úspešnom prihlásení sa objaví **domovská stránka**, ktorá slúži ako rozcestník do všetkých modulov a zároveň zobrazuje aktuálnu konfiguráciu systému.

---

## 2.1  Navigačné menu
Rozdelené je na **systémovú** a **aplikačnú** časť.

### 2.1.1  Systémová lišta (horný riadok)
| Odkaz / prvok | Funkcia |
|---------------|---------|
| **Logged in:** *username* | Zobrazuje práve prihláseného používateľa. |
| **Logout** | Okamžité odhlásenie a presmerovanie na prihlasovaciu stránku. |
| **Kismet WEB** | Otvorí webové rozhranie Kismetu v novom okne — dostupné len počas bežiaceho auditu. |
| **Clear kismet folder** | Vymaže všetky nazbierané súbory. |
| **Clear reports folder** | Vymaže všetky doteraz vytvorené reporty. |
| **Restart APP** | Reštartuje Flask backend (užitočné pri zlyhaní modulu). |
| **Restart system** | Reštartuje celé Raspberry Pi. |
| **Shutdown system** | Bezpečné vypnutie zariadenia. |
| **Toggle Theme** | Prepnúť medzi tmavou a svetlou témou. |

> *Tip:* pred ručným reštartom služby/skupiny modulov stačí často kliknúť **Restart APP**, čo trvá len pár sekúnd a nezastaví systémové procesy.

### 2.1.2  Aplikačná lišta (druhý riadok)
| Odkaz | Modul | Stručný popis |
|-------|-------|---------------|
| **Home** | Domovská stránka | Prehľad aktuálnej konfigurácie (viď nižšie). |
| **Config** | Konfigurácia | Detailné nastavenie rozhraní, logovania, parametrov auditu, zoznamov a wordlistov. |
| **Audit** | Audit Wi‑Fi | Spustenie/stop auditu (Kismet → Parser → Tests) a live status. |
| **Cracking** | Prelamovanie | Vyhľadanie AP, zachytenie handshake, slovníkový útok. |
| **Report** | Reporty | Tvorba HTML/CSV reportov zo zbieraných dát. |
| **Logs** | Logy | Živý výpis súboru `logs/app.log`. |
| **Terminal** | Web Terminal | Vstavaný linuxový terminál (ak je povolený v Config). |

---

## 2.2  Obsah stránky *Home*
Pod navigáciou sa nachádza nadpis **Current Configuration** a stromové zobrazenie JSON súboru `config/config.json`.

* Každá kľúčová hodnota sa rekurzívne rozbalí do prehľadného zoznamu.  
* Úpravy konfigurácie sa vykonávajú na stránke **Config**; *Home* slúži výhradne na rýchlu vizuálnu kontrolu.

---

# 3  Konfiguračná stránka (`/config`)

Konfiguračná stránka, práve tu sa určujete, ktoré rozhrania sa používajú, aké filtračné listy sa použijú a aké heslá sa budú skúšať pri slovníkových útokoch.

> **Obmedzenie:** Ak beží Audit alebo Cracking, konfiguráciu nemožno meniť. Najprv zastavte príslušný modul.

---

## 3.1  Rozhranie stránky
Stránka je rozdelená do niekoľkých **fieldsetov**. Po stlačení **Save Configuration** sa všetky hodnoty zapíšu do `config/config.json` a aplikácia sa reštartuje, aby sa nové nastavenia okamžite prejavili.

### A  Wi‑Fi audit settings
#### 1. Interface
| Pole | Význam |
|------|--------|
| **Available Interfaces** | Výpis všetkých Wi‑Fi kariet detegovaných v systéme (názov rozhrania, MAC adresa). |
| **Monitoring** | Rozhranie, ktoré sa prepne do *monitor mode* a bude zachytávať pakety (Kismet). |
| **Cracking** | Rozhranie, ktoré sa prepne do *monitor mode* iba počas prelamovania hesiel. Ak nechcete cracking, zvoľte **None**. |

> **Validácia:** Nie je dovolené použiť rovnaké rozhranie na Monitoring aj Cracking.

#### 2. Logger
Určuje úroveň detailu výpisu pre:
* **Console Level** – čo sa zobrazuje v reálnom čase v CLI.
* **File Level** – čo sa zapisuje do `logs/app.log`.

Úrovne (od najpodrobnejšej): `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

#### 3. General Settings
| Parameter | Popis |
|-----------|-------|
| **Scan Type** | Ako sa filtrujú SSID pri audite: `1` – len **whiteList.txt** `2` – všetko okrem **blackList.txt** `3` – biela + čierna listina kombinačne |
| **Main Sleep (s)** | Pauza medzi dvomi cyklami hlavnej slučky auditu (Parser → Tests). |
| **Max AP Distance (m)** | Maximálna vzdialenosť (GPS) medzi AP, po ktorej sa považujú za duplicitné (test *GPS_DISTANCE*). |

### B  Web settings
| Prepínač | Funkcia |
|----------|---------|
| **Enable terminal** | Ak je zaškrtnuté, v menu „Terminal“ sa povolí webový linuxový shell na správu zariadenia. |

### C  List settings
Tri textové polia predstavujú regulárne **zoznamy SSID** — každý jeden riadok = jeden vzor.
| Súbor | Úloha |
|-------|-------|
| **whiteList.txt (1)** | SSID, ktoré **musí** audit zahrnúť. |
| **blackList.txt (2)** | SSID, ktoré sa **ignorujú**. |
| **whiteBlackList.txt (3)** | Pokročilý filter, ktorý kombinuje whitelist a blacklist. |

> Riadky môžu obsahovať aj regular‑expression (regex). Napr. `^HUAWEI#.*2G`.

### D  Custom password list
Vlastný wordlist (jedno heslo na riadok) používaný pri prelamovaní hesiel počas auditu pri voľbe *customPasswordList*.

### E  Save Configuration
Odosiela formulár. Po úspešnom zápise sa aplikácia reštartuje — v hornom menu sa zobrazí hláška o uložení.

---

## 3.2  Odporúčaný pracovný postup
1. **Najprv** zvoľte Wi‑Fi karty — jednu na audit (*Monitoring*), druhú (voliteľne) na cracking.  
2. Nastavte úrovne logu (v produkcii zvyčajne `INFO` do konzoly  a `WARNING` do súboru).  
3. Upravením **Scan Type** + zoznamov si vyfiltrujte testované AP.  
4. Pridajte vlastný wordlist, ak chcete vyskúšať heslá špecifické pre lokálnu sieť.  
5. Kliknite **Save Configuration** a počkajte na reštart.

---

# 4  Audit stránka (`/audit`)

Audit stránka je centrom zberu dát — práve tu spúšťate alebo zastavujete **hlavnú slučku auditu** a voliteľne pripojíte modul Cracking. Všetko prebieha v reálnom čase, takže okamžite vidíte, ktorý pod‑modul beží a aký test sa práve vykonáva.

---

## 4.1  Hlavný panel
| Prvok | Popis |
|-------|-------|
| **Audit status** | Dynamický nápis mení farbu podľa stavu: `Running` – aktualne beží, `Waiting` – audit beží, modul čaká, `Stopped` – modul zastavený. |
| **START / STOP** | Veľké tlačidlo prepína audit. *START* spustí audit; *STOP* ukončí všetky moduly a resetuje stav. |

> **Poznámka:** pred prvým štartom skontrolujte v **Config** správne nastavené rozhrania.

---

## 4.2  Voľba „Enable cracking“
| Pole | Funkcia |
|------|---------|
| **Enable cracking** | Zaškrtnite, ak chcete počas auditu automaticky skúšať prelomiť WPA/WEP. |
| **Handshake capture time** | Čas (v sekundách) — ako dlho sa bude pri každom AP zbierať handshake predtým, než sa spustí Aircrack‑ng. Odporúčané ≥ 60 s. |
| **Cracking type** | *rockyoutxt* – použije klasický wordlist **rockyou.txt**, *customPasswordList* – využije váš `customPasswordList.txt` (nastavený v Config). |

> Ak **Cracking** rozhranie v Config = `None`, cracking sa neaktivuje.

---

## 4.3  Stavové indikátory modulov
| Stav | Farba |
|-------|-------|
| **Running** | Zelená (🟢)|
| **Waiting** | Oranžová (🟠)|
| **Stopped** | Červená (🔴) |

> Všetky indikátory sa obnovujú každú sekundu; ak prepnete na iné okno, tak sa interval pozastaví.

---

## 4.4  Typický pracovný postup
1. Na Config stránke zvoľte rozhrania a uložte konfiguráciu.  
2. (Voliteľne) zaškrtnite **Enable cracking**, zadajte čas a wordlist. 
3. Prejdite na **Audit** a kliknite **START**. 
4. Sledujte, ako sa menia stavové nápisy a aktuálne testy.  
5. Po dokončení kliknite **STOP**. 
6. Prejdite na **Report** a vygenerujte report z poslednej databázy.

---

# 5  Cracking stránka (`/cracking`)

Stránka **Cracking** slúži na **cieľené prelomenie hesla jedného konkrétneho Wi‑Fi AP** bez spustenia celého auditu.

> **Obmedzenie:** Ak práve beží modul Audit, Cracking je zakázaný.

---

## 5.1  Pracovný postup v skratke
1. Kliknite **Scan for Access Points** – zariadenie na 10 s preskenuje okolie a načíta zoznam s výsledkami.
2. Vyberte AP zo zoznamu (SSID / BSSID / kanál).  
3. Stlačte **START** – začne sa zachytávať handshake a automaticky spustí Aircrack‑ng.  
4. Sledujte **live konzolu** – vypisuje podrobnosti vrátane deauth útokov, zachytenia handshake, priebeh Aircrack‑ng a prípadný nájdený kľúč.
5. Kedykoľvek môžete proces ukončiť tlačidlom **STOP**.

---

## 5.2  Popis ovládacích prvkov
| Prvok | Úloha |
|-------|-------|
| **Scan for Access Points** | Spustí `airodump-ng` (10 s) na rozhraní *cracking*. Po dokončení sa vyparsujú všetky SSID/BSSID/Channel a vypíšu do rozbaľovacieho menu. |
| **Select a Wi‑Fi Access Point** | Zoznam nájdených AP.|
| **START** | **START** spustí: • zachytávanie handshake (airodump‑ng + deauth slučka); • po zachytení handshaku sa spustí prelamovanie hesiel *Aircrack‑ng* so súborom *rockyou.txt*.|
| **STOP** | Ukončí procesy prelamovania hesiel. |
| **Cracking status** | Text nad nadpisom: `Scanning`, `Running`, `Waiting`, `Stopped` (mení farbu a bliká podobne ako na Audit stránke). |
| **Status box (live konzola)** | Modul sem zapisuje všetky dôležité udalosti s časovou pečiatkou (monitor‑mode, deauth, handshake found, aircrack‑ng výsledky…).|

---

## 5.3  Uložené výsledky
* Úspešne prelomené kľúče sa zapisujú do súboru `/var/log/cracked_ap_keys.txt` v tvare:  
`MyWiFi (AA:BB:CC:DD:EE:FF): qwerty123`
* Zoznam sa načítava vždy pri načítaní stránky a zobrazuje sa pod live konzolou.

---

## 5.4  Kedy použiť Cracking namiesto Auditu?
* Ak potrebujete **otestovať iba jeden AP** a nechcete spúšťať plný audit.  
* Keď sa Audit skončil, ale handshake chýbal – viete skúsiť ručne s nekonečnou dobou odchytu.

---

# 6  Report stránka (`/report`)

Modul **Report** premieňa surové dáta z auditu na prehľadné výstupy (HTML alebo CSV). Vytvorené súbory sa automaticky ukladajú do priečinka `reports/` a zostávajú dostupné na stiahnutie.

---

## 6.1  Dvojkrokový sprievodca
| Krok | Čo vybrať | Popis |
|------|-----------|-------|
| **1 – Select Database** | `.sqlite3` súbor | Zobrazí zoznam uložených databáz z auditu. Kliknite **Next**. |
| **2 – Select Report Type** | Typ + (voliteľne) zariadenie | Po výbere DB sa zobrazí ďalší formulár: **Report Type** – 4 možnosti (tabuľka 6.2). **Device** – zoznam SSID+BSSID; zobrazuje sa len pri type **one**. Kliknite **Create Report** (otvorí sa v novom okne). |

> **Help on Report** – otvorí stránku *report_help.html* v novom okne s podrobným popisom polí reportov.

---

## 6.2  Typy reportov
| Hodnota (`type`) | Názov v GUI | Obsah / použití |
|-----------------|-------------------------|--------------------------------------------------------------|
| `one` | *One Wi‑Fi AP per page* | Detailný report jediného AP: tabuľka parametrov, zoznam testov, frekvenčný graf, mapa + reverzné geokódovanie, stiahnutie PDF/HTML. |
| `separate` | *All devices – separate* | Všetky AP postupne, každý má vlastný podnadpis, tabuľku, graf a individuálnu mapu. |
| `combined` | *All devices – combined on one map* | Jedna interaktívna mapa so všetkými značkami + karty AP pod ňou. Vhodné na rýchly geografický prehľad. |
| `csv` | *CSV* | Dvojicu tabuliek **devices** a **tests** exportuje do CSV. Tlačidlo **Download CSV** vygeneruje súbor pre offline spracovanie. |

---

## 6.3  Sekcia „Existing Reports“
Pod formulárom sa zobrazuje zoznam už vygenerovaných HTML súborov. Kliknutím otvoríte report v novom okne; ten je možné tlačiť alebo uložiť.

> Staré reporty môžete jedným klikom zmazať cez systémovú lištu → **Clear reports folder**.

---

## 6.4  Typický workflow
1. Po dokončení auditu otvorte **Report**.  
2. Vyberte najnovšiu databázu (zoradené podľa dátumu).  
3. Zvoľte typ reportu; pri type **one** vyberte konkrétny AP.  
4. Kliknite **Create Report** – nová karta zobrazí výstup.  
5. (Voliteľne) stlačte **Download → PDF** alebo **HTML** priamo v reporte.  
6. Pre export do Excelu vyberte typ **CSV** a stiahnite.

---

## 6.5  Riešenie problémov
| Problém | Riešenie |
|---------|----------|
| **„No databases available“** | Najprv spustite Audit; každé spustenie vytvorí novú `.sqlite3` DB. |
| **„Device not found“** | Databáza pravdepodobne neobsahuje zvolený `device_id`; v okolí auditu zrejme nie je žiadne zariadenie. |
| **Mapa sa nezobrazí** | Stránka vyžaduje pripojenie na internet pre dlaždice a reverzné geokódovanie; offline režim skryje mapu. |

---

# 7  Logs stránka (`/log`)

Stránka **Log** poskytuje **živý náhľad do súboru `logs/app.log`**, v ktorom sa zhromažďujú správy zo všetkých modulov (Audit, Cracking, Report, Web‑UI …). Tento log je prvým miestom, kam sa pozrieť pri akýchkoľvek chybách alebo nečakanom správaní aplikácie.

---

## 7.1  Ovládacie prvky
| Prvok | Funkcia |
|-------|---------|
| **Refresh** | Okamžite načíta aktuálny obsah logu. |
| **Auto refresh** | Ak je zaškrtnuté, stránka volá endpoint každú 1 s a automaticky posúva zobrazenie na koniec. *Prepnutie na inú kartu dočasne pozastaví aktualne log správy.* |
| **Log window** | Blok s textom logu. |

---

## 7.2  Čo sa zapisuje do `app.log`?
* **INFO** hlášky o štarte/stop modulu, uložení konfigurácie, vygenerovaní reportu…
* **DEBUG** detailné interné stavy (voliteľné podľa nastavenia v [Config → Logger]).
* **WARNING/ERROR/CRITICAL** výnimky, zlyhané systémové príkazy, chýbajúce súbory atď.

---

# 8  Terminal stránka (`/terminal`)

Interný modul **Flask‑Terminal** embeduje plnohodnotnú Linux konzolu priamo do prehliadača. Po prihlásení máte pocit, akoby ste boli v `ssh` – vidíte prompt, môžete spúšťať príkazy, prehliadať súbory či editovať konfiguráciu.

> **Bezpečnosť:** Terminál je dostupný iba vtedy, ak je v [Config → Web settings] zaškrtnuté **Enable terminal**. Inak sa odkaz v menu nezobrazí.

---

## 8.2  Praktické použitie
| Scenár | Príkazy |
|--------|---------|
| **Diagnostika siete** | `iw dev`, `ifconfig -a`, `ping 8.8.8.8`, `systemctl status kismet` |
| **Správa logov** | `tail -f logs/app.log`, `journalctl -u wifi_audit_tool.service` |
| **Aktualizácia systému** | `apt update && apt upgrade` (odporúča sa mimo auditu) |
| **Úprava konfigurácie** | `nano config/customPasswordList.txt` |

---

## 8.3  Dôležité informácie
* **Oprávnenia** – terminál beží pod rovnakým používateľom ako služba aplikácie (root).
* **Zdieľané zdroje** – spustené príkazy môžu ovplyvniť prebiehajúci Audit/Cracking.