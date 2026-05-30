"""Deterministischer Zeit-Jitter für die „Günstige Stunde"-Sensoren.

Damit nicht hunderte Verbraucher exakt zur selben Sekunde (z. B. 10:00:00)
gleichzeitig eine große Last schalten und so eine Lastspitze im Stromnetz
erzeugen, verschiebt jeder Sensor seine Schaltflanken um einen kleinen,
zufällig *wirkenden* Betrag.

Der Versatz ist **deterministisch** aus der – vom Nutzer nicht editierbaren –
Subentry-ID abgeleitet. Das hat gegenüber einer bei jeder Flanke neu gezogenen
Zufallszahl mehrere Vorteile:

* **Stabil bei jeder Neuberechnung.** Der Binary-Sensor wird minütlich neu
  ausgewertet; eine bei jedem Aufruf frisch gezogene Zufallszahl würde die
  Schaltschwelle ständig verschieben und den Sensor flackern lassen.
* **Transparent/reproduzierbar.** Bei bekannter Sensor-ID lässt sich der
  Versatz jederzeit nachrechnen – makroskopisch zufällig, mikroskopisch
  nachvollziehbar.
* **Gleichverteilt über viele Sensoren.** SHA-256 streut die IDs gleichmäßig,
  sodass sich die aggregierte Last über die Nutzer hinweg glättet.

Wichtig: Diese Funktionen wirken ausschließlich auf den „Günstige Stunde"-
Binary-Sensor. Sie verändern weder die Preis-Sensoren noch die zugrunde
liegenden Preisdaten.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

from .const import JITTER_OFF_SPAN_SECONDS, JITTER_ON_MAX_SECONDS


def cheap_phase(seed: str) -> float:
    """Stabiler Pseudo-Zufallswert in ``[0, 1)`` aus ``seed``.

    Es werden die ersten 8 Bytes eines SHA-256-Hashes als 64-Bit-Zahl
    interpretiert und auf ``[0, 1)`` normiert. Gleiche ``seed`` ergeben immer
    denselben Wert; unterschiedliche IDs sind nahezu gleichverteilt.
    """
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big")
    return value / 2 ** 64


def jittered_window(
    start: datetime, end: datetime, phase: float
) -> tuple[datetime, datetime]:
    """Verschobenes Ein-/Ausschaltfenster eines zusammenhängenden Günstig-Blocks.

    ``start``/``end`` sind die Grenzen eines (bereits zusammengefassten)
    durchgehenden günstigen Blocks; ``phase`` ist der sensoreigene Wert aus
    :func:`cheap_phase`.

    * **Einschalten:** Verzögerung ``phase * JITTER_ON_MAX_SECONDS`` →
      gleichverteilt in ``[0, JITTER_ON_MAX_SECONDS]``. Es wird **nie vor**
      Beginn des günstigen Blocks eingeschaltet (sonst liefe der Verbraucher in
      die noch teure Zeit hinein).
    * **Ausschalten:** Versatz ``(phase - 0.5) * JITTER_OFF_SPAN_SECONDS`` →
      symmetrisch um die Blockgrenze. Der Erwartungswert fällt damit genau auf
      die Grenze (volle Stunde).

    Da für beide Flanken **dieselbe** ``phase`` verwendet wird, verschiebt sich
    das Fenster als Ganzes: Seine Länge verkürzt sich für *jeden* Sensor um
    konstant ``JITTER_OFF_SPAN_SECONDS / 2`` Sekunden, unabhängig von ``phase``.
    Ein durchgehender Block wird so nie zerteilt und – solange er länger als
    dieser feste Betrag ist – auch nie ausgelöscht. Bei der kleinsten möglichen
    Blocklänge (ein 15-Minuten-Intervall) bleiben damit 10 min Einschaltzeit.
    """
    on_time = start + timedelta(seconds=phase * JITTER_ON_MAX_SECONDS)
    off_time = end + timedelta(seconds=(phase - 0.5) * JITTER_OFF_SPAN_SECONDS)
    # Sicherheitsnetz für (hier nicht vorkommende) extrem kurze Blöcke: das
    # Fenster darf nie leer oder negativ werden.
    if off_time < on_time:
        off_time = on_time
    return on_time, off_time
