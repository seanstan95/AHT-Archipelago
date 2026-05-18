import asyncio
import collections
from dataclasses import dataclass
import functools
import pkgutil
from collections import defaultdict
from typing import Any, TextIO, override

import orjson

from Options import OptionError
import Utils
from BaseClasses import Item, ItemClassification, MultiWorld, Region
from rule_builder.options import OptionFilter
from rule_builder.rules import Has, HasAny, Rule, True_
from worlds.AutoWorld import World
from worlds.LauncherComponents import icon_paths

from .options import RandomizeMovement, SpyroAHTOptions, RandomizeBreath
from .client import rules


icon_paths['spyro-aht'] = f'ap:{__name__}/icon.png'


KEYS = {
    "DV": "Dragon Village",
    "CS": "Crocovile Swamp",
    "DF": "Dragonfly Falls",
    "CR": "Coastal Remains",
    "CD": "Cloudy Domain",
    "SR": "Sunken Ruins",
    "FV": "Frostbite Village",
    "GG": "Gloomy Glacier",
    "IC": "Ice Citadel",
    "SB": "Stormy Beach",
    "MM": "Moltem Mount",
    "MFt": "Magma Falls Top",
    "MFb": "Magma Falls Bottom",
    "DM": "Dark Mine",
    "RL": "Red's Laboratory",
    "Moneybags": "Shop Items"
}


def _load_file(file: str) -> Any:
    return orjson.loads(pkgutil.get_data(__name__, "data/" + file).decode("utf-8")) # type: ignore


location_rules: dict[str, dict] = {}
_k = _load_file("locations.json")
for n, r in _k.items():
    location_rules[n] = r
    r['access_rule'] = rules.rule_from_dict(r['access_rule'])
    locs = []
    for l in r['locations']:
        l['access_rule'] = rules.rule_from_dict(l['access_rule'])
        locs.append(l)
    r['locations'] = locs


def create_location_groups() -> dict[str, set[str]]:
    data = _load_file("locations.json")
    r = defaultdict(set)
    for region in data.values():
        for location in region['locations']:
            key, _ = location['name'].split(': ')
            if key not in KEYS: continue
            r[KEYS[key]].add(location['name'])
    
    for s in SGT_BYRD:
        r["Sgt. Byrd"].update(s)
    for s in BLINK:
        r["Blink"].update(s)
    for s in SPARX:
        r["Sparx"].update(s)
    for s in TURRET:
        r["Turret"].update(s)
    return r


def create_item_groups() -> dict[str, set[str]]:
    data = _load_file("items.json")
    r = defaultdict(set)
    for item in data:
        r[item["group"]].add(item["name"])

    return r


def _item_name_to_id() -> dict[str, int]:
    data = _load_file("items.json")
    return {i['name']: i['id'] for i in data}


def _location_name_to_id() -> dict[str, int]:
    data = _load_file("locations.json")
    ret = {}
    for r in data.values():
        for l in r['locations']:
            ret[l['name']] = l['id']
    return ret


classifications = {i['name']: ItemClassification(i['classification']) for i in _load_file("items.json")}

SGT_BYRD = {
    ("DV: Dragon Egg from Sgt. Byrd", "DV: Light Gem from Sgt. Byrd"),
    ("CD: Dragon Egg from Sgt. Byrd", "CD: Light Gem from Sgt. Byrd"),
    ("IC: Dragon Egg from Sgt. Byrd", "IC: Light Gem from Sgt. Byrd"),
    ("MM: Dragon Egg from Sgt. Byrd", "MM: Light Gem from Sgt. Byrd")
}

BLINK = {
    ("CS: Dragon Egg from Blink", "CS: Light Gem from Blink"),
    ("CR: Dragon Egg from Blink", "CR: Light Gem from Blink"),
    ("FV: Dragon Egg from Blink", "FV: Light Gem from Blink"),
    ("DM: Dragon Egg from Blink", "DM: Light Gem from Blink")
}

SPARX = {
    ("DF: Dragon Egg from Sparx", "DF: Light Gem from Sparx"),
    ("SR: Dragon Egg from Sparx", "SR: Light Gem from Sparx"),
    ("GG: Dragon Egg from Sparx", "GG: Light Gem from Sparx"),
    ("MFb: Dragon Egg from Sparx", "MFb: Light Gem from Sparx")
}

