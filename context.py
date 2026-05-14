from __future__ import annotations

import asyncio
import collections
from typing import Any

import Utils
from kvui import GameManager

from CommonClient import ClientCommandProcessor, CommonContext, logger
from NetUtils import ClientStatus, NetworkItem

from .client import GenericClient, DolphinClient
from .data import consts


class SpyroAHTCommands(ClientCommandProcessor):
    ctx: SpyroAHTContext
    
    async def _cmd_reset_client(self) -> bool:
        """Forcibly reconnect the client."""
        self.output("Resetting client...")
        if self.ctx.emu_client:
            self.ctx.emu_loop.cancel()
            await self.ctx.emu_client.disconnect()
        self.ctx.emu_loop = asyncio.create_task(self.ctx._emu_loop())
        return True

    async def _cmd_debug_send(self, location: str) -> bool:
        await self.ctx.send_msgs([{"cmd": "LocationChecks","locations":[int(location)]}])
        return True


class SpyroAHTContext(CommonContext):
    items_handling = 0b111
    game = "Spyro: A Hero's Tail"
    command_processor = SpyroAHTCommands

    def __init__(self, server_address: str | None = None, password: str | None = None) -> None:
        super().__init__(server_address, password)

        self.emu_client: GenericClient = None # type: ignore
        self.emu_loop: asyncio.Task = None # type: ignore
        self.auth_ready = asyncio.Event()

        self.slot_data = {}
        self._seed = ""

        self._shop_items: list[NetworkItem] = []
        self._shop_items_received = asyncio.Event()

        self._handled_items: set[NetworkItem] = set()

        self._checked_boss_doors = set()
        self._checked_gem_doors = set()
        self._checked_gadgets = set()

        self._scouted_locations: set[int] = set()
    
    def make_gui(self) -> type[GameManager]:
        ui = super().make_gui()
        ui.base_title = "Spyro: A Hero's Tail Archipelago Client"
        return ui

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect(game=self.game)
    
    def on_package(self, cmd: str, args: dict):
        match cmd:
            case 'Connected':
                self.slot_data = args['slot_data']
                if self.slot_data['death_link'] != 0:
                    self.tags.add("DeathLink")
                    Utils.async_start(self.send_msgs([{"cmd": "ConnectUpdate", "tags": self.tags}]))
                if self.emu_loop and not self.emu_loop.cancelled():
                    self.emu_loop.cancel()
                self.emu_loop = asyncio.create_task(self._emu_loop())
                self.auth_ready.set()
            case 'RoomInfo':
                self._seed = args['seed_name']
            case 'LocationInfo':
                if not self._shop_items_received.is_set():
                    self._shop_items = [NetworkItem(*item) for item in args['locations']]
                    self._shop_items_received.set()
            case 'PrintJSON':
                match args.get('type', ''):
                    case 'ItemSend':
                        if args['receiving'] == self.slot:
                            item = args['item']
                            self.emu_client.msg_queue.put_nowait((consts.COLOUR_WHITE, f'Received {self.item_names.lookup_in_slot(item.item, self.slot)} from {self.player_names[item.player]}'))
                    case 'Hint':
                        if args['found']: return
                        if args['receiving'] == self.slot:
                            item = args['item']
                            player = "your" if item.player == self.slot else f"{self.player_names[item.player]}'s"
                            location = self.location_names.lookup_in_slot(item.location, item.player)
                            msg = f"[Hint] Your {self.item_names.lookup_in_slot(item.item, self.slot)} is at {player} {location}"
                            self.emu_client.msg_queue.put_nowait((consts.COLOUR_WHITE, msg))
                        elif args['item'].player == self.slot:
                            item = args['item']
                            location = self.location_names.lookup_in_slot(item.location, self.slot)
                            player = self.player_names[args['receiving']]
                            msg = f"[Hint] {player}'s {self.item_names.lookup_in_slot(item.item, args['receiving'])} is at {location}"
                            self.emu_client.msg_queue.put_nowait((consts.COLOUR_WHITE, msg))
    
    async def start_emu_client(self):
        # TODO: pcsx2 client
        self.emu_client = DolphinClient()
        await self.emu_client.connect()
        await self.emu_client.apply_patch(self)
        await self.emu_client.ready.wait()
    
    async def _receive_items(self):
        item_counts = collections.Counter(self.item_names.lookup_in_slot(i.item, self.slot) for i in self.items_received)
        updated = False
        for item in self.items_received:
            if item in self._handled_items: continue
            self._handled_items.add(item)
            match item.item:
                case 0xB:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.Swim, True)
                    updated = True
                case 0xC:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.Glide, True)
                    updated = True
                case 0xD:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.Charge, True)
                    updated = True
                case 0x1:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.DoubleJump, True)
                    updated = True
                case 0x2:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.PoleSpin, True)
                    updated = True
                case 0x3:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.WingShield, True)
                    updated = True
                case 0x4:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.WallKick, True)
                    updated = True
                case 0xE:
                    if not await self.emu_client.has_any_breath():
                        await self.emu_client.set_breath(consts.BREATH_FIRE)
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.FireBreath, True)
                    updated = True
                case 0x5:
                    if not await self.emu_client.has_any_breath():
                        await self.emu_client.set_breath(consts.BREATH_ELECTRIC)
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.ElectricBreath, True)
                    updated = True
                case 0x6:
                    if not await self.emu_client.has_any_breath():
                        await self.emu_client.set_breath(consts.BREATH_WATER)
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.WaterBreath, True)
                    updated = True
                case 0x7:
                    if not await self.emu_client.has_any_breath():
                        await self.emu_client.set_breath(consts.BREATH_ICE)
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.IceBreath, True)
                    updated = True
                case 0x8:
                    count = await self.emu_client.get_item_count(self.emu_client.addresses.DARK_GEM_COUNT)
                    if count < item_counts["Dark Gem"]:
                        await self.emu_client.set_item(self.emu_client.addresses.DARK_GEM_COUNT, count + 1)
                        updated = True
                case 0x9:
                    count = await self.emu_client.get_item_count(self.emu_client.addresses.LIGHT_GEM_COUNT)
                    if count < item_counts["Light Gem"]:
                        await self.emu_client.set_item(self.emu_client.addresses.LIGHT_GEM_COUNT, count + 1)
                        updated = True
                case 0xA:
                    count = await self.emu_client.get_item_count(self.emu_client.addresses.DRAGON_EGG_COUNT)
                    if count < item_counts["Dragon Egg"]:
                        await self.emu_client.set_item(self.emu_client.addresses.DRAGON_EGG_COUNT, count + 1)
                case 0x1C:
                    count = await self.emu_client.get_item_count(self.emu_client.addresses.g_NUM_LOCK_PICKS_RECEIVED)
                    if count < item_counts["Lockpick"]:
                        lc = await self.emu_client.get_item_count(self.emu_client.addresses.LOCKPICKS)
                        await self.emu_client.set_item(self.emu_client.addresses.g_NUM_LOCK_PICKS_RECEIVED, count + 1)
                        await self.emu_client.set_item(self.emu_client.addresses.LOCKPICKS, lc + 1)
                        updated = True
                case 0xF:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.SparxHealthUpgrade, True)
                case 0x19:
                    await self.emu_client.enable_butterfly_jar()
                case 0x1A:
                    #await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.DoubleGems, True)
                    await self.emu_client.toggle_double_gems(True)
                case 0x1B:
                    await self.emu_client.set_flag(self.emu_client.addresses.ABILITY_FLAGS, consts.AbilityFlags.Shockwave, True)
                case 0x1D:
                    count = await self.emu_client.get_item_count(self.emu_client.addresses.g_NUM_GEM_PACKS_RECEIVED)
                    if count < item_counts["Gem Pack"]:
                        await self.emu_client.set_item(self.emu_client.addresses.g_NUM_GEM_PACKS_RECEIVED, count + 1)
                        await self.emu_client.add_gem_pack()
                case 0x1E:
                    total = await self.emu_client.get_item_count(self.emu_client.addresses.g_NUM_FIRE_AMMO_RECEIVED)
                    if total < item_counts["Fire Bomb"]:
                        count = await self.emu_client.get_item_count(self.emu_client.addresses.FIRE_BOMBS)
                        await self.emu_client.set_item(self.emu_client.addresses.g_NUM_FIRE_AMMO_RECEIVED, total + 1)
                        await self.emu_client.set_item(self.emu_client.addresses.FIRE_BOMBS, count + 1)
                case 0x1F:
                    total = await self.emu_client.get_item_count(self.emu_client.addresses.g_NUM_ELECTRIC_AMMO_RECEIVED)
                    if total < item_counts["Electric Bomb"]:
                        count = await self.emu_client.get_item_count(self.emu_client.addresses.ELECTRIC_BOMBS)
                        await self.emu_client.set_item(self.emu_client.addresses.g_NUM_ELECTRIC_AMMO_RECEIVED, total + 1)
                        await self.emu_client.set_item(self.emu_client.addresses.ELECTRIC_BOMBS, count + 1)
                case 0x20:
                    total = await self.emu_client.get_item_count(self.emu_client.addresses.g_NUM_WATER_AMMO_RECEIVED)
                    if total < item_counts["Water Bomb"]:
                        count = await self.emu_client.get_item_count(self.emu_client.addresses.WATER_BOMBS)
                        await self.emu_client.set_item(self.emu_client.addresses.g_NUM_WATER_AMMO_RECEIVED, total + 1)
                        await self.emu_client.set_item(self.emu_client.addresses.WATER_BOMBS, count + 1)
                case 0x21:
                    total = await self.emu_client.get_item_count(self.emu_client.addresses.g_NUM_ICE_AMMO_RECEIVED)
                    if total < item_counts["Ice Bomb"]:
                        count = await self.emu_client.get_item_count(self.emu_client.addresses.ICE_BOMBS)
                        await self.emu_client.set_item(self.emu_client.addresses.g_NUM_ICE_AMMO_RECEIVED, total + 1)
                        await self.emu_client.set_item(self.emu_client.addresses.ICE_BOMBS, count + 1)
                case 0x22 | 0x23 | 0x24 | 0x25 | 0x26 | 0x27 | 0x28 | 0x29 | 0x2A | 0x2B | 0x2C | 0x2D | 0x2E | 0x2F:
                    bit = consts.KEY_RINGS.index(item.item)
                    address = self.emu_client.addresses.g_KEYRING_BITFIELD + (bit // 8)
                    data = await self.emu_client.get_item_count(address)
                    flag = 1 << (bit % 8)
                    data |= flag
                    await self.emu_client.set_item(address, data)
                    updated = True
                case 0x30 | 0x31 | 0x32 | 0x33: # access cards
                    await self.emu_client.allow_realm_access(item.item)
                    updated = True
        if updated:
            await self.emu_client.update_tracker(self, item_counts)

    async def _check_doors(self):
        dark = await self.emu_client.get_item_count(self.emu_client.addresses.DARK_GEM_COUNT)
        for idx, cost in enumerate(self.slot_data['boss_lair_costs']):
            if idx in self._checked_boss_doors: continue
            if dark >= cost:
                self._checked_boss_doors.add(idx)
                msg = consts.COLOUR_RED, "SOMETHING WENT WRONG"
                match idx:
                    case 0:
                        msg = consts.COLOUR_WHITE, "You can now access Gnasty's Lair!"
                    case 1:
                        msg = consts.COLOUR_WHITE, "You can now access Ineptune's Lair!"
                    case 2:
                        msg = consts.COLOUR_WHITE, "You can now access Red's Lair!"
                    case 3:
                        msg = consts.COLOUR_WHITE, "You can now access Mecha-Red's Lair!"
                self.emu_client.msg_queue.put_nowait(msg)
        
        light = await self.emu_client.get_item_count(self.emu_client.addresses.LIGHT_GEM_COUNT)
        for idx, cost in enumerate(self.slot_data['light_gem_door_costs']):
            if idx in self._checked_gem_doors: continue
            if light >= cost:
                self._checked_gem_doors.add(idx)
                msg = consts.COLOUR_RED, "SOMETHING WENT WRONG"
                match idx:
                    case 0:
                        msg = consts.COLOUR_WHITE, "You can now access the Light Gem door in Dragonfly Falls!"
                    case 1:
                        msg = consts.COLOUR_WHITE, "You can now access the Light Gem door in Coastal Remains!"
                    case 2:
                        msg = consts.COLOUR_WHITE, "You can now access the Light Gem door in Frostbite Village!"
                    case 3:
                        msg = consts.COLOUR_WHITE, "You can now access the Light Gem door in Dark Mine!"
                self.emu_client.msg_queue.put_nowait(msg)
        
        for idx, cost in enumerate(self.slot_data['randomize_gadget_costs']):
            if idx in self._checked_gadgets: continue
            if light >= cost:
                self._checked_gadgets.add(idx)
                msg = consts.COLOUR_RED, "SOMETHING WENT WRONG"
                match idx:
                    case 0:
                        msg = consts.COLOUR_WHITE, "You can now access the Ball Gadget!"
                    case 1:
                        msg = consts.COLOUR_WHITE, "You can now access the Invincibility Gadget!"
                    case 2:
                        msg = consts.COLOUR_WHITE, "You can now access the Supercharge Gadget!"
                self.emu_client.msg_queue.put_nowait(msg)

    async def _location_checks(self):
        locations = await self.emu_client.scan_locations(shop_items=self.slot_data['randomize_shop_items'] == 1, key_rings=self.slot_data['key_rings'] == 1)
        for c in {229, 230, 231, 232, 999}:
            locations.add(c)
        locations -= self.checked_locations
        if locations:
            await self.send_msgs([{"cmd": "LocationChecks", "locations": locations}])
    
    async def _location_scouts(self):
        locations = set()
        if self.slot_data['misc_hint_minigame_rewards']:
            for obj, loc in consts.MINIGAME_OBJECTIVES.items():
                flag = await self.emu_client.get_objective(obj)
                if flag:
                    locations.update(loc)
        
        if self.slot_data['misc_hint_boss_rewards']:
            for obj, loc in consts.BOSS_OBJECTIVES.items():
                flag = await self.emu_client.get_objective(obj)
                if flag:
                    locations.add(loc)
        locations -= self._scouted_locations
        if locations:
            self._scouted_locations.update(locations)
            await self.send_msgs([{"cmd":"LocationScouts","locations":locations,"create_as_hint":2}])

    async def check_goal(self) -> bool:
        flag = await self.emu_client.check_goal(self.slot_data['misc_goal'])
        if flag:
            await self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])
        return flag
    
    async def _emu_loop(self):
        has_goaled = False
        try:
            await self.auth_ready.wait()
            await self.start_emu_client()

            items = collections.Counter(self.item_names.lookup_in_slot(i.item, self.slot) for i in self.items_received)
            await self.emu_client.update_tracker(self, items)

            while not self.exit_event.is_set():
                if not self.server or self.server.socket.closed:
                    logger.info("Client disconnected")
                    await self.emu_client.disconnect()
                    return

                try:
                    await asyncio.wait_for(self.watcher_event.wait(), 1.0)
                except asyncio.TimeoutError:
                    pass
                self.watcher_event.clear()

                if await self.emu_client.should_process_checks():
                    if self.slot_data["death_link"] > 0:
                        await self._send_deathlink()
                    await self._receive_items()
                    await self._check_doors()
                    await self._location_checks()
                    await self._location_scouts()
                    if not has_goaled:
                        has_goaled = await self.check_goal()
        except Exception:
            logger.error("ERROR IN EMULATOR LOOP, PLEASE REPORT IN THE THREAD", exc_info=True)
    
    async def _send_deathlink(self):
        if await self.emu_client.export_deathlink():
            await self.send_death()

    async def _receive_deathlink(self, msg: str):
        self.emu_client.msg_queue.put_nowait((consts.COLOUR_RED, msg))
        await self.emu_client.import_deathlink(self.slot_data['death_link'])
    
    def on_deathlink(self, data: dict) -> None:
        Utils.async_start(self._receive_deathlink(data.get('cause') or f"{data['source']} died."))

    async def shutdown(self):
        if self.emu_loop:
            self.emu_loop.cancel()
        if self.emu_client:
            await self.emu_client.disconnect()
        return await super().shutdown()