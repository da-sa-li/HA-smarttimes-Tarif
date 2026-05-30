"""Binary-Sensoren „Günstige Stunde" für die smartTIMES Integration.

Jeder Sensor markiert, ob das aktuelle Intervall zu den günstigsten Stunden des
Tages zählt – gemessen an den **gesamten variablen Kosten** (Arbeitspreis +
Abgaben + Netzentgelte inkl. SNAP). Die Anzahl günstiger Stunden wird je
Untereintrag (Config Subentry) festgelegt, sodass pro Verbraucher ein eigener
Sensor mit eigener Stundenzahl möglich ist (z. B. Boiler 4 h, Wallbox 8 h).
"""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SmartTimesConfigEntry
from .const import CONF_CHEAP_HOURS, DOMAIN, SUBENTRY_TYPE_CHEAP_HOUR, UNIT_CT_PER_KWH
from .coordinator import SmartTimesCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTimesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Richtet je Untereintrag einen „Günstige Stunde"-Binary-Sensor ein."""
    coordinator = entry.runtime_data
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_CHEAP_HOUR:
            continue
        async_add_entities(
            [CheapHourBinarySensor(coordinator, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


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
        subentry: ConfigSubentry,
    ) -> None:
        super().__init__(coordinator)
        self._cheap_hours: float = subentry.data[CONF_CHEAP_HOURS]
        self._attr_unique_id = f"{subentry.subentry_id}_cheap_hour"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer="smartENERGY",
            model="smartTIMES Günstige Stunde",
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
        return data.is_cheap(price, self._cheap_hours)

    @property
    def extra_state_attributes(self) -> dict:
        """Schwellwert, günstige Intervalle und nächster günstiger Start."""
        data = self.coordinator.data
        now = dt_util.now()
        today = now.date()
        price = data.current()
        cheap = data.cheap_intervals(today, self._cheap_hours)
        upcoming = [p for p in cheap if p.start > now]
        next_cheap = upcoming[0] if upcoming else None

        def current_price() -> StateType:
            return data.all_in_value(price) if price else None

        return {
            "cheap_hours": self._cheap_hours,
            "threshold_ct_kwh": data.cheap_cutoff(today, self._cheap_hours),
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