TURRET = {
    ("CS: Dragon Egg from Fredneck", "CS: Light Gem from Fredneck"),
    ("CR: Dragon Egg from Turtle Mother", "CR: Light Gem from Turtle Mother"),
    ("FV: Dragon Egg from Peggy", "FV: Light Gem from Peggy"),
    ("SB: Dragon Egg from Wally", "SB: Light Gem from Wally")
}

class SpyroAHTWorld(World):
    """
    Spyro: A Hero's Tail is a 3D platformer and collect-a-thon released in 2004 for the Xbox, Playstation 2 and GameCube.
    """
    game = "Spyro: A Hero's Tail"
    origin_region_name = "START"

    options_dataclass = SpyroAHTOptions
    options: SpyroAHTOptions # type: ignore

    item_name_groups = create_item_groups()
    location_name_groups = create_location_groups()
    item_name_to_id = _item_name_to_id()
    location_name_to_id = _location_name_to_id()

    def __init__(self, multiworld: MultiWorld, player: int):
        super().__init__(multiworld, player)
        multiworld.early_items[player]['Double Jump'] = 1

        self._lg_doors = [70, 20, 95, 45]
        self._boss_lairs = [10, 20, 30, 40]
        self._gadget_costs = [8, 24, 40]
        self._starting_realm = 0
        self._starting_breath = -1

        self._access_cards = [
            "Dragon Village Access Card",
            "Coastal Remains Access Card",
            "Frostbite Village Access Card",
            "Stormy Beach Access Card"
        ]
    
    def generate_early(self) -> None:
        if self.options.starting_realm.value != 0: # not dragon village
            if self.options.randomize_movement.value == 0 and self.options.randomize_shop_items.value == 0:
                raise OptionError("Cannot start outside Dragon Village if Movement and Shop randomization is off")
    
    def create_item(self, name: str) -> Item:
        return Item(name, classifications[name], self.item_name_to_id[name], self.player)

    def create_regions(self):
        if self.options.randomize_gadget_costs.value != 0:
            if self.options.randomize_gadget_costs.value == 2:  # shuffled:
                self.random.shuffle(self._gadget_costs)
            else:  # randomized:
                lmin, lmax = self.options.gadget_cost_min.value, self.options.gadget_cost_max.value
                if lmin > lmax:
                    lmin, lmax = lmax, lmin

                self._gadget_costs = [self.random.randint(lmin, lmax) for _ in range(3)]

        match self.options.starting_realm.value:
            case 4: # Randomized:
                self._starting_realm = self.random.randint(0, 3)
                while self._starting_realm == self.options.misc_goal.value:
                    self._starting_realm = self.random.randint(0, 3)
            case _:
                self._starting_realm = self.options.starting_realm.value

        if self.options.randomize_boss_lair_doors.value != 0:
            if self.options.randomize_boss_lair_doors.value == 2: # shuffled:
                self.random.shuffle(self._boss_lairs)
            else:
                bmin, bmax = self.options.boss_lair_door_cost_min.value, self.options.boss_lair_door_cost_max.value
                if bmin > bmax:
                    bmin, bmax = bmax, bmin
                
                self._boss_lairs = [self.random.randint(bmin, bmax) for _ in range(4)]
        
            if self.options.misc_goal.value != 4:
                highest = functools.reduce(max, self._boss_lairs)
                self._boss_lairs.remove(highest)
                if self.options.misc_goal < 3:
                    self._boss_lairs.insert(self.options.misc_goal.value, highest)
                else:
                    self._boss_lairs.append(highest)
        
        if self.options.randomize_light_gem_door_costs.value != 0:
            if self.options.randomize_light_gem_door_costs.value == 2: # shuffled:
                self.random.shuffle(self._lg_doors)
            else:
                lmin, lmax = self.options.light_gem_door_cost_min.value, self.options.light_gem_door_cost_max.value
                if lmin > lmax:
                    lmin, lmax = lmax, lmin
                
                self._lg_doors = [self.random.randint(lmin, lmax) for _ in range(4)]

        data = _load_file("locations.json")

        self.multiworld.regions.extend(Region(r['name'], self.player, self.multiworld) for r in data.values())

        for r in data.values():
            region = self.get_region(r['name'])
            for con in r['connections']:
                c = self.get_region(con)
                entrance = f'{region.name}=>{c.name}'
                region.connect(c, entrance, rule=self.rule_from_dict(data[con]['access_rule']))

        for r in data.values():
            region = self.get_region(r['name'])
            f = {}
            for l in r['locations']:
                add = True
                for options in l.get('options', ()):
                    option = getattr(self.options, options['option'])
                    match options.get('operator', 'eq'):
                        case 'eq': add = add and option.value == options['value']
                        case 'ne': add = add and option.value != options['value']
                        case 'gt': add = add and option.value > options['value']
                        case 'ge': add = add and option.value >= options['value']
                        case 'lt': add = add and option.value < options['value']
                        case 'le': add = add and option.value <= options['value']
                if add:
                    f[l['name']] = l['id']
            region.add_locations(f)
        
        match self.options.misc_goal.value:
            case 0 | 1 | 2 | 3:
                self.multiworld.completion_condition[self.player] = lambda state: state.has("Victory", self.player)
            case 4:
                self.multiworld.completion_condition[self.player] = lambda state: state.has_all(("VictoryCon1", "VictoryCon2", "VictoryCon3", "VictoryCon4"), self.player)
        match self.options.misc_goal.value:
            case 0:
                self.get_region("DragonVillageGnastysCave").add_event("DragonVillageDefeatGnasty", "Victory", rule=(
                    Has("Fire Breath", options=[OptionFilter(RandomizeBreath, 0, "ne")]) |
                    Has("Charge", options=[OptionFilter(RandomizeMovement, 1)]) |
                    True_(options=[OptionFilter(RandomizeBreath, 0), OptionFilter(RandomizeMovement, 0)])
                ))
            case 1:
                self.get_region("CoastalRemainsWateryTomb").add_event("CoastalRemainsDefeatIneptune", "Victory", rule=True_())
            case 2:
                self.get_region("FrostbiteVillageRedsChamber").add_event("FrostbiteVillageDefeatRed", "Victory", rule=True_())
            case 3:
                self.get_region("RedsLaboratory").add_event("Red's Laboratory: Defeat Mecha-Red", "Victory", rule=(
                    BossLairRule(3) & (
                        Has("Fire Breath", options=[OptionFilter(RandomizeBreath, 0, "ne")]) |
                        True_(options=[OptionFilter(RandomizeBreath, 0)])
                    )
                ))
            case 4:
                self.get_region("DragonVillageGnastysCave").add_event("DragonVillageDefeatGnasty", "VictoryCon1", rule=(
                    Has("Fire Breath", options=[OptionFilter(RandomizeBreath, 0, "ne")]) |
                    Has("Charge", options=[OptionFilter(RandomizeMovement, 1)]) |
                    True_(options=[OptionFilter(RandomizeBreath, 0), OptionFilter(RandomizeMovement, 0)])
                ))
                self.get_region("CoastalRemainsWateryTomb").add_event("CoastalRemainsDefeatIneptune", "VictoryCon2", rule=True_())
                self.get_region("FrostbiteVillageRedsChamber").add_event("FrostbiteVillageDefeatRed", "VictoryCon3", rule=True_())
                self.get_region("RedsLaboratory").add_event("Red's Laboratory: Defeat Mecha-Red", "VictoryCon4", rule=(
                    BossLairRule(3) & (
                        Has("Fire Breath", options=[OptionFilter(RandomizeBreath, 0, "ne")]) |
                        True_(options=[OptionFilter(RandomizeBreath, 0)])
                    )
                ))
                
    def set_rules(self) -> None:
        data = _load_file("locations.json")
        for r in data.values():
            for l in r['locations']:
                try:
                    loc = self.get_location(l['name'])
                except KeyError:
                    continue
                self.set_rule(loc, self.rule_from_dict(l['access_rule']))
        
    def create_items(self) -> None:
        data = _load_file("items.json")
        itempool = []

        minigames = 0

        if self.options.randomize_sgt_byrd_minigames.value == 0:
            for d, l in SGT_BYRD:
                self.get_location(d).place_locked_item(self.create_item("Dragon Egg"))
                self.get_location(l).place_locked_item(self.create_item("Light Gem"))
            minigames += 4
        if self.options.randomize_blink_minigames.value == 0:
            for d, l in BLINK:
                self.get_location(d).place_locked_item(self.create_item("Dragon Egg"))
                self.get_location(l).place_locked_item(self.create_item("Light Gem"))
            minigames += 4
        if self.options.randomize_sparx_minigames.value == 0:
            for d, l in SPARX:
                self.get_location(d).place_locked_item(self.create_item("Dragon Egg"))
                self.get_location(l).place_locked_item(self.create_item("Light Gem"))
            minigames += 4
        if self.options.randomize_turret_minigames.value == 0:
            for d, l in TURRET:
                self.get_location(d).place_locked_item(self.create_item("Dragon Egg"))
                self.get_location(l).place_locked_item(self.create_item("Light Gem"))
            minigames += 4
        
        if self.options.randomize_fireworks.value == 1:
            for _ in range(22):
                itempool.append(self.create_item("Gem Pack"))

        if self.options.randomize_breath.value == 0:
            self._starting_breath = 0
        elif self.options.randomize_breath.value == 1:
            self._starting_breath = self.random.randint(0, 3)
        else:
            self._starting_breath = -1
        
        l = self.get_location("Starter Checks: Breath")
        match self._starting_breath:
            case 0:
                l.place_locked_item(self.create_item("Fire Breath"))
            case 1:
                l.place_locked_item(self.create_item("Electric Breath"))
            case 2:
                l.place_locked_item(self.create_item("Water Breath"))
            case 3:
                l.place_locked_item(self.create_item("Ice Breath"))
        
        if self.options.randomize_movement.value == 0:
            self.get_location("Starter Checks: Swim").place_locked_item(self.create_item("Swim"))
            self.get_location("Starter Checks: Charge").place_locked_item(self.create_item("Charge"))
            self.get_location("Starter Checks: Glide").place_locked_item(self.create_item("Glide"))

        for item in data:
            add = True

            match item['name']:
                case "Fire Breath": add = self._starting_breath != 0
                case "Electric Breath": add = self._starting_breath != 1
                case "Water Breath": add = self._starting_breath != 2
                case "Ice Breath": add = self._starting_breath != 3
                case "Glide" | "Charge" | "Swim": add = self.options.randomize_movement.value == 1

            for options in item.get("option", ()):
                option = getattr(self.options, options['option'])
                match options.get('operator', 'eq'):
                    case 'eq': add = add and option.value == options['value']
                    case 'ne': add = add and option.value != options['value']
                    case 'gt': add = add and option.value > options['value']
                    case 'ge': add = add and option.value >= options['value']
                    case 'lt': add = add and option.value < options['value']
                    case 'le': add = add and option.value <= options['value']

            if add:
                count = item.get('count', 1)
                if item['name'] in ('Dragon Egg', 'Light Gem'):
                    count -= minigames
                
                for _ in range(count):
                    itempool.append(self.create_item(item['name']))

        if self.options.realm_access.value == 2:
            itempool.append(self.create_item("Gem Pack"))
        
            start = self._access_cards.pop(self._starting_realm)
            self.get_location("Starter Checks: Starting Realm Access").place_locked_item(self.create_item(start))
            for i in self._access_cards:
                itempool.append(self.create_item(i))
            
        self.multiworld.itempool.extend(itempool)
    
    def fill_slot_data(self):
        smin = self.options.shop_prices_min.value
        smax = self.options.shop_prices_max.value
        if smin > smax:
            smin, smax = smax, smin

        r: dict[str, Any] = {
            "misc_goal": self.options.misc_goal.value,
            "misc_skip_cutscenes": self.options.misc_skip_cutscenes.value,
            "misc_hint_boss_rewards": self.options.misc_hint_boss_rewards.value,
            "misc_hint_minigame_rewards": self.options.misc_hint_minigame_rewards.value,
            "misc_skip_elevators": self.options.misc_skip_elevators.value,

            "realm_access": self.options.realm_access.value,
            "starting_realm": self._starting_realm,

            "key_rings": self.options.key_rings.value,
            "randomize_shop_items": self.options.randomize_shop_items.value,

            "randomize_boss_lair_doors": self.options.randomize_boss_lair_doors.value,
            "boss_lair_costs": self._boss_lairs,

            "randomize_light_gem_door_costs": self.options.randomize_light_gem_door_costs.value,
            "light_gem_door_costs": self._lg_doors,

            "randomize_gadget_costs": self.options.randomize_gadget_costs.value,
            "gadget_costs": self._gadget_costs,

            "randomize_movement": self.options.randomize_movement.value,
            "randomize_breath": self.options.randomize_breath.value,
            "randomize_fireworks": self.options.randomize_fireworks.value,

            "easy_bosses": self.options.misc_easy_bosses.value,

            "death_link": self.options.death_link.value
        }

        if self.options.randomize_shop_items.value:
            if self.options.key_rings.value:
                r['randomized_shop_prices'] = [self.random.randint(smin, smax) for _ in range(19)]
            else:
                r['randomized_shop_prices'] = [self.random.randint(smin, smax) for _ in range(57)]
        return r
    
    def write_spoiler(self, spoiler_handle: TextIO) -> None:
        super().write_spoiler(spoiler_handle)
        spoiler_handle.write(f"Starting Realm:                  {self._starting_realm}\n")
        spoiler_handle.write(f"Randomized Gadget Costs:         {self._gadget_costs}\n")
        spoiler_handle.write(f"Randomized Boss Lair Costs:      {self._boss_lairs}\n")
        spoiler_handle.write(f"Randomized Light Gem Door Costs: {self._lg_doors}\n")


