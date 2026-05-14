from dataclasses import dataclass

from Options import OptionSet, PerGameCommonOptions, Toggle, Choice, Range


class RandomizeSgtByrdMinigames(Toggle):
    """Toggle randomizing Sgt. Byrds mini game rewards.
    If set to 'false', it will always be the vanilla Dragon Egg and Light Gem."""
    display_name = "Randomize Sgt. Byrd Mini Games"
    default = 1


class RandomizeBlinkMinigames(Toggle):
    """Toggle randomizing Blinks mini game rewards.
    If set to 'false', it will always be the vanilla Dragon Egg and Light Gem."""
    display_name = "Randomize Blink Mini Games"
    default = 0


class RandomizeTurretMinigames(Toggle):
    """Toggle randomizing Turret mini game rewards.
    If set to 'false', it will always be the vanilla Dragon Egg and Light Gem."""
    display_name = "Randomize Turret Mini Games"
    default = 1


class RandomizeSparxMinigames(Toggle):
    """Toggle randomizing Sparxs mini game rewards.
    If set to 'false', it will always be the vanilla Dragon Egg and Light Gem."""
    display_name = "Randomize Sparx Mini Games"
    default = 1


class MiscHintMinigameRewards(Toggle):
    """When talking to a mini game npc, hint out their rewards."""
    display_name = "Hint Mini Game Rewards"
    default = 1


class MiscHintBossRewards(Toggle):
    """Hint out the item for beating a boss when their gate is opened."""
    display_name = "Hint Boss Rewards"
    default = 0


class RandomizeBreath(Choice):
    """Determines which starting elemental breath you have.
    
    default: Fire breath.
    random: Start with a random breath.
    none: Start with no breath. Adds a starting check.
    """
    display_name = "Starting Breath"
    option_default = 0
    option_randomized = 1
    option_none = 2
    default = 0

class RandomizeMovement(Toggle):
    """Randomize the 3 movement abilities (Glide, Swim, Charge).
    If you don't want to randomize one of these, add it to your start inventory."""
    display_name = "Randomize Movement"
    default = 0

class RandomizeFireworks(Toggle):
    """Adds Fireworks as a location check. Requires Fire Breath."""
    display_name = "Randomize Fireworks"
    default = 0


class RandomizeShopItems(Toggle):
    """Randomize Moneybags shop items.
    This will replace the vanilla shop items with various items from the multiworld,
    and it will put various items from the vanilla shop around in the multiworld.
    
    This has a few consequences:
    - If key rings are disabled, lock-picks have no upper limit. You can view your amount
    of lock-picks in the pause menu under 'Abilities'.
    - Health Refill (Butterfly Jar) will replenish on death once obtained.
    - Double Gems is infinite once obtained."""
    display_name = "Randomize Shop Items"
    default = 0

class ShopPricesMin(Range):
    """The minimum price for items in the shop."""
    display_name = "Minimum Shop Price"
    range_start = 1
    range_end = 10000
    default = 500


class ShopPricesMax(Range):
    """The maximum price for items in the shop."""
    display_name = "Maximum Shop Price"
    range_start = 1
    range_end = 10000
    default = 5000


class KeyRings(Toggle):
    """Enable region-specific key rings for locked chests.
    Key rings reduce the required progressive items, thereby letting locked chests
    have more progressive items inside them.
    
    Instead of obtaining individual lock-picks, there are key rings for reach level
    that let you unlock all locked chests there.
    If the shop is not randomized, key rings will appear there instead of lock-picks."""
    display_name = "Key Rings"
    default = 0


class RandomizeBossLairDoorCosts(Choice):
    """Sets the Dark Gem requirement of the Boss Lairs.
    Note: The door to your goal boss will always be the most expensive of the 4.

    default: No changes to cost.
    randomized: Randomizes the cost, between 1 and 40.
    shuffle: Shuffles the existing costs (10, 20, 30, 40)
    """
    display_name = "Randomize Boss Lair Requirements"
    option_default = 0
    option_randomized = 1
    option_shuffle = 2
    default = 0


class BossLairDoorCostMin(Range):
    """Sets the minimum cost for the boss lairs."""
    display_name = "Boss Lair Door Cost Minimum"
    range_start = 1
    range_end = 40
    default = 1


class BossLairDoorCostMax(Range):
    """Sets the maximum cost for the boss lairs."""
    display_name = "Boss Lair Door Cost Maximum"
    range_start = 1
    range_end = 40
    default = 40


