# Spyro: A Hero's Tail Archipelago
An implementation of the Archipelago randomizer for Spyro: A Hero's Tail for Playstation 2 and GameCube.

## What is randomized?

- [x] Dark Gems
- [x] Light Gems
- [x] Dragon Eggs
  - [x] Egg Thieves
- [x] Locked Chests
  - [x] Gem locked chests?
- [x] Elemental Breaths
  - [x] + Fire Breath
- [x] Elder abilities
- [x] Mini game rewards
  - [x] Toggle in YAML
- [x] Charge, Swim and Glide
- [x] Shop Items
  - [x] Lockpicks
    - [x] Region Key Rings
- [x] Light Gem door costs
- [x] Boss Lair door costs
- [x] Fireworks
- [x] Gadget Access
  - [x] Ball
  - [x] Invulnerability
  - [x] Supercharge
- [x] Realm Access Cards

## Setup Guide

##### Currently does not support PCSX2, but may change in the future.

1. Download the ``AR_Code.txt`` from https://github.com/BrinchEbsen/AHT_Archipelago
2. Download and install the apworld under the releases on this repo
3. Toggle ``Enable Cheats`` in Dolphins settings
4. Add the contents of ``AR_Code.txt`` into Dolphins cheats manager
5. Launch the game
6. Launch the client via Archipelago and connect to the multiworld (it will automatically hook into Dolphin).
7. Enjoy!

## Extra Notes

These are notes for getting the best experience on the GameCube version of
Spyro: A Hero's Tail on Dolphin.

#### Version

The latest release of Dolphin is recommended.

#### Graphics Settings

Dolphin has an issue with the game's depth-of-field effect which produces
glitchy graphics while underwater.
This issue can be fixed by disabling the settings "Store EFB Copies to Texture
Only" and "Defer EFB Copies to RAM" under Graphics->Hacks. This takes a big
toll on performance, so alternatively the effect can be disabled entirely by
enabling "Disable Fog" under Graphics->Enhancements, however this will obviously
disable the general fog effect as well.

#### Controls
For those unfamiliar with the GameCube version of the game, the button layout
is a bit weird, and might need remapping to match closer with other releases.

**A**: Jump
**X**: Charge
**Y**: Flame
**B**: Interact/Wing Shield

As there is no select button, you open the map screen by holding the **Z** button.
