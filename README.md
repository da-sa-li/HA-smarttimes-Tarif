# smartENERGY smartTIMES – Home Assistant Integration

Eine [Home Assistant](https://www.home-assistant.io/) Integration für den
dynamischen Stromtarif **smartTIMES** des österreichischen Anbieters
[smartENERGY](https://www.smartenergy.at/). Sie ruft die öffentliche
smartTIMES-Preis-API ab und stellt die viertelstündlichen Tarifpreise als
Sensoren bereit – ideal, um Verbraucher automatisch in günstige Tarifzonen zu
verschieben.

> Diese Integration ist ein inoffizielles Community-Projekt und steht in keiner
> Verbindung zur smartENERGY GmbH.

## Funktionen

- 🔌 **Aktueller Strompreis** der laufenden 15-Minuten-Tarifzone
- 🚦 **Tarifzone** (Off-Peak / Shoulder / Peak) als eigener Status-Sensor
- 📊 **Tageskennzahlen**: Durchschnitts-, Niedrigst- und Höchstpreis von heute
- 💰 **Grundgebühr** (Monatspauschale) als eigener Sensor
- 🗓️ **Vollständige Preisvorschau** für heute und morgen als Attribute
  (z. B. für Diagramme oder Automatisierungen)
- 💶 Umschaltbar zwischen **Brutto** (inkl. 20 % USt.) und **Netto**
- ⚙️ Komplette Einrichtung über die **Benutzeroberfläche** (kein YAML, kein API-Schlüssel)

## Datenquelle

Die Integration verwendet die öffentliche smartTIMES-API:

```
https://apis.smartenergy.at/tariffs/v1/Tariffs/smartTIMES/prices
```

Die API liefert pro Zeitintervall (i. d. R. 15 Minuten) den gültigen
Tarifpreis sowie die monatliche Grundgebühr. Die Antwort ist wie folgt
aufgebaut:

```json
{
  "energyPrice": {
    "interval": 15,
    "unit": "cent/kWh",
    "values": [
      { "dateTimeFrom": "2026-05-29T00:00:00+02:00", "value": 11.244 },
      { "dateTimeFrom": "2026-05-29T00:15:00+02:00", "value": 11.244 }
    ]
  },
  "basicFee": {
    "unit": "EUR/month",
    "values": [
      { "dateTimeFrom": "2026-05-29T00:00:00+02:00", "value": 2.988 }
    ]
  }
}
```

| Feld                       | Bedeutung                                          |
|----------------------------|----------------------------------------------------|
| `energyPrice.unit`         | Einheit des Energiepreises (z. B. `cent/kWh`)      |
| `energyPrice.interval`     | Gültigkeit des Preises in Minuten                  |
| `…values[].dateTimeFrom`   | Preis gültig ab (lokale Datum/Uhrzeit, mit Offset) |
| `…values[].value`          | Preis **inkl. 20 % MwSt.** (dezimal)               |
| `basicFee`                 | Monatliche Grundgebühr (z. B. `EUR/month`)         |

> Hinweis: Die Integration unterstützt zusätzlich das ältere, in der
> Dokumentation gezeigte Format (`data` / `date`) als Fallback. Da die API
> lokale Zeitstempel liefert, sollte die Zeitzone in Home Assistant korrekt
> auf `Europe/Vienna` eingestellt sein.

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → oben rechts auf die drei Punkte → **Benutzerdefinierte Repositories**.
2. Repository-URL dieses Projekts eintragen, Kategorie **Integration** wählen und hinzufügen.
3. Die Integration **smartENERGY smartTIMES** suchen, herunterladen und Home Assistant neu starten.

### Manuell

1. Den Ordner `custom_components/smartenergy_smarttimes` in das
   `custom_components`-Verzeichnis deiner Home-Assistant-Konfiguration kopieren.
2. Home Assistant neu starten.

## Einrichtung

1. **Einstellungen → Geräte & Dienste → Integration hinzufügen** öffnen.
2. Nach **smartENERGY smartTIMES** suchen.
3. Auswählen, ob die Preise inkl. USt. (brutto) angezeigt werden sollen.

Die Brutto-/Netto-Einstellung lässt sich später jederzeit über
**Konfigurieren** bei der Integration ändern.

## Sensoren

| Sensor                                          | Beschreibung                                |
|-------------------------------------------------|---------------------------------------------|
| `sensor.smartenergy_smarttimes_aktueller_preis` | Preis der aktuell gültigen Tarifzone        |
| `sensor.smartenergy_smarttimes_durchschnittspreis_heute` | Durchschnittspreis des heutigen Tages |
| `sensor.smartenergy_smarttimes_niedrigster_preis_heute`  | Günstigster Preis heute              |
| `sensor.smartenergy_smarttimes_hochster_preis_heute`     | Teuerster Preis heute                |
| `sensor.smartenergy_smarttimes_grundgebuhr`              | Monatliche Grundgebühr (EUR/Monat)   |
| `sensor.smartenergy_smarttimes_tarifzone`               | Aktuelle Tarifzone (Off-Peak/Shoulder/Peak) |

Die Preissensoren verwenden die Einheit **ct/kWh**, der Grundgebühr-Sensor
**EUR/Monat**.

### Sensor „Tarifzone"

smartTIMES teilt den Tag in feste Preisstufen ein. Der Sensor leitet die
aktuelle Zone direkt aus den Preisen ab: der **niedrigste** Preis ist
`off_peak`, der **höchste** `peak`, dazwischenliegende Preise `shoulder`.

Als Zustand liefert der Sensor die stabilen Werte `off_peak`, `shoulder` bzw.
`peak` (gut für Automatisierungen); in der Oberfläche werden sie als
*Off-Peak*, *Shoulder* und *Peak* angezeigt. Zusätzliche Attribute:

| Attribut            | Beschreibung                                              |
|---------------------|-----------------------------------------------------------|
| `level_prices`      | Preis je Zone, z. B. `{off_peak: 9.77, shoulder: 11.24, peak: 13.68}` |
| `next_status`       | Nächste abweichende Tarifzone                             |
| `next_status_start` | Zeitpunkt, ab dem die nächste Zone gilt                   |
| `vat_included`      | `true`, wenn die Preise brutto sind                       |

```yaml
automation:
  - alias: "Waschmaschine nur in Off-Peak starten"
    trigger:
      - platform: state
        entity_id: sensor.smartenergy_smarttimes_tarifzone
        to: "off_peak"
    action:
      - action: switch.turn_on
        target:
          entity_id: switch.waschmaschine
```

> Die genauen Entity-IDs können je nach Spracheinstellung abweichen.

### Attribute des Sensors „Aktueller Preis“

Der Sensor `Aktueller Preis` enthält zusätzlich umfangreiche Attribute:

| Attribut            | Beschreibung                                              |
|---------------------|-----------------------------------------------------------|
| `tariff`            | Tarifname laut API                                        |
| `unit`              | Einheit der Preise                                        |
| `interval_minutes`  | Länge einer Tarifzone in Minuten                          |
| `vat_included`      | `true`, wenn die Preise brutto (inkl. USt.) sind          |
| `current_start` / `current_end` | Beginn/Ende der aktuellen Tarifzone           |
| `next_price`        | Preis der nächsten Tarifzone                              |
| `next_price_start`  | Beginn der nächsten Tarifzone                             |
| `average_today` / `lowest_today` / `highest_today` | Tageskennzahlen           |
| `basic_fee` / `basic_fee_unit` | Aktuelle Grundgebühr und deren Einheit        |
| `prices_today`      | Liste aller heutigen Preise (`start`, `end`, `price`)     |
| `prices_tomorrow`   | Liste aller morgigen Preise (sofern verfügbar)            |
| `prices`            | Vollständige Preisliste (gut für Diagramme)               |

## Beispiele

### Automatisierung: Gerät bei günstigem Preis einschalten

```yaml
automation:
  - alias: "Boiler bei günstigem Strom einschalten"
    trigger:
      - platform: numeric_state
        entity_id: sensor.smartenergy_smarttimes_aktueller_preis
        below: 10            # ct/kWh
    action:
      - action: switch.turn_on
        target:
          entity_id: switch.boiler
```

### Diagramm mit ApexCharts Card

Mit der [ApexCharts Card](https://github.com/RomRider/apexcharts-card) lässt sich
der Preisverlauf darstellen:

```yaml
type: custom:apexcharts-card
header:
  title: smartTIMES Preise
  show: true
series:
  - entity: sensor.smartenergy_smarttimes_aktueller_preis
    name: Preis
    type: column
    data_generator: |
      return entity.attributes.prices.map(p => {
        return [new Date(p.start).getTime(), p.price];
      });
```

## Hinweise

- Die smartTIMES-API gibt die Preise für den nächsten Tag typischerweise am
  Nachmittag bekannt. Vorher bleibt `prices_tomorrow` leer.
- Die API wird höchstens alle 30 Minuten abgefragt; der Sensorwert für den
  aktuellen Preis wird dennoch minütlich neu berechnet, damit der Wechsel der
  Tarifzone sofort korrekt angezeigt wird.

## Lizenz

Siehe [LICENSE](LICENSE).
