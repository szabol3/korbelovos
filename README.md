# Körbelövős MicroPython Projekt

Ez a projekt egy egyszerű, körpályán mozgó lövöldözős játék MicroPython környezethez, SSD1306 OLED kijelzőre optimalizálva. A játékot egyetlen gombbal lehet irányítani. 

## Könyvtárstruktúra

- **korbelovos.py** – A játék fő programja, tartalmazza a játékmenetet, hardverkezelést, rajzolást.
- **ssd1306.py** – SSD1306 OLED kijelző meghajtó MicroPythonhoz.

## Fő funkciók

- Körpályán mozgó játékos és középen álló ellenség, lövedékek, pajzsok, pontszámítás.
- Egygombos irányítás (irányváltás).
- OLED kijelző támogatás (72x40 px).

## Használat

1. Másold fel a projekt python (.py) fájljait a MicroPython eszközödre. A korbelovos.py -t main.py néven mentsd, akkor automatikusan az indul el mikor áramot kap.
2. A játékban a gombbal irányíthatod a játékost.

## Követelmények

- MicroPython kompatibilis eszköz (pl. Raspberry Pi Pico)
- SSD1306 OLED kijelző (I2C, 72x40 px)

## Fájlok

- [korbelovos.py](korbelovos.py) – Játéklogika
- [ssd1306.py](ssd1306.py) – OLED driver

## Szerző

- Soma (2025)
- Thon of Py oktató: Szabó László
---

A projekt szabadon felhasználható oktatási és hobbi célokra.