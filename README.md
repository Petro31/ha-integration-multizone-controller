# ha-multizone-controller

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
<br><a href="https://www.buymeacoffee.com/Petro31" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-black.png" width="150px" height="35px" alt="Buy Me A Coffee" style="height: 35px !important;width: 150px !important;" ></a>


This creates a sensor that represents the current media_player zone that is under control.

e.g. You have a reciever with 3 zones.  When brought into Home Assistant, you get 3 separate Zones.  You'd like to turn the volume up for all the zones that are on, or optionally just turn on one.

* The created sensors current state will represent which zones are on.  e.g. `All Zones`, `Zone 1`, `Zone 2`, `Zone 1`, `Zone 1,2`, `off`.
* The sensor will contain a list of available media_players (All players that are currently on).
* The sensor will contain a list of active media_players (All players that will be affected by the events).

<h1><a class="title-link" name="installation" href="#installation"></a>Installation</h1>

* Install using HACS, or copy the contents of `custom_components/multizone_controller/` to `<config>/custom_components/multizone_controller/`
* Restart Home Assistant

<h1><a class="title-link" name="configuration" href="#configuration"></a>Configuration</h1>

<h3><a class="title-link" name="basic" href="#basic"></a>Basic</h3>

```
sensor:
  - platform: multizone_controller
    zones:
      - source: media_player.yamaha_receiver
      - source: media_player.yamaha_receiver_zone_2
```

<h3><a class="title-link" name="advanced" href="#advanced"></a>Advanced</h3>

```
sensor:
  - platform: multizone_controller
    zones:
      - source: media_player.yamaha_receiver
      - source: media_player.yamaha_receiver_zone_2
    snap_volume: true
    volume_increment: 0.05
    volume_max: 1.0
    volume_min: 0.2
```

<h3><a class="title-link" name="options" href="#options"></a>Options</h3>

<p>
<span style="color:#222222bd; font-weight: bold; font-size: 16px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>zones</span>
<span style="color:#8792a2; font-size: 13px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>list</span>
<span style="color:#e56f4a; font-size: 11px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>REQUIRED</span>
</p>
<p style="color:#4f566b; font-size: 14px;";>list of media_player entity_ids.</p>

<p>
<span style="color:#222222bd; font-weight: bold; font-size: 16px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>name</span>
<span style="color:#8792a2; font-size: 13px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>str (optional, default: Active Media Player)</span>
</p>
<p style="color:#4f566b; font-size: 14px;";>Friendly name of the Sensor.</p>

<p>
<span style="color:#222222bd; font-weight: bold; font-size: 16px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>volume_max</span>
<span style="color:#8792a2; font-size: 13px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>float (optional, default: 1.0)</span>
</p>
<p style="color:#4f566b; font-size: 14px;";>A maximum volume that the controller can go to.</p>

<p>
<span style="color:#222222bd; font-weight: bold; font-size: 16px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>volume_min</span>
<span style="color:#8792a2; font-size: 13px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>float (optional, default: 0.0)</span>
</p>
<p style="color:#4f566b; font-size: 14px;";>A minimum volume that the controller can go to.</p>

<p>
<span style="color:#222222bd; font-weight: bold; font-size: 16px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>volume_increment</span>
<span style="color:#8792a2; font-size: 13px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>float (optional, default: 0.01)</span>
</p>
<p style="color:#4f566b; font-size: 14px;";>The amount of volume that moves up and down when a volume_up/down service is used.</p>

<p>
<span style="color:#222222bd; font-weight: bold; font-size: 16px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>snap_volume</span>
<span style="color:#8792a2; font-size: 13px; font-family: "Helvetica Neue",Helvetica,Arial,sans-serif;";>bool (optional, default: false)</span>
</p>
<p style="color:#4f566b; font-size: 14px;";>When this is active, the volume will snap to the volume increment.  Meaning if you have an increment of 0.5, the volume will only increase to all numerical values that are devisible by 0.05.  I.e. 0.0, 0.05, 0.10, 0.15, etc.</p>

<h1><a class="title-link" name="services" href="#services"></a>Services</h1>

<h3><a class="title-link" name="next_zone" href="#next_zone"></a>multizone_controller.next_zone</h3>

<p style="color:#4f566b; font-size: 14px;";>Cycle through available media_player zones.</p>

Service data attribute | Optional | Description
-- | -- | --
`entity_id` | yes | Target a specific mutlizone controller sensor.

<h3><a class="title-link" name="volume_up" href="#volume_up"></a>multizone_controller.volume_up</h3>

<p style="color:#4f566b; font-size: 14px;";>Turn a zone volume up.</p>

Service data attribute | Optional | Description
-- | -- | --
`entity_id` | yes | Target a specific mutlizone controller sensor.

<h3><a class="title-link" name="volume_down" href="#volume_down"></a>multizone_controller.volume_down</h3>

<p style="color:#4f566b; font-size: 14px;";>Turn a zone volume down.</p>

Service data attribute | Optional | Description
-- | -- | --
`entity_id` | yes | Target a specific mutlizone controller sensor.

<h3><a class="title-link" name="toggle_volume_mute" href="#toggle_volume_mute"></a>multizone_controller.toggle_volume_mute</h3>

<p style="color:#4f566b; font-size: 14px;";>Toggle to mute/unmute a zone's volume.</p>

Service data attribute | Optional | Description
-- | -- | --
`entity_id` | yes | Target a specific mutlizone controller sensor.

<h3><a class="title-link" name="volume_mute" href="#volume_mute"></a>multizone_controller.volume_mute</h3>

<p style="color:#4f566b; font-size: 14px;";>Toggle to mute/unmute a zone's volume.</p>

Service data attribute | Optional | Description
-- | -- | --
`entity_id` | yes | Target a specific mutlizone controller sensor.
`is_volume_muted` | no | True/false for mute/unmute

<h3><a class="title-link" name="volume_set" href="#volume_set"></a>multizone_controller.volume_set</h3>

<p style="color:#4f566b; font-size: 14px;";>Set a zone's volume level.</p>

Service data attribute | Optional | Description
-- | -- | --
`entity_id` | yes | Target a specific mutlizone controller sensor.
`is_volume_muted` | no | Float for volume level. Range 0..1