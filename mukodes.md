# Korbelövős játék – Programstruktúra és működés

Ez a dokumentum összefoglalja a `korbelovos.py` MicroPython játék főbb szerkezeti elemeit és működését.

## Főbb modulok és szerkezet

- **Hardver inicializálás:**  
  A program elején inicializálja az I2C-t az OLED kijelzőhöz, valamint a gombot. Ha nem MicroPython környezetben fut, "dummy" kijelző/gomb objektumokat hoz létre teszteléshez.

- **Globális konfiguráció:**  
  A játék elején számos konstans határozza meg a kijelző méretét, a gomb és I2C lábak számát, a játékos és ellenség tulajdonságait (sebesség, életerő, lövedékek, pajzs stb.), valamint a pontozás logikáját.

- **Játékállapot változók:**  
  Globális változók tárolják a játékos és ellenség aktuális állapotát (pozíció, életerő, lövedékek, pajzs, pontszám stb.).

- **Segédfüggvények:**  
  - Kör és ív rajzolása a kijelzőre.
  - Távolság számítás, pont íven belüliségének ellenőrzése.

- **Játéklogika fő részei:**  
  - **Játékos frissítése:** A játékos körpályán mozog, automatikusan lő, ha lehet.
  - **Ellenség frissítése:** Az ellenség különböző támadási mintákat választ véletlenszerűen, időnként pajzsot aktivál.
  - **Lövedékek frissítése:** Mindkét fél lövedékei mozognak, ütközés esetén sebzést okoznak vagy eltűnnek.
  - **Pajzs logika:** Az ellenség pajzsa kétféle lehet (folyamatos "C" vagy szegmentált), és csak bizonyos szögtartományban véd.
  - **Pontozás:** Találatért pont jár, győzelem esetén idő- és életerő bónuszt is kap a játékos.

- **Rajzolás:**  
  Minden ciklusban frissül a kijelző: játékos, ellenség, pajzs, lövedékek, életerő, ellenség életerő-csík.

- **Fő ciklus:**  
  Minden játék után megjelenik az eredmény és a pontszám, majd a gombbal lehet új játékot kezdeni.

## Működés magas szinten

1. **Indítás:**  
   A program inicializálja a hardvert, majd elindítja a fő játékmenetet.

2. **Játékos irányítása:**  
   Egyetlen gombbal lehet a játékos mozgásirányát váltani a körpályán.

3. **Játékmenet:**  
   - A játékos automatikusan lő az ellenség felé.
   - Az ellenség különböző támadási mintákat hajt végre, időnként pajzsot aktivál.
   - A lövedékek ütközéseit, találatait a program kezeli.
   - A játékos és az ellenség életereje csökken találat esetén.

4. **Győzelem/vereség:**  
   - Ha a játékos vagy az ellenség életereje elfogy, a játék véget ér.
   - Győzelem esetén idő- és életerő bónusz jár a pontszámhoz.

5. **Újraindítás:**  
   A játék végén a kijelzőn megjelenik az eredmény és a pontszám, majd a gomb lenyomásával újraindítható a játék.

## Főbb érdekességek

- A játékos mozgása és lövése teljesen automatizált, csak az irányt lehet váltani.
- Az ellenség pajzsa szögtartományban véd, így a lövedékek csak bizonyos szögekből tudnak sebezni.
- A játék MicroPython környezeten kívül is tesztelhető dummy kijelzővel/gombbal.

---

A program jól strukturált, könnyen bővíthető további támadási mintákkal, grafikai elemekkel vagy pontozási szabályokkal.