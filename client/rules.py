from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


__all__ = ["rule_from_dict", "Rule", "True_", "Has", "Or", "And"]


translation = {
    "worlds.spyro-aht.options.KeyRings": "key_rings",
    "worlds.spyro-aht.options.RandomizeShopItems": "randomize_shop_items",
    "worlds.spyro-aht.options.RandomizeMovement": "randomize_movement",
    "worlds.spyro-aht.options.RealmAccess": "realm_access",
    "worlds.spyro-aht.options.RandomizeBreath": "randomize_breath"
}


def rule_from_dict(d: dict) -> 'Rule':
    match d['rule']:
        case 'True_': return True_(**d)
        case 'Has': return Has(**d)
        case 'Or': return Or(**d)
        case 'And': return And(**d)
        case 'BossLairRule': return BossLairRule(**d)
        case 'LGDoorRule': return LGDoorRule(**d)
        case 'BallGadget': return BallGadget(**d)
        case 'InvincibilityGadget': return InvincibilityGadget(**d)
        case 'SuperchargeGadget': return SuperchargeGadget(**d)
        case _: raise TypeError(d['rule'])


def operator(left: int, op: str, right: int) -> bool:
    match op:
        case 'eq': return left == right
        case 'ne': return left != right
        case 'gt': return left > right
        case 'ge': return left >= right
        case 'lt': return left < right
        case 'le': return left <= right
        case _: raise TypeError(op)


class Rule(ABC):
    def __init__(
            self, *,
            options: list | None = None,
            args: dict | None = None,
            children: list | None = None,
            **_
        ):
        self.options = options or []
        self.args = args or {}
        self.children = [rule_from_dict(c) for c in (children or [])]

        for opt in self.options:
            opt['option'] = translation.get(opt['option'], opt['option'])

    @abstractmethod
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool: ...

    def can_resolve(self, slot_data: dict) -> bool:
        for option in self.options:
            o = slot_data[option['option']]
            if not operator(o, option['operator'], option['value']):
                return False
        return True


class True_(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data)

class Has(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and items.get(self.args['item_name'], 0) >= self.args.get("count", 1)

class Or(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and any(rule.resolve(slot_data, items) for rule in self.children)

class And(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and all(rule.resolve(slot_data, items) for rule in self.children)

class BossLairRule(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and items.get("Dark Gem", 0) >= slot_data['boss_lair_costs'][self.args['index']]

class LGDoorRule(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and items.get("Light Gem", 0) >= slot_data['light_gem_door_costs'][self.args['index']]

class BallGadget(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and items.get("Light Gem", 0) >= slot_data["randomize_gadget_costs"][0]

class InvincibilityGadget(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and items.get("Light Gem", 0) >= slot_data["randomize_gadget_costs"][1]

class SuperchargeGadget(Rule):
    def resolve(self, slot_data: dict[str, Any], items: dict[str, int]) -> bool:
        return self.can_resolve(slot_data) and items.get("Light Gem", 0) >= slot_data["randomize_gadget_costs"][2]
