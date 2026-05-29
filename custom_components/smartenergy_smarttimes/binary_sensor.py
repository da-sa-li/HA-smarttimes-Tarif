"""Binary-Sensor „Günstige Stunde" für die smartTIMES Integration.

Markiert, ob das aktuelle Intervall zu den günstigsten Stunden des Tages zählt –
gemessen an den **gesamten variablen Kosten** (Arbeitspreis + Abgaben +
Netzentgelte inkl. SNAP). Ideal, um z. B. einen Elektroboiler genau dann laufen
zu lassen, wenn der Strom insgesamt am günstigsten ist.
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SmartTimesConfigEntry
from .const import DOMAIN, UNIT_CT_PER_KWH
from .coordinator import SmartTimesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTimesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richtet den „Günstige Stunde"-Binary-Sensor ein."""
    coordinator = entry.runtime_data
    async_add_entities([CheapHourBinarySensor(coordinator, entry)])


class CheapHourBinarySensor(
    CoordinatorEntity[SmartTimesCoordinator], BinarySensorEntity
):
    """`on`, wenn die laufende Viertelstunde zu den günstigsten des Tages zählt."""

    _attr_has_entity_name = True
    _attr_translation_key = "cheap_hour"
    _attr_icon = "mdi:cash-clock"

    def __init__(
        self,
        coordinator: SmartTimesCoordinator,
        entry: SmartTimesConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_cheap_hour"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="smartENERGY smartTIMES",
            manufacturer="smartENERGY",
            model="smartTIMES",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.smartenergy.at/api-schnittstellen-smarttimes",
        )

    @property
    def is_on(self) -> bool | None:
        """Ob das aktuelle Intervall günstig ist."""
        data = self.coordinator.data
        price = data.current()
        if price is None:
            return None
        return data.is_cheap(price)

    @property
    def extra_state_attributes(self) -> dict:
        """Schwellwert, günstige Intervalle und nächster günstiger Start."""
        data = self.coordinator.data
        now = dt_util.now()
        today = now.date()
        price = data.current()
        cheap = data.cheap_intervals(today)
        upcoming = [p for p in cheap if p.start > now]
        next_cheap = upcoming[0] if upcoming else None

        def current_price() -> StateType:
            return data.all_in_value(price) if price else None

        return {
            "cheap_hours": data.cheap_hours,
            "threshold_ct_kwh": data.cheap_cutoff(today),
            "current_price_ct_kwh": current_price(),
            "unit_ct": UNIT_CT_PER_KWH,
            "vat_included": data.include_vat,
            "next_cheap_start": (
                next_cheap.start.isoformat() if next_cheap else None
            ),
            "cheap_intervals": [
                {
                    "start": p.start.isoformat(),
                    "end": p.end.isoformat(),
                    "price": data.all_in_value(p),
                }
                for p in cheap
            ],
        }
