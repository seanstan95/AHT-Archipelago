from __future__ import annotations

import asyncio
import random
import struct
from collections import defaultdict
from math import floor

import dolphin_memory_engine

from NetUtils import NetworkItem

from . import rules
from .client import GenericClient
from ..data import consts

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..context import SpyroAHTContext

class DolphinClient(GenericClient):
    def __init__(self) -> None:
        super().__init__()
        self._notification_task = asyncio.create_task(self.notification_task())
        self.ready = asyncio.Event()
        self.msg_queue = asyncio.Queue()
        self.addresses = consts.G5SE7D()
    
    async def notification_task(self):
        from CommonClient import logger
        try:
            await self.ready.wait()
            while True:
                await asyncio.sleep(0.5)
                if await self.should_process_checks():
                    await asyncio.sleep(5)
                    dolphin_memory_engine.write_word(self.addresses.n_AP_NOTIFICATION_TIMER, 0)
                    col, msg = await self.msg_queue.get()

                    if len(msg) > 254:
                        msg = msg[:254]
                    
                    colour = struct.pack(">BBBB", *col)
                    dolphin_memory_engine.write_bytes(self.addresses.n_AP_NOTIFICATION_COLOR, colour)
                    dolphin_memory_engine.write_bytes(self.addresses.n_AP_NOTIFICATION_TEXT_BUFFER, (msg + "\0").encode("utf_16_be"))
                    dolphin_memory_engine.write_word(self.addresses.n_AP_NOTIFICATION_TIMER, 5*60)
        except Exception:
            logger.error("ERROR IN NOTIFICATION TASK, REPORT IN THREAD", exc_info=True)

    async def connect(self):
        if not dolphin_memory_engine.is_hooked():
            dolphin_memory_engine.hook()
            game_id = dolphin_memory_engine.read_bytes(0x80000000, 6)
            if game_id != b'G5SE7D':
                dolphin_memory_engine.un_hook()
                raise TypeError(f"Invalid or unsupported game id {game_id.decode()!r}")
        self.ready.set()
    
    async def disconnect(self):
        dolphin_memory_engine.write_byte(self.addresses.p_PATCH_BEEN_WRITTEN_TO, 0)
        self._notification_task.cancel()
        if dolphin_memory_engine.is_hooked():
            dolphin_memory_engine.un_hook()
            self.ready.clear()
    
    async def should_process_checks(self) -> bool:
        m_state = dolphin_memory_engine.read_word(self.addresses.IN_GAME)
        m_pause = dolphin_memory_engine.read_byte(self.addresses.PAUSE)
        return m_state == 3 and (m_pause & 0x80 == 0)

    async def scan_locations(self, *, shop_items: bool = False, key_rings: bool = False) -> set[int]:
        result: set[int] = set()
        for aploc, index in consts.LOCATIONS_BITFIELD.items():
            await asyncio.sleep(0)

            addr = self.addresses.g_LOCATION_BITFIELD + (index * 2) // 8
            data = dolphin_memory_engine.read_byte(addr)
            flag = data & (0b01 << ((index * 2) % 8))
            # 17: 245, 79: 246, 136: 247, 228: 248
            if flag:
                match aploc:
                    case 17:
                        result.update({17, 4000})
                    case 79:
                        result.update({79, 4001})
                    case 136:
                        result.update({136, 4002})
                    case 228:
                        result.add(4003)
                    case _:
                        result.add(aploc)
        
        if shop_items:
            for i in range(4):
                await asyncio.sleep(0)

                purchase_flag = dolphin_memory_engine.read_byte(self.addresses.g_SHOP_TEXT + (0x62 * i))
                if purchase_flag:
                    result.add(1000 + i)
            offset = 4
            for i in range(13):
                await asyncio.sleep(0)

                purchase_flag = dolphin_memory_engine.read_byte(self.addresses.g_SHOP_TEXT + (0x62 * (i + offset)))
                if purchase_flag:
                    result.add(2000 + i)
            offset += 13
            if not key_rings:
                for i in range(39):
                    await asyncio.sleep(0)

                    purchase_flag = dolphin_memory_engine.read_byte(self.addresses.g_SHOP_TEXT + (0x62 * (i + offset)))
                    if purchase_flag:
                        result.add(3013 + i)

        return result

    async def set_flag(self, address: int, flag: int, to: bool):
        flags = dolphin_memory_engine.read_word(address)
        if to:
            flags |= flag
        else:
            flags &= ~flag
        dolphin_memory_engine.write_word(address, int(flags))
    
    async def get_flag(self, address: int, flag: int) -> bool:
        return dolphin_memory_engine.read_word(address) & flag != 0

    async def get_objective(self, objective: int) -> bool:
        index = (objective & 0xFFFF) - 1
        uint = index // 32
        bit = index % 32
        return await self.get_flag(self.addresses.OBJECTIVES + (uint * 4), 1 << bit)
    
    async def has_any_breath(self) -> bool:
        b = dolphin_memory_engine.read_word(self.addresses.ABILITY_FLAGS)
        return b & (0x800e0) != 0

    async def set_breath(self, breath_id: int):
        dolphin_memory_engine.write_word(self.addresses.ACTIVE_BREATH, breath_id)
    
    async def get_item_count(self, address: int) -> int:
        return dolphin_memory_engine.read_byte(address)
    
    async def set_item(self, address: int, count: int):
        dolphin_memory_engine.write_byte(address, count)
    
    async def enable_butterfly_jar(self):
        check = dolphin_memory_engine.read_byte(self.addresses.g_INFINITE_BUTTERFLY_JAR)
        if not check:
            dolphin_memory_engine.write_byte(self.addresses.g_INFINITE_BUTTERFLY_JAR, 1)
            await self.set_flag(self.addresses.ABILITY_FLAGS, consts.AbilityFlags.ButterflyJar, True)
    
    async def add_gem_pack(self):
        value = random.randint(400, 600)
        double = dolphin_memory_engine.read_byte(self.addresses.g_INFINITE_DOUBLE_GEM)
        if double:
            value *= 2
        count = dolphin_memory_engine.read_word(self.addresses.GEMS)
        total = dolphin_memory_engine.read_word(self.addresses.TOTAL_GEMS)
        dolphin_memory_engine.write_word(self.addresses.GEMS, count + value)
        dolphin_memory_engine.write_word(self.addresses.TOTAL_GEMS, total + value)
    
    async def check_goal(self, goal_index: int) -> bool:
        if goal_index < 4:
            return await self.get_objective(consts.GOALS[goal_index])
        count = 0
        for obj in consts.GOALS:
            if await self.get_objective(obj):
                count += 1
        return count == 4

    async def import_deathlink(self, mode: int):
        dolphin_memory_engine.write_byte(self.addresses.g_DEATHLINK_INGOING, mode)

    async def export_deathlink(self) -> bool:
        b = dolphin_memory_engine.read_byte(self.addresses.g_DEATHLINK_OUTGOING)
        if b:
            dolphin_memory_engine.write_byte(self.addresses.g_DEATHLINK_OUTGOING, 0)
            return True
        return False

    async def apply_patch(self, ctx: "SpyroAHTContext"):
        dolphin_memory_engine.write_byte(self.addresses.p_SKIP_CUTSCENE_BUTTON, ctx.slot_data['misc_skip_cutscenes'])
        dolphin_memory_engine.write_byte(self.addresses.p_ALLOW_TELEPORT_TO_HUB, 1)
        dolphin_memory_engine.write_byte(self.addresses.p_DISABLE_POPUPS, 1)
        dolphin_memory_engine.write_byte(self.addresses.p_INSTANT_ELEVATORS, ctx.slot_data['misc_skip_elevators'])
        dolphin_memory_engine.write_word(self.addresses.p_MW_SEED, (int(ctx._seed) & 0xffffffff))
        dolphin_memory_engine.write_byte(self.addresses.p_USE_KEY_RINGS, ctx.slot_data['key_rings'])
        dolphin_memory_engine.write_byte(self.addresses.p_FIREWORKS_ARE_RANDOMIZED, ctx.slot_data['randomize_fireworks'])

        if ctx.slot_data['randomize_shop_items']:
            locations = list(range(1000, 1004))
            locations.extend(range(2000, 2013))
            if not ctx.slot_data['key_rings']:
                locations.extend(range(3013, 3051))
            await ctx.send_msgs([{"cmd": "LocationScouts", "locations": locations, "create_as_hint": 0}])
            await ctx._shop_items_received.wait()
            await self._prepare_shop_items(ctx, *ctx._shop_items)
        
        if ctx.slot_data["randomize_light_gem_door_costs"]:
            dolphin_memory_engine.write_bytes(self.addresses.p_LG_DOOR_COSTS, struct.pack(">BBBB", *ctx.slot_data["light_gem_door_costs"]))
        if ctx.slot_data["randomize_boss_lair_doors"]:
            dolphin_memory_engine.write_bytes(self.addresses.p_BOSS_COSTS, struct.pack(">BBBB", *ctx.slot_data["boss_lair_costs"]))
        
        b, i, s = ctx.slot_data['randomize_gadget_costs']
        dolphin_memory_engine.write_byte(self.addresses.p_BALL_GADGET_COST, b)
        dolphin_memory_engine.write_byte(self.addresses.p_INVINCIBILITY_COST, i)
        dolphin_memory_engine.write_byte(self.addresses.p_SUPERCHARGE_COST, s)

        dolphin_memory_engine.write_byte(self.addresses.p_STARTING_REALM, ctx.slot_data['starting_realm'])
        if ctx.slot_data['realm_access'] == 2:
            realm_access = [False, False, False, False]
            realm_access[ctx.slot_data['starting_realm']] = True
            dolphin_memory_engine.write_bytes(self.addresses.p_REALM_ACCESS, struct.pack(">????", *realm_access))
        else:
            dolphin_memory_engine.write_bytes(self.addresses.p_REALM_ACCESS, struct.pack(">????", True, True, True, True))
        
        if ctx.slot_data['easy_bosses']:
            bosses = [False, False, False, False]
            for b in ctx.slot_data['easy_bosses']:
                match b:
                    case 'Gnasty Gnorc':
                        bosses[0] = True
                    case 'Ineptune':
                        bosses[1] = True
                    case 'Red':
                        bosses[2] = True
                    case 'Mecha-Red':
                        bosses[3] = True
            dolphin_memory_engine.write_bytes(self.addresses.p_BOSS_EASY_MODE, struct.pack(">????", *bosses))
        
        dolphin_memory_engine.write_byte(self.addresses.p_PATCH_BEEN_WRITTEN_TO, 1)
    
    async def _prepare_shop_items(self, ctx: "SpyroAHTContext", *shop_items: NetworkItem):
        dolphin_memory_engine.write_byte(self.addresses.p_RANDOMIZE_SHOP, 1)
        dolphin_memory_engine.write_word(self.addresses.p_XLS_SHOP_ROWCOUNT, len(shop_items)+1)

        for idx, item in enumerate(shop_items):
            player = ctx.player_names[item.player]
            name = ctx.item_names.lookup_in_slot(item.item, item.player)
            game = ctx.slot_info[item.player]
            model = consts.ShopItemModel.Lockpick
            price = ctx.slot_data["randomized_shop_prices"][idx]
            if game.game == "Spyro: A Hero's Tail":
                if item.item in (0x1A, 0x1D, 0x1, 0xE, 0x5, 0x6, 0x7, 0xD): # softlock prevention
                    price = 0
                
                match item.item:
                    case 0xE:
                        model = consts.ShopItemModel.FireBomb
                    case 0x5:
                        model = consts.ShopItemModel.ElectricBomb
                    case 0x6:
                        model = consts.ShopItemModel.WaterBomb
                    case 0x7:
                        model = consts.ShopItemModel.IceBomb
                    case 0xF:
                        model = consts.ShopItemModel.HealthUpgrade
                    case 0x19:
                        model = consts.ShopItemModel.ButterflyJar
                    case 0x1A:
                        model = consts.ShopItemModel.DoubleGems
                    case 0x1B:
                        model = consts.ShopItemModel.Shockwave
                    case 0x22 | 0x23 | 0x24 | 0x25 | 0x26 | 0x27 | 0x28 | 0x29 | 0x2A | 0x2B | 0x2C | 0x2D | 0x2E | 0x2F:
                        model = consts.ShopItemModel.Keychain

            i = consts.XLSShoppingItem(model, consts.TextEntry(idx, f"{player}'s {name}"), (price, floor(price + (price * 0.25))))
            dolphin_memory_engine.write_bytes(self.addresses.p_XLS_SHOP_ITEMS + (0x20 * (idx + 1)), i.to_bytes('big'))
            dolphin_memory_engine.write_bytes(self.addresses.p_SHOP_TEXT + (0x62 * idx), i.text.to_bytes('big'))

    async def update_tracker(self, ctx: "SpyroAHTContext", items: dict[str, int]):
        from .. import location_rules
        parents: dict[str, list[str]] = defaultdict(list)
        extra_rules: dict[str, list[rules.Rule]] = defaultdict(list)

        def recursive_resolve(region):
            for rule in extra_rules[region]:
                if not rule.resolve(ctx.slot_data, items):
                    return False
            for parent in parents[region]:
                if not recursive_resolve(parent):
                    return False
            return True

        for region in location_rules.values():
            rule: rules.Rule = region['access_rule']

            extra_rules[region['name']].append(rule)

            for c in region['connections']:
                parents[c].append(region['name'])
                extra_rules[c].append(rule)
            
            if not recursive_resolve(region['name']):
                continue

            for loc in region['locations']:
                if loc['id'] not in consts.LOCATIONS_BITFIELD:
                    continue

                rule: rules.Rule = loc['access_rule']
                if not rule.resolve(ctx.slot_data, items):
                    continue

                index = consts.LOCATIONS_BITFIELD[loc['id']]
                addr = self.addresses.g_LOCATION_BITFIELD + (index * 2) // 8
                bit = (index * 2) % 8
                data = dolphin_memory_engine.read_byte(addr)
                dolphin_memory_engine.write_byte(addr, data | (0b10 << bit))
    
    async def allow_realm_access(self, id: int):
        current: list[bool] = list(struct.unpack(">????", dolphin_memory_engine.read_bytes(self.addresses.g_REALM_ACCESS, 4)))
        current[id - 0x30] = True
        dolphin_memory_engine.write_bytes(self.addresses.g_REALM_ACCESS, struct.pack(">????", *current))
    
    async def toggle_double_gems(self, to: bool):
        dolphin_memory_engine.write_byte(self.addresses.g_INFINITE_DOUBLE_GEM, 1 if to else 0)