@dataclass
class BossLairRule(Rule[SpyroAHTWorld], game="Spyro: A Hero's Tail"):
    index: int

    @override
    def _instantiate(self, world: SpyroAHTWorld) -> Rule.Resolved:
        return Has("Dark Gem", world._boss_lairs[self.index]).resolve(world)


@dataclass
class LGDoorRule(Rule[SpyroAHTWorld], game="Spyro: A Hero's Tail"):
    index: int

    @override
    def _instantiate(self, world: SpyroAHTWorld) -> Rule.Resolved:
        return Has("Light Gem", world._lg_doors[self.index]).resolve(world)


@dataclass
class BallGadget(Rule[SpyroAHTWorld], game="Spyro: A Hero's Tail"):
    @override
    def _instantiate(self, world: SpyroAHTWorld) -> Rule.Resolved:
        return Has("Light Gem", world._gadget_costs[0]).resolve(world)


@dataclass
class InvincibilityGadget(Rule[SpyroAHTWorld], game="Spyro: A Hero's Tail"):
    @override
    def _instantiate(self, world: SpyroAHTWorld) -> Rule.Resolved:
        return Has("Light Gem", world._gadget_costs[1]).resolve(world)


@dataclass
class SuperchargeGadget(Rule[SpyroAHTWorld], game="Spyro: A Hero's Tail"):
    @override
    def _instantiate(self, world: SpyroAHTWorld) -> Rule.Resolved:
        return Has("Light Gem", world._gadget_costs[2]).resolve(world)


def _run_client(*args: str):
    import colorama
    from CommonClient import server_loop, gui_enabled, get_base_parser
    Utils.init_logging("Spyro: A Hero's Tail Client")

    async def _main(connect: str | None, password: str | None):
        from .context import SpyroAHTContext
        ctx = SpyroAHTContext(connect, password)
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        await asyncio.sleep(1)

        await ctx.exit_event.wait()
        ctx.watcher_event.set()
        ctx.server_address = None
        await ctx.shutdown()
    
    parser = get_base_parser()
    parsed_args = parser.parse_args(args)
    colorama.init()
    asyncio.run(_main(parsed_args.connect, parsed_args.password))
    colorama.deinit()

def run_client():
    from multiprocessing import Process
    Process(target=_run_client,name="SpyroAHTClient").start()

from worlds.LauncherComponents import Component, components
components.append(Component("Spyro AHT Client", func=run_client, icon='spyro-aht'))