class RandomizeLightGemDoorCosts(Choice):
    """Sets the cost of light gem doors.
    
    default: No changes to cost.
    randomized: Randomizes the cost, defined by the range in **Minimum Light Gem Door Cost** and **Maximum Light Gem Door Cost**.
    shuffle: Shuffles the existing prices (20, 45, 70 and 95)."""
    display_name = "Randomize Light Gem Door Cost"
    option_default = 0
    option_randomized = 1
    option_shuffle = 2
    default = 0


class LightGemDoorCostMin(Range):
    """Sets the minimum cost for light gem doors."""
    display_name = "Minimum Light Gem Door Cost"
    range_start = 1
    range_end = 100
    default = 1


class LightGemDoorCostMax(Range):
    """Sets the maximum cost for light gem doors."""
    display_name = "Maximum Light Gem Door Cost"
    range_start = 1
    range_end = 100
    default = 50


class RandomizeGadgetCost(Range):
    """Randomizes the cost of Ball, Invincibility and Supercharge gadgets.
    Set to 0 to leave as default cost."""
    display_name = "Randomize Gadget Costs"
    range_start = 0
    range_end = 100
    default = 0


class RealmAccess(Choice):
    """Set realm access mode.

    always: Access any realm at any time
    randomized: Shuffles access into the multiworld
    """
    display_name = "Realm Access"
    option_always = 0
    option_randomized = 2
    default = 0


class StartingRealm(Choice):
    """Sets starting realm behaviour.
    
    randomized: Start in a random realm
    """
    default = 0
    display_name = "Starting Realm"
    option_dragon_village = 0
    option_coastal_remains = 1
    option_frostbite_village = 2
    option_stormy_beach = 3
    option_randomized = 4


class MiscEasyBosses(OptionSet):
    """Toggle "easy" mode for bosses, making them take triple damage, shortening the fight considerably.
    Valid options: ["Gnasty Gnorc", "Ineptune", "Red", "Mecha-Red"]"""
    display_name = "Easy Bosses"
    valid_keys = ("Gnasty Gnorc", "Ineptune", "Red", "Mecha-Red")
    default = ("Gnasty Gnorc", "Ineptune", "Red", "Mecha-Red")


class MiscGoal(Choice):
    """Set the goal condition."""
    display_name = "Goal"
    option_gnorc = 0
    option_ineptune = 1
    option_red = 2
    option_mechared = 3
    option_all = 4
    default = 3


class MiscSkipCutscenes(Toggle):
    """Enable skipping most cutscenes with the Y button.
    In rare cases, this may have glitchty side-effects."""
    display_name = "Auto Skip Cutscenes"
    default = 0


class MiscSkipElevators(Toggle):
    """Enable a patch to skip the long elevator waits to Cloudy Domain, Sunken Ruins and Magma Falls"""
    display_name = "Skip Elevators"
    default = 1


class MiscDeathLink(Choice):
    """Enable Death-Link.

    disabled: Disabled.
    Shielded: The Butterfly Jar will protect you from a DeathLink, if you have it.
    Enabled: Enabled.
    """
    display_name = "DeathLink"
    option_disabled = 0
    option_shielded = 1
    option_enabled = 2
    default = 0


@dataclass
class SpyroAHTOptions(PerGameCommonOptions):
    randomize_sgt_byrd_minigames: RandomizeSgtByrdMinigames
    randomize_blink_minigames: RandomizeBlinkMinigames
    randomize_turret_minigames: RandomizeTurretMinigames
    randomize_sparx_minigames: RandomizeSparxMinigames

    randomize_breath: RandomizeBreath
    randomize_movement: RandomizeMovement

    randomize_fireworks: RandomizeFireworks

    key_rings: KeyRings

    randomize_shop_items: RandomizeShopItems
    shop_prices_min: ShopPricesMin
    shop_prices_max: ShopPricesMax

    randomize_light_gem_door_costs: RandomizeLightGemDoorCosts
    light_gem_door_cost_min: LightGemDoorCostMin
    light_gem_door_cost_max: LightGemDoorCostMax

    randomize_boss_lair_doors: RandomizeBossLairDoorCosts
    boss_lair_door_cost_min: BossLairDoorCostMin
    boss_lair_door_cost_max: BossLairDoorCostMax

    randomize_gadget_costs: RandomizeGadgetCost

    realm_access: RealmAccess
    starting_realm: StartingRealm

    misc_easy_bosses: MiscEasyBosses
    misc_goal: MiscGoal
    misc_hint_minigame_rewards: MiscHintMinigameRewards
    misc_hint_boss_rewards: MiscHintBossRewards
    misc_skip_cutscenes: MiscSkipCutscenes
    misc_skip_elevators: MiscSkipElevators

    death_link: MiscDeathLink

