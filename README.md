# Wi-Fi Audit Tool

## Fork
Forked from: https://bitbucket.org/kis-fri/wifi-audit-tool.git

## Krátky popis  
Wi-Fi Audit Tool je prenosné zariadenie určené na automatizovaný audit Wi-Fi sietí v organizáciách. Cieľom projektu je modernizovať hardvér i softvér pôvodného systému (branch: dobis-original) a doplniť nové funkcie, aby sa zvýšila úroveň zabezpečenia bezdrôtových sietí. Súčasťou systému je webové používateľské rozhranie, ktoré umožňuje jednoduchú správu a vyhodnocovanie výsledkov auditu.  

## Inštalácia  
Inštaláciu systému je možné vykonať pomocou skriptu `install_script.sh`, ktorý automaticky nainštaluje a nakonfiguruje potrebné komponenty. Podrobný postup nájdete v [Používateľskej príručke – install.md](Pouzivatelska_prirucka-install.md). Po úspešnej inštalácii sa aplikácia automaticky spustí a bude dostupná na adrese http://192.168.4.1.  

## Funkcionality  
Hlavné funkcie Wi-Fi Audit Tool zahŕňajú:  
- Automatizovaný audit Wi-Fi sietí (skener bezdrôtových sietí)  
- Detekcia zraniteľností v bezdrôtových sieťach  
- Prelamovanie hesiel Wi-Fi (napr. WEP/WPA)  
- Generovanie reportov z auditu  
- Webové používateľské rozhranie pre správu a vyhodnocovanie výsledkov  

## Použitie  
Pre prístup k webovému rozhraniu sa pripojte k Wi-Fi sieti vytvorenej zariadením a v prehliadači otvorte adresu http://192.168.4.1. Zobrazí sa prihlasovacia stránka, kde zadáte užívateľské meno a heslo nastavené počas inštalácie.  

## Používateľské príručky  
Projekt obsahuje dve používateľské príručky:  
- [Používateľská príručka – install.md](Pouzivatelska_prirucka-install.md): popisuje inštaláciu a konfiguráciu systému krok za krokom  
- [Používateľská príručka – web.md](Pouzivatelska_prirucka-web.md): vysvetľuje použitie webového rozhrania a detailne popisuje jeho funkcie