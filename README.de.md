[English](README.md) · **Deutsch**

# Desktop Destroyer

Der Klassiker aus den 90ern — jetzt für Linux. Hammer, Kettensäge, Maschinen­gewehr,
Flammenwerfer, Farbwerfer, Phaser, Stempel, Termiten und Waschpistole, losgelassen
auf deinen echten Desktop.

![Desktop Destroyer](docs/screenshot.png)

## Wie es funktioniert

Beim Start wird ein Standbild deines Desktops aufgenommen und pixelgenau als
Vollbildfenster wieder angezeigt. Was du danach zerlegst, ist dieses Bild — deine
Fenster, Dateien und Sitzung bleiben unangetastet. `Esc` beendet, `R` repariert
alles wieder.

Genau deshalb läuft es identisch unter **X11 und Wayland**: es wird nichts in
fremde Fenster gezeichnet und nichts am Compositor vorbei manipuliert.

Unter Linux gibt es kein `.exe` — das Klick-Äquivalent ist ein `.desktop`-Eintrag
im Anwendungsmenü. Den legt `./install.sh` an.

## Starten

```bash
git clone https://github.com/TechnikWeber/desktop-destroyer.git
cd desktop-destroyer
./install.sh
```

Danach steht **Desktop Destroyer** im Anwendungsmenü — anklicken, fertig.
Im Terminal geht überall einfach `desktop-destroyer`.

`install.sh` legt genau drei Dinge an: einen Menüeintrag, ein Icon und einen Befehl
in `~/.local/bin`; `./uninstall.sh` entfernt das wieder. Fehlt PySide6 (Qt 6),
fragt das Skript, ob es ein lokales `.venv` anlegen soll — sauberer ist das
Distributionspaket:

| Distribution  | Paket                              |
|---------------|------------------------------------|
| Fedora / RHEL | `sudo dnf install python3-pyside6` |
| Debian/Ubuntu | `sudo apt install python3-pyside6` |
| Arch          | `sudo pacman -S pyside6`           |

## Steuerung

| Taste                      | Wirkung                                     |
|----------------------------|---------------------------------------------|
| `1` … `9`                  | Waffe wählen                                |
| Linke Maustaste            | zuschlagen, halten für Dauerfeuer           |
| Mausrad                    | nächste / vorherige Waffe                   |
| `Tab` oder rechte Maustaste| Werkzeugkasten ein- und ausblenden          |
| `R`                        | Desktop komplett reparieren                 |
| `S`                        | Trümmerfeld als PNG speichern (`~/Bilder`)  |
| `M`                        | Ton an / aus                                |
| `Esc` oder `Q`             | Beenden                                     |

Den Werkzeugkasten kannst du an seiner Titelleiste verschieben.

## Die neun Werkzeuge

| # | Werkzeug        | Wirkung                                                        |
|---|-----------------|----------------------------------------------------------------|
| 1 | Hammer          | Ein Schlag pro Klick: Krater mit verästelten Rissen, Bildschirm wackelt |
| 2 | Kettensäge      | Ziehen schneidet eine durchgehende, ausgefranste Kerbe; Sägemehl fliegt |
| 3 | Maschinengewehr | Dauerfeuer mit Streuung, Einschusslöchern, Mündungsfeuer und Hülsen |
| 4 | Flammenwerfer   | Verkohlt die Oberfläche schwarz, Blasen werfen, Rauch steigt auf |
| 5 | Farbwerfer      | Spritzer in wechselnden Farben, die nach unten verlaufen        |
| 6 | Phaser          | Brennt einen glühenden Schnitt quer über den Bildschirm         |
| 7 | Stempel         | Drückt „KAPUTT", „VOID", „REJECTED" … schräg und krisselig auf  |
| 8 | Termiten        | Setzt Termiten aus, die umherlaufen und Fraßgänge nagen         |
| 9 | Waschpistole    | Das Rückgängig-Werkzeug: wäscht den Desktop wieder sauber       |

## Kommandozeile

```
desktop-destroyer [Optionen]

  -w, --windowed       im normalen Fenster statt im Vollbild (gut zum Testen)
  -i, --image DATEI    ein Bild statt des echten Desktops zerlegen
  -m, --mute           stumm starten
  -d, --delay SEKUNDEN vor der Aufnahme warten
      --primary-only   nur den Hauptbildschirm übernehmen
      --backend        erkanntes Screenshot-Verfahren ausgeben und beenden
```

## Screenshot-Verfahren

Das Standbild wird über die erste Methode geholt, die auf dem System funktioniert:

* **X11** — Qt greift die Root-Fenster direkt ab; sonst `maim`, `scrot`, `import`
* **Wayland** — `grim` (wlroots: Sway, Hyprland, river, Wayfire), `spectacle` (KDE),
  `org.gnome.Shell.Screenshot`, `gnome-screenshot`
* **überall** — `org.freedesktop.portal.Screenshot` als letzter Ausweg
  (kann je nach Compositor einmalig nachfragen)

`desktop-destroyer --backend` zeigt, was gewählt wurde. Klappt nichts davon,
startet das Spiel trotzdem — dann eben mit einem gemalten Ersatz-Desktop.

## Warum keine Grafik- und Audiodateien?

Es gibt keine. Sämtliche Werkzeug-Icons sind Vektorzeichnungen in `icons.py`,
alle Geräusche werden beim ersten Start in `sfx.py` synthetisiert und unter
`~/.cache/desktop-destroyer/` abgelegt. Ein `git clone` genügt.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
