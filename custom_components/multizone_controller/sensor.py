"""Support for controlling multiple media players with a single sensor."""
from __future__ import annotations
from typing import List

from homeassistant.helpers.entity_component import EntityComponent
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.components.media_player import (
    _rename_keys,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
)
from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_ICON,
    CONF_NAME,
    CONF_UNIQUE_ID,
    CONF_SOURCE,
    SERVICE_VOLUME_UP,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.reload import async_setup_reload_service

from . import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

ATTR_ACTIVE = "active"
ATTR_AVAILABLE = "available"

CONF_ZONES = "zones"
CONF_SNAP_VOLUME = "snap_volume"
CONF_VOLUME_INCREMENT = "volume_increment"
CONF_VOLUME_MAX = "volume_max"
CONF_VOLUME_MIN = "volume_min"
CONF_COMBINED = "combined"

DEFAULT_NAME = "Active Media Player"
DEFAULT_COMBINED_NAME = "All Zones"
DEFAULT_COMBINED_ICON = "mdi:speaker-multiple"
DEFAULT_ZONE_NAME = "Zone"
DEFAULT_ICON = "mdi:numeric-{}-box"
DEFAULT_ICON_9_PLUS = "9-plus"

SERVICE_VOLUME_TOGGLE_MUTE = "toggle_volume_mute"
SERVICE_NEXT_ZONE = "next_zone"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ZONES): cv.ensure_list(
            {
                vol.Required(CONF_SOURCE): cv.entity_domain(MEDIA_PLAYER_DOMAIN),
                vol.Optional(CONF_NAME): cv.string,
                vol.Optional(CONF_ICON): cv.icon,
            }
        ),
        vol.Optional(CONF_UNIQUE_ID): str,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Optional(CONF_VOLUME_MAX, default=1.0): vol.Coerce(float),
        vol.Optional(CONF_VOLUME_MIN, default=0.0): vol.Coerce(float),
        vol.Optional(CONF_VOLUME_INCREMENT, default=0.01): vol.Coerce(float),
        vol.Optional(CONF_SNAP_VOLUME, default=False): bool,
        vol.Optional(
            CONF_COMBINED,
            default={
                CONF_NAME: DEFAULT_COMBINED_NAME,
                CONF_ICON: DEFAULT_COMBINED_ICON,
            },
        ): {
            vol.Optional(CONF_NAME, default=DEFAULT_COMBINED_NAME): cv.string,
            vol.Optional(CONF_ICON, default=DEFAULT_COMBINED_ICON): cv.icon,
        },
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the multizone sensor."""

    unique_id = config.get(CONF_UNIQUE_ID)
    name = config[CONF_NAME]
    volume_min = config[CONF_VOLUME_MIN]
    volume_max = config[CONF_VOLUME_MAX]
    volume_inc = config[CONF_VOLUME_INCREMENT]
    snap = config[CONF_SNAP_VOLUME]

    zones = {}
    for i, zone in enumerate(config[CONF_ZONES]):
        n = i + 1
        zone_name = zone.get(CONF_NAME, f"{DEFAULT_ZONE_NAME} {n}")
        icon_n = str(n) if n < 10 else DEFAULT_ICON_9_PLUS
        icon = zone.get(CONF_ICON, DEFAULT_ICON.format(icon_n))
        entity_id = zone[CONF_SOURCE]

        if entity_id not in zone.keys():
            zones[entity_id] = Zone(zone_name, icon)
        else:
            _LOGGER.warn(
                "Duplicate entity_id '%s' in zone sources, ignoring", entity_id
            )

    all_zones = AllZones(
        list(zones.values()),
        config[CONF_COMBINED][CONF_NAME],
        config[CONF_COMBINED][CONF_ICON],
    )

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    async_add_entities(
        [
            MultizoneSensor(
                unique_id,
                name,
                zones,
                all_zones,
                volume_min,
                volume_max,
                volume_inc,
                snap,
            )
        ]
    )

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_NEXT_ZONE,
        {},
        "async_next_zone",
    )
    platform.async_register_entity_service(
        SERVICE_VOLUME_UP,
        {},
        "async_volume_up",
    )
    platform.async_register_entity_service(
        SERVICE_VOLUME_DOWN,
        {},
        "async_volume_down",
    )
    platform.async_register_entity_service(
        SERVICE_VOLUME_TOGGLE_MUTE,
        {},
        "async_toggle_mute_volume",
    )
    platform.async_register_entity_service(
        SERVICE_VOLUME_SET,
        vol.All(
            cv.make_entity_service_schema(
                {vol.Required(ATTR_MEDIA_VOLUME_LEVEL): cv.small_float}
            ),
            _rename_keys(volume=ATTR_MEDIA_VOLUME_LEVEL),
        ),
        "async_set_volume_level",
    )
    platform.async_register_entity_service(
        SERVICE_VOLUME_MUTE,
        vol.All(
            cv.make_entity_service_schema(
                {vol.Required(ATTR_MEDIA_VOLUME_MUTED): cv.boolean}
            ),
            _rename_keys(mute=ATTR_MEDIA_VOLUME_MUTED),
        ),
        "async_mute_volume",
    )


class MultizoneSensor(SensorEntity):
    """Representation of a multizone sensor."""

    def __init__(
        self,
        unique_id: str,
        name: str,
        zones: dict[str, Zone],
        all_zones: AllZones,
        volume_min: int,
        volume_max: int,
        volume_inc: int,
        snap: bool,
    ):
        self._unique_id = unique_id
        self._name = name
        self._zones = zones
        self._all_zones = all_zones
        self._volume_min = volume_min
        self._volume_max = volume_max
        self._volume_inc = volume_inc
        self._snap = snap
        self._all_entities = list(self._zones.keys())

        self._current = None
        self._icon = DEFAULT_ICON.format(0)
        self._state = None

    async def async_added_to_hass(self):
        """Handle added to Hass."""

        entity_ids = list(self._zones.keys())

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, entity_ids, self._async_multizone_sensor_state_listener
            )
        )

    @property
    def unique_id(self):
        """Return the unique id of this sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the sensor."""
        active = []
        available = []
        for entity_id, zone in self._zones.items():
            if zone.active:
                active.append(entity_id)
            if zone.available:
                available.append(entity_id)

        return {
            ATTR_ENTITY_ID: self._all_entities,
            ATTR_ACTIVE: active,
            ATTR_AVAILABLE: available,
        }

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

    def next_zone(self):
        """Set the next zone."""
        zones = [z for z in self._zones.values() if z.available]
        nxt = None
        if len(zones) <= 1:
            return
        elif self._current == self._all_zones:
            nxt = zones[0]
        else:
            if self._current == zones[-1] and len(self._zones) == len(zones):
                nxt = self._all_zones
            else:
                nxt = self._get_next_zone(self._current)

        nxt.set_active(True)
        if nxt == self._all_zones:
            self._set_current_zone(nxt)
            for zone in zones:
                zone.set_active(True)
        else:
            self._all_zones.set_active(False)
            self._activate_single_zone(nxt)

        self.schedule_update_ha_state()

    async def async_next_zone(self):
        """Mute the volume."""
        await self.hass.async_add_executor_job(self.next_zone)

    def mute_volume(self, mute):
        """Mute the volume."""
        self.hass.services.call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_VOLUME_MUTE,
            {ATTR_MEDIA_VOLUME_MUTED: mute},
            False,
            None,
            None,
            {ATTR_ENTITY_ID: self._get_active_zones()},
        )

    async def async_mute_volume(self, mute):
        """Mute the volume."""
        await self.hass.async_add_executor_job(self.mute_volume, mute)

    def toggle_mute_volume(self):
        """Toggle mute the volume."""
        entities = self._get_active_zones()
        is_volume_muted = any(
            [
                self.hass.states.get(entity_id).attributes[ATTR_MEDIA_VOLUME_MUTED]
                for entity_id in entities
            ]
        )

        self.hass.services.call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_VOLUME_MUTE,
            {ATTR_MEDIA_VOLUME_MUTED: not is_volume_muted},
            False,
            None,
            None,
            {ATTR_ENTITY_ID: entities},
        )

    async def async_toggle_mute_volume(self):
        """Mute the volume."""
        await self.hass.async_add_executor_job(self.toggle_mute_volume)

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self.hass.services.call(
            MEDIA_PLAYER_DOMAIN,
            SERVICE_VOLUME_SET,
            {ATTR_MEDIA_VOLUME_LEVEL: volume},
            False,
            None,
            None,
            {ATTR_ENTITY_ID: self._get_active_zones()},
        )

    async def async_set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        await self.hass.async_add_executor_job(self.set_volume_level, volume)

    def volume_up(self):
        """Turn volume up for media player."""
        volume_level = self._get_combined_volume_level()
        if volume_level is not None and volume_level < 1:
            self.set_volume_level(
                min(self._volume_max, round(volume_level + self._volume_inc, 2))
            )

    async def async_volume_up(self):
        """Turn volume up for media player."""
        await self.hass.async_add_executor_job(self.volume_up)

    def volume_down(self):
        """Turn volume down for media player."""
        volume_level = self._get_combined_volume_level()
        if volume_level is not None and volume_level > 0:
            self.set_volume_level(
                max(self._volume_min, round(volume_level - self._volume_inc, 2))
            )

    async def async_volume_down(self):
        """Turn volume down for media player."""
        await self.hass.async_add_executor_job(self.volume_down)

    @callback
    def _async_multizone_sensor_state_listener(self, event):
        """Handle media_player state changes."""
        new_state = event.data.get("new_state")
        entity = event.data.get("entity_id")
        _LOGGER.debug("New state from '%s': '%s'", entity, str(new_state))

        zone = self._zones[entity]

        if new_state.state is None:
            self._update_zones(zone, False)
            self.async_write_ha_state()
            return

        self._update_zones(zone, new_state.state == STATE_ON)
        self.async_write_ha_state()

    @callback
    def _update_zones(self, zone: Zone, value: bool):
        """Update the active zones."""

        zone.set_active_and_available(value)
        # only 1 zone can be active at a time or all zones.
        if all(
            [z.active == value and z.available == value for z in self._zones.values()]
        ):
            self._all_zones.set_active(value)

            if value:
                # ALL ON
                self._set_current_zone(self._all_zones)
            else:
                # ALL OFF
                self._set_current_zone(None)
        else:
            if value:
                # ONE ON
                self._activate_single_zone(zone)
            else:
                # NEXT ONE
                nxt = self._get_next_zone(zone)
                if nxt is not None:
                    # NEXT ONE ON
                    self._activate_single_zone(nxt)
                else:
                    # ALL OFF
                    self._set_current_zone(None)

    def _get_next_zone(self, current: Zone) -> Zone:
        """Activate the next zone."""
        ret = None
        found = False
        before = None
        after = None
        for zone in self._zones.values():
            if current == zone:
                found = True

            if current != zone and zone.available:
                if found:
                    after = zone
                    break
                elif not found and before is None:
                    before = zone

        if after is not None:
            ret = after
        elif before is not None:
            ret = before

        return ret

    def _activate_single_zone(self, zone) -> None:
        """Activate a single zone, deactivate the rest."""
        # If other zones are active, deactivate them.
        self._set_current_zone(zone)
        for z in self._zones.values():
            if z != zone and z.active and z.available:
                z.set_active(False)

    def _set_current_zone(self, zone: Zone) -> None:
        """Set the current zone."""
        self._current = zone
        if zone is None:
            self._state = STATE_OFF
            self._icon = DEFAULT_ICON.format(0)
        else:
            self._state = zone.name
            self._icon = zone.icon

    def _get_combined_volume_level(self) -> float:
        """Get the combined volume level of the media_players, if any."""
        levels = []
        for entity_id in self._get_active_zones():
            state = self.hass.states.get(entity_id)
            levels.append(state.attributes[ATTR_MEDIA_VOLUME_LEVEL])

        level = None
        if len(levels) > 0:
            divisor = 100
            level = int(round(sum(levels) / len(levels), 2) * divisor)
            if self._snap:
                level = level - level % int(self._volume_inc * divisor)
            level /= divisor
        return level

    def _get_active_zones(self) -> List[str]:
        """Return the current active zones."""
        return [e for e, z in self._zones.items() if z.active]

    def _get_available_zones(self) -> List[str]:
        """Return the current available zones."""
        return [e for e, z in self._zones.items() if z.available]


class Zone(object):
    def __init__(self, name: str, icon: str):
        self._name = name
        self._icon = icon
        self._active = False
        self._available = False

    @property
    def name(self) -> str:
        """Zone name."""
        return self._name

    @property
    def icon(self) -> str:
        """Zone icon."""
        return self._icon

    @property
    def active(self) -> bool:
        """Zone in use."""
        return self._active

    @property
    def available(self) -> bool:
        """Zone available for use."""
        return self._available

    def set_active(self, value: bool) -> None:
        """Set available."""
        self._active = value

    def set_active_and_available(self, value: bool):
        """Set active and available."""
        self.set_active(value)
        self._available = value


class AllZones(Zone):
    def __init__(self, zones: List[Zone], name: str, icon: str):
        super().__init__(name, icon)
        self._zones = zones

    @property
    def active(self) -> bool:
        """Zone in use."""
        if self.available:
            return self._active
        else:
            ret = False
            self._active = ret
            return ret

    @property
    def available(self) -> bool:
        """Zone available for use."""
        return all([z.available for z in self._zones])
