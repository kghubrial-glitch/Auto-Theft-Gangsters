"""Content tables + world simulation config: NPCs, combat, skills, cars.

Item/weapon/car/skill content is merged from `game_data.py`, which holds the
real values recovered from the APK's Data.bundle. A small set of legacy
placeholder goods is kept for the shop flow tests. See research/server/README.md.
"""

from . import game_data as GD
from .game_data import CARS as REAL_CARS
from .game_data import ITEMS as REAL_ITEMS
from .game_data import PROFESSIONS
from .game_data import SKILLS as REAL_SKILLS
from .game_data import WEAPONS as REAL_WEAPONS

# The main open-world map the client loads after character pick.
#
# CRITICAL: map ids must match the client's MapInfoData table (recovered from
# the APK's Data.bundle). In that table map 1's scene name is literally
# "LoadingScene" — entering map 1 makes LoadingWindow.LoadScene load the
# loading screen as the game map, so the loading window never finishes.
# The main city (scene DSJ_GTA) is map id 11.
MAIN_CITY_MAP = "11"

# --- testing build --------------------------------------------------------
# Every new character starts maxed out so all content is reachable while
# testing (user request: level 80, huge gold/diamond wallets).
TEST_MAX_LEVEL = 80
TEST_START_GOLD = 99_999_999
TEST_START_DIAMOND = 999_999
TEST_START_CASH = 99_999_999

# --- items -----------------------------------------------------------------
# item_id -> {"name", "type", "slot", "price"(gold), "power"}
# type: "consumable" | "equipment" | "badge" | "fashion" | "package"
# slot: 0 weapon, 1 armor, 2 badge, 3 fashion (equipment/badge/fashion only)
# Real items from the APK ItemData table + the legacy placeholders below.
ITEMS = {
    1:  {"name": "Health Potion", "type": "consumable", "price": 250,
         "heal": 50},
    2:  {"name": "Bandage", "type": "consumable", "price": 120, "heal": 20},
    3:  {"name": "Body Armor", "type": "equipment", "slot": 1, "price": 3000,
         "power": 20},
    4:  {"name": "Gold Pack (S)", "type": "package", "price": 1000,
         "gold": 2000},
    5:  {"name": "Energy Drink", "type": "consumable", "price": 300,
         "heal": 30},
    10: {"name": "Pistol", "type": "equipment", "slot": 0, "price": 8000,
         "power": 15},
    11: {"name": "Shotgun", "type": "equipment", "slot": 0, "price": 15000,
         "power": 35},
    12: {"name": "Rifle", "type": "equipment", "slot": 0, "price": 40000,
         "power": 60},
    20: {"name": "Badge of Strength", "type": "badge", "slot": 2, "price": 5000,
         "power": 10},
    21: {"name": "Lucky Badge", "type": "badge", "slot": 2, "price": 9000,
         "power": 25},
    30: {"name": "Leather Jacket", "type": "fashion", "slot": 3, "price": 2000},
    31: {"name": "Street Suit", "type": "fashion", "slot": 3, "price": 6000},
    40: {"name": "Starter Crate", "type": "package", "price": 1500,
         "contents": {1: 3, 2: 5}},
}
ITEMS.update(REAL_ITEMS)
# weapons are equipment with slot 0 and `atk` as power
for _wid, _w in REAL_WEAPONS.items():
    ITEMS[_wid] = {
        "name": _w["name"], "type": "equipment", "slot": 0,
        "price": 0, "power": _w["atk"], "weapon_class": _w["class"],
        "tier": _w["tier"], "skills": _w["skills"],
    }

# --- fashion (ITEM_TYPE.FASHION_EQUIP = 16) ----------------------------------
# fashion_id -> {"name", "type": "fashion", "fashion_slot" (client
# FASHION_EQUIPPACK index: 0 head / 1 body / 2 weapon / 3 leg), "model",
# "price"}. Model ids are CharacterModelData part rows (base suffix _T/_S/
# _WQ/_X like the armor visuals) so the client can render the worn piece.
FASHION_SET = {
    70: {"name": "Street Cap",        "type": "fashion", "fashion_slot": 0,
         "model": "", "price": 1000},
    71: {"name": "Leather Jacket",    "type": "fashion", "fashion_slot": 1,
         "model": "", "price": 2000},
    72: {"name": "Gold Bat Skin",     "type": "fashion", "fashion_slot": 2,
         "model": "", "price": 3000},
    73: {"name": "Cargo Pants",       "type": "fashion", "fashion_slot": 3,
         "model": "", "price": 1500},
    74: {"name": "Red Beanie",        "type": "fashion", "fashion_slot": 0,
         "model": "", "price": 1200},
    75: {"name": "Street Suit",       "type": "fashion", "fashion_slot": 1,
         "model": "", "price": 6000},
    76: {"name": "Chrome Bat Skin",   "type": "fashion", "fashion_slot": 2,
         "model": "", "price": 5000},
    77: {"name": "Track Pants",       "type": "fashion", "fashion_slot": 3,
         "model": "", "price": 1800},
}
ITEMS.update(FASHION_SET)
# every new account spawns with ALL fashions in the wardrobe
ALL_FASHION_IDS = sorted(FASHION_SET)

# --- cars --------------------------------------------------------------------
# legacy placeholder cars (shop goods 901-903 reference ids 1-3)
LEGACY_CARS = {
    1: {"name": "Sedan", "speed": 14},
    2: {"name": "Muscle Car", "speed": 18},
    3: {"name": "Sports Coupe", "speed": 24},
}
CARS = dict(LEGACY_CARS)
CARS.update(REAL_CARS)

# shops: shop_id -> goods list (as before, plus car shop id 9)
SHOPS = {
    1: {
        "name": "General Store",
        "goods": [
            {"goods_id": 101, "item_id": 1, "count": 1,
             "currency": 1, "price": 250},
            {"goods_id": 102, "item_id": 2, "count": 5,
             "currency": 1, "price": 600},
            {"goods_id": 103, "item_id": 3, "count": 1,
             "currency": 1, "price": 3000},
            {"goods_id": 104, "item_id": 4, "count": 1,
             "currency": 2, "price": 10},
            {"goods_id": 105, "item_id": 5, "count": 10,
             "currency": 2, "price": 25},
            {"goods_id": 106, "item_id": 40, "count": 1,
             "currency": 1, "price": 1500},
        ],
    },
    2: {
        "name": "Weapon Shop",
        "goods": [
            {"goods_id": 201, "item_id": 10, "count": 1,
             "currency": 1, "price": 8000},
            {"goods_id": 202, "item_id": 11, "count": 1,
             "currency": 1, "price": 15000},
            {"goods_id": 203, "item_id": 12, "count": 1,
             "currency": 2, "price": 60},
        ],
    },
    3: {
        "name": "Badge & Fashion",
        "goods": [
            {"goods_id": 301, "item_id": 20, "count": 1,
             "currency": 1, "price": 5000},
            {"goods_id": 302, "item_id": 21, "count": 1,
             "currency": 1, "price": 9000},
            {"goods_id": 303, "item_id": 30, "count": 1,
             "currency": 1, "price": 2000},
            {"goods_id": 304, "item_id": 31, "count": 1,
             "currency": 2, "price": 20},
        ],
    },
    9: {
        "name": "Car Shop",
        "car_shop": True,
        # the real car shop sold the car exchange vouchers (ItemData 9301-9307)
        # which the client exchanges into the actual vehicles (CarData 1001-1007)
        "goods": [
            {"goods_id": 901, "item_id": 9301, "count": 1, "car_id": 1001,
             "name": "North Star", "currency": 1, "price": 1888},
            {"goods_id": 902, "item_id": 9303, "count": 1, "car_id": 1002,
             "name": "Thunder", "currency": 1, "price": 5888},
            {"goods_id": 903, "item_id": 9304, "count": 1, "car_id": 1003,
             "name": "Conqueror", "currency": 1, "price": 8888},
            {"goods_id": 904, "item_id": 9302, "count": 1, "car_id": 1004,
             "name": "Bison", "currency": 1, "price": 18888},
            {"goods_id": 905, "item_id": 9305, "count": 1, "car_id": 1005,
             "name": "Night Walker", "currency": 1, "price": 28888},
            {"goods_id": 906, "item_id": 9306, "count": 1, "car_id": 1006,
             "name": "Golden King", "currency": 2, "price": 100},
            {"goods_id": 907, "item_id": 9307, "count": 1, "car_id": 1007,
             "name": "Christmas Sleigh", "currency": 2, "price": 50},
        ],
    },
}

CURRENCY_CASH = 0
CURRENCY_GOLD = 1
CURRENCY_DIAMOND = 2

# guild shop (bought with guild-donated gold via req_buy_guild_goods)
GUILD_SHOP = [
    {"goods_id": 801, "item_id": 1, "count": 5, "price": 500},
    {"goods_id": 802, "item_id": 2, "count": 10, "price": 800},
    {"goods_id": 803, "item_id": 20, "count": 1, "price": 4000},
    {"goods_id": 804, "item_id": 40, "count": 1, "price": 2500},
]

# --- missions ---------------------------------------------------------------
# The REAL main mission chain lives in server/mission_data.py (extracted
# from the APK's MissionData table). The entries below are legacy side
# missions kept for the buy/visit progression hooks.
MISSIONS = {
    "900001": {
        "name": "Stock Up",
        "type": "buy",
        "item_id": 1,
        "count": 2,
        "reward": {"gold": 1000, "diamond": 2, "items": {2: 2}},
        "next": "900002",
    },
    "900002": {
        "name": "Armed and Ready",
        "type": "buy",
        "item_id": 10,
        "count": 1,
        "reward": {"gold": 3000, "diamond": 5, "items": {3: 1}},
        "next": None,
    },
    "900101": {
        "name": "Courier Run",
        "type": "visit",
        "map_id": MAIN_CITY_MAP,
        "count": 1,
        "reward": {"gold": 800, "diamond": 1, "items": {1: 3}},
        "next": None,
    },
}

DAILY_MISSION_IDS = ["900101"]

# --- combat / npcs ------------------------------------------------------------
# skills: real per-class skill groups from SkillData merged over the legacy
# generic set
SKILLS = {
    1: {"name": "Basic Attack", "damage": 5},
    2: {"name": "Heavy Strike", "damage": 15},
    3: {"name": "Power Blow", "damage": 30},
}
SKILLS.update(REAL_SKILLS)

SKILL_LEVELUP_COST = 1000       # gold per skill level

# NPC kinds per map: kind -> (name, level, max_hp, damage, exp, loot table)
# loot: {item_id: (drop chance 0..1, count)}
#
# npcdataid/atk/def are REAL NpcData rows recovered from the APK's
# Data.bundle (server/game_data.py-style extraction): the client's
# npc_create_handler -> ObjInitNpcData.InitData hard-looks-up
# DataManager.GetNpcDataByID(npc_attribute.npcdataid) — an id that is not in
# the client's NpcData table returns null and crashes the client (loading
# window freezes at 90%). Rows used (NpcData CSV):
#   21131 RepairMan  Lv.1 Atk 20 Hp 2800 Def 100  (model NPC_Nan_009)
#   21132 Horro      Lv.2 Atk 25 Hp 3640 Def 110  (model NPC_Nan_006)
#   21133 Punk       Lv.3 Atk 30 Hp 4480 Def 120  (model NPC_Nan_015)
#   61101 Office lady Lv.6 Atk 90 Hp 2500 Def 150 (model NPC_Nv_002)  (boss)
NPC_KINDS = {
    1: {"name": "RepairMan", "npcdataid": "21131", "level": 1, "max_hp": 60,
        "damage": 6, "exp": 40, "gold": 80,
        "loot": {1: (0.5, 1), 2: (0.4, 2)}},
    2: {"name": "Horro", "npcdataid": "21132", "level": 2, "max_hp": 120,
        "damage": 12, "exp": 90, "gold": 200,
        "loot": {10: (0.15, 1), 1: (0.6, 2)}},
    3: {"name": "Punk", "npcdataid": "21133", "level": 3, "max_hp": 300,
        "damage": 25, "exp": 300, "gold": 800,
        "loot": {11: (0.08, 1), 20: (0.2, 1)}},
}

# The main open-world map the client loads after character pick.
# npc spawn tables: map_id -> [(kind, x, y, z)]
NPC_SPAWNS = {
    MAIN_CITY_MAP: [(1, 300, 0, 300), (1, 320, 0, 310), (2, 500, 0, 500),
                    (3, 900, 0, 900)],
}

# player base combat values (a weapon's `power` is added to attack)
PLAYER_BASE_ATTACK = 12
PLAYER_BASE_HP = 100
RESPAWN_HP_FRACTION = 1.0

# Starter extras granted on character creation. The real tier-1 armor set
# (helmet/chest/legs/belt/necklace) comes from economy.starter_armor(); the
# weapon comes from the profession's tier-1 weapon. Badges get their own
# system pass later, so only the legacy starter badge is granted here.
STARTER_GEAR = [
    (2, 20),   # Badge of Strength (slot 2)
]

# EQUIP_QUALITY.KUANG_WHITE - the 1-star quality for starter gear.
STARTER_QUALITY = 1

# --- real equipment instances (colors from the recovered tables) -------------
#
# The client colors an item by its gameitem.quality (EQUIP_QUALITY —
# decompiled EQUIP_QUALITY.cs: BLACK=-2 INVALID=-1 WHITE=0 GREEN=1 BLUE=2
# PURPLE=3 YELLOW=4 RED=5) — and per the client's EquipDrop flow the quality
# comes from the item's RANDOM STAT: one stat is rolled from the ATTR_POOLS
# table (recovered EquipDrop rows) and the stat's quality IS the item's
# color. Weapons additionally roll ONE random skill from their skill group;
# the weapon's color is the rolled skill's color.

# ARMOR_ITEMS: equip_id -> {"class", "tier", "pos", "name", "base_attrs"}
# built from the recovered ARMOR_ROWS (client EquipData Position 2..6:
# helmet/chest/legs/belt/necklace).
ARMOR_ITEMS = {}
for _key, (_eid, _aname, _attrs, _q) in GD.ARMOR_ROWS.items():
    _cls, _tier, _pos = (int(x) for x in _key.split("-"))
    ARMOR_ITEMS[_eid] = {
        "class": _cls, "tier": _tier, "pos": _pos, "name": _aname,
        "base_attrs": list(_attrs),
    }
    # register as a real equipment item so equip/sell/loot flows work; the
    # equip slot comes from the recovered EquipData Position (see slot_for).
    ITEMS.setdefault(_eid, {
        "name": _aname, "type": "equipment", "price": 0,
        "base_attrs": list(_attrs), "pos": _pos,
    })


# db equip slot = client EQUIP_BACKPACK_TYPE (WEAPON=0, HEAD=1, BODY=2,
# LEG=3, BELT=4, NECKLACE=5). The recovered armor rows store the client's
# EquipData Position 2..6 (helmet..necklace); map them straight through:
# position p -> slot p-1. Badges/fashion keep the legacy slots 8/9 on the
# server so they never collide with the six real equip slots.
ARMOR_DB_SLOT_OFFSET = -1
BADGE_DB_SLOT = 8
FASHION_DB_SLOT = 9


# fashion db slots: FASHION_DB_SLOT + client FASHION_EQUIPPACK index
# (0 head / 1 body / 2 weapon / 3 leg) -> 9..12
FASHION_DB_SLOT_BASE = 9


def fashion_slot_for(item_id: int):
    """db equip slot for a fashion piece (9..12), or None."""
    idef = ITEMS.get(item_id)
    if idef is None or idef.get("type") != "fashion":
        return None
    if "fashion_slot" in idef:
        return FASHION_DB_SLOT_BASE + idef["fashion_slot"]
    return FASHION_DB_SLOT


def slot_for(item_id: int):
    """db equip slot for an item id, or None if it is not equipment."""
    idef = ITEMS.get(item_id)
    if idef is None:
        return None
    if idef.get("type") == "badge":
        return BADGE_DB_SLOT
    if idef.get("type") == "fashion":
        return fashion_slot_for(item_id)
    if idef.get("type") != "equipment":
        return None
    if idef.get("slot") == 0 or "weapon_class" in idef:
        return 0                       # weapon
    if "pos" in idef:
        return idef["pos"] + ARMOR_DB_SLOT_OFFSET   # client Position -> slot
    return idef.get("slot")            # legacy placeholders


def starter_armor(profession: int):
    """[(db_slot, armor_id)] — the real tier-1 armor set for a profession."""
    out = []
    for pos in (2, 3, 4, 5, 6):
        row = GD.ARMOR_ROWS.get("%d-1-%d" % (profession, pos))
        if row is not None:
            out.append((pos + ARMOR_DB_SLOT_OFFSET, row[0]))
    return out


# The random stat's ATTR_POOLS quality (0..3) IS the EQUIP_QUALITY wire
# value (WHITE=0 GREEN=1 BLUE=2 PURPLE=3).
QUALITY_WIRE = {0: 0, 1: 1, 2: 2, 3: 3}
# roll weights: white 45% / green 30% / blue 18% / purple 7%
QUALITY_WEIGHTS = ((0, 45), (1, 30), (2, 18), (3, 7))


def _roll_quality(rng):
    total = sum(w for _, w in QUALITY_WEIGHTS)
    roll = rng.randrange(total)
    acc = 0
    for q, w in QUALITY_WEIGHTS:
        acc += w
        if roll < acc:
            return q
    return 0


def _pick_attr(pool, rng):
    """Weighted pick from an ATTR_POOLS entry list (attr_id, q, value, w)."""
    total = sum(e[3] for e in pool)
    roll = rng.randrange(total)
    acc = 0
    for entry in pool:
        acc += entry[3]
        if roll < acc:
            return entry
    return pool[0]


def _pool_for(cls: int, tier: int, q: int):
    pool = GD.ATTR_POOLS.get("%d-%d-%d" % (cls, tier, q))
    if pool is None:
        pool = GD.ATTR_POOLS.get("%d-%d-0" % (cls, tier), [])
    return pool


# Skill rarity (the weapon skill's color): the client's SkillQualityData
# table (recovered, keyed by skillId) carries the base skill id + the quality
# weight table (white 100 / green 40 / blue 15 / purple 5 — 1 : 0.4 : 0.15 :
# 0.05 odds). Weapon skills are IDs in the class's BaseSkills group and the
# ROLLED QUALITY is what colors both the skill and the weapon itself.
SKILL_QUALITY_WEIGHTS = ((0, 100), (1, 40), (2, 15), (3, 5))
# per-quality skill multiplier (QualityData ModulusVal on the client): the
# higher-rarity roll multiplies the skill's damage/fvalue contribution.
SKILL_QUALITY_MODULUS = {0: 1.0, 1: 1.1, 2: 1.25, 3: 1.5}


def _roll_skill_quality(rng):
    total = sum(w for _, w in SKILL_QUALITY_WEIGHTS)
    roll = rng.randrange(total)
    acc = 0
    for q, w in SKILL_QUALITY_WEIGHTS:
        acc += w
        if roll < acc:
            return q
    return 0


def roll_weapon_instance(weapon_id: int, rng=None):
    """(quality_wire, attrs) for a weapon.

    The weapon's attack is its base BSValue atk (attr 1001), NEVER a skill.
    The rolled skill comes ONLY from the class's 6-skill pool
    (game_data.WEAPON_SKILL_POOL — the basic attack x01 is excluded) at a
    rarity drawn from the recovered SkillQualityData weights; the weapon's
    color IS the rolled skill's rarity. The attr entry carries (index,
    attr_id, value, quality, skillId) — skillId is what the client shows as
    the weapon's colored skill, quality is EQUIP_QUALITY 0..3.
    """
    import random as _random
    from . import game_data as GD
    rng = rng or _random
    w = ITEMS.get(weapon_id, {})
    pool = GD.WEAPON_SKILL_POOL.get(w.get("weapon_class", 0)) \
        or [x for x in w.get("skills", []) if x % 100 != 1] or [102]
    skill = rng.choice(pool)
    q = _roll_skill_quality(rng)
    wire_q = QUALITY_WIRE[q]
    # ONLY the rolled skill rides random_attri (skillId at field 4) — the
    # client's weapon info panel lists every random_attri entry carrying a
    # skillId, so a base-atk entry here would render as a second "attack"
    # skill. The base attack is the weapon's EquipData BSValue atk: it is
    # applied server-side from weapon_base_atk() and never sent as a
    # random_attri entry.
    return wire_q, [(0, 0, 0, wire_q, str(skill))]


def roll_armor_instance(armor_id: int, rng=None):
    """(quality_wire, attrs) for a real armor piece.

    The instance blob carries ONLY the 1-2 random bonus stats (tier 1-2 ->
    1 stat, tier 3+ -> 2 stats). The base status row (HP/def/...) is NOT
    included: the client reads the base attrs from its own EquipData table,
    so anything else in random_attri renders as an extra random stat (that
    is why pieces showed the basic status as a "random status"). The rolled
    stats come from the real client attribute-id pool (1001..1007/1012/1013
    per ATTR_POOLS), and the best roll's quality colors the piece.
    """
    import random as _random
    rng = rng or _random
    info = ARMOR_ITEMS.get(armor_id)
    if info is None:
        return 1, []
    n_random = 2 if info.get("tier", 1) >= 3 else 1
    rolls = roll_random_attrs(n_random, rng)
    best_q = 0
    attrs = []
    for slot, aid, val, rq in rolls:
        best_q = max(best_q, rq)
        attrs.append((slot, aid, val, QUALITY_WIRE[rq], ""))
    if not attrs:
        # fallback: one plain roll so the piece is never stat-less
        aid, lo, hi = RANDOM_ATTR_POOL[0]
        attrs = [(0, aid, rng.randint(lo, hi), QUALITY_WIRE[0], "")]
    return QUALITY_WIRE[best_q], attrs


# Random attribute roll pool for freshly created gear (gameitem
# random_attri entries). Attr ids are the client's REAL attribute ids
# (GetAttributeName_S / ATTRIBUTE_ICON): 1001 atk, 1002 hp, 1003 def,
# 1004 hit, 1005 eva, 1006 cri, 1007 res, 1012/1013 = the percent stats
# (value shown as value/10000 %). The pool holds ONLY random bonus stats —
# the equipment's base status comes from the client's own EquipData row and
# must never appear as a random roll.
RANDOM_ATTR_POOL = [
    (1001, 8, 40),      # atk
    (1002, 50, 300),    # hp
    (1003, 3, 20),      # def
    (1004, 5, 40),      # hit
    (1005, 3, 25),      # eva
    (1006, 2, 18),      # cri
    (1007, 2, 18),      # res
    (1012, 100, 600),   # %stat (value/10000)
]
# the gameitem random_attri array supports up to 8 bonus slots
RANDOM_ATTR_SLOTS = 8


def roll_random_attrs(count: int = 2, rng=None):
    """Roll `count` DISTINCT random attributes from RANDOM_ATTR_POOL.

    Returns [(slot, attr_id, value, quality)] for gameitem.random_attri —
    slot is the random_attri SLOT (0..7), quality is the roll's rarity
    (0..3) which the client colors the stat line AND (best roll) the piece.
    """
    import random as _random
    rng = rng or _random
    picked = rng.sample(RANDOM_ATTR_POOL, min(count, len(RANDOM_ATTR_POOL)))
    out = []
    for slot, (aid, lo, hi) in enumerate(picked):
        out.append((slot, aid, rng.randint(lo, hi), _roll_quality(rng)))
    return out
# skills: real per-class skill groups from SkillData merged over the legacy
# generic set
SKILLS = {
    1: {"name": "Basic Attack", "damage": 5},
    2: {"name": "Heavy Strike", "damage": 15},
    3: {"name": "Power Blow", "damage": 30},
}
SKILLS.update(REAL_SKILLS)

# --- character attributes + power (the client's real formulas) --------------
#
# CharacterAttributeData (Assembly-CSharp.dll) is driven entirely by the
# server's `attribute`/`attribute_all` sproto objects: base attrs in
# `attribute`, base+equipment+skill totals in `attribute_all`. CombValue is
# SERVER-AUTHORITATIVE (attribute_other.combValue — every UI just prints it),
# and per GameItem.GetItemCombatVal the server-side power contribution of a
# piece of gear is Σ(attr value × GET_ATTRIBUTE_COMBAT_VAL(attid)) with the
# per-profession weights in game_data.ATTRIBUTE_COMBAT_VAL.

# Base character attributes (the revival's baseline — the client adds the
# gear/skill contributions on top of whatever the server sends).
CHAR_BASE_ATTRS = {
    1001: 50,      # atk
    1002: 1000,    # hp
    1003: 25,      # def
    1004: 40,      # hit
    1005: 20,      # dge/eva
    1006: 15,      # cri
    1007: 10,      # res
}
# Level growth: the client's EquipData.LevelScale convention (LevelScale
# 10000 = ×1.0 at item level 0) — each character level adds this fraction of
# the base attrs.
CHAR_LEVEL_SCALE = 0.02


def _attr_weight(profession: int, attr_id: int) -> float:
    return GD.ATTRIBUTE_COMBAT_VAL.get(profession, {}).get(attr_id, 0.0)


def instance_attrs(instance: dict) -> list:
    """[(attr_id, value)] carried by a persisted item instance.

    `attrs` is [(index, attr_id, value, quality, skillId)] in db order
    (the wire format used by gameitem.random_attri).
    """
    return [(a[1], a[2]) for a in instance.get("attrs", [])
            if len(a) > 2 and a[2]]


def instance_combat_value(profession: int, instance: dict,
                          item_id: int) -> int:
    """GameItem.GetItemCombatVal() for one equipped instance.

    Equip: Σ(base attrs + random attrs) × profession weight.
    Weapons (client SubType 0) EXCLUDE random attrs (the client checks
    mItemData.SubType != 0 — the random slot on a weapon is its skill, whose
    power rides the character skill group instead).
    """
    idef = ITEMS.get(item_id, {})
    is_weapon = idef.get("slot") == 0 or "weapon_class" in idef
    total = 0.0
    # base attrs (client EquipData row) — part of GetItemCombatVal
    for aid, val in armor_base_attrs(item_id):
        total += val * _attr_weight(profession, aid)
    if not is_weapon:
        # random rolls (client skips them for weapons: SubType == 0)
        for a in instance.get("attrs", []):
            val = a[2] if len(a) > 2 else 0
            if val:
                total += val * _attr_weight(profession, a[1])
    else:
        # the weapon's base atk comes from the EquipData row
        atk = weapon_base_atk(item_id)
        if atk:
            total += atk * _attr_weight(profession, 1001)
    return int(total)


def weapon_skill_bonus(profession: int, instance: dict,
                       item_id: int) -> int:
    """Combat contribution of a weapon's rolled skill.

    SkillData.fvalue is the skill's power value; the client's
    GetAttrValByQualityAndLevel applies the quality ModulusVal (QualityData)
    — replicated here with SKILL_QUALITY_MODULUS so rarity raises power.
    """
    idef = ITEMS.get(item_id, {})
    if idef.get("slot") != 0 and "weapon_class" not in idef:
        return 0
    for a in instance.get("attrs", []):
        skill = a[4] if len(a) > 4 else None
        if skill:
            try:
                sid = int(skill)
            except (TypeError, ValueError):
                continue
            sdef = SKILLS.get(sid) or {}
            fvalue = sdef.get("damage", 0)
            q = a[3] if len(a) > 3 and a[3] in SKILL_QUALITY_MODULUS else 0
            return int(fvalue * SKILL_QUALITY_MODULUS[q]
                       * _attr_weight(profession, 1001))
    return 0


def character_attributes(db, char_id: int, level: int,
                         profession: int) -> dict:
    """Final attribute map for a character: base + level growth + every
    equipped piece's BASE attrs (client EquipData rows, server-side since
    the instance blobs carry only random rolls) + every instance's random
    rolls + the weapon skill bonus.

    Recomputed ONLY on the change events (equip/unequip/upgrade/chest/
    level-up) and persisted into characters.data — never at login.
    """
    attrs = dict(CHAR_BASE_ATTRS)
    growth = 1.0 + CHAR_LEVEL_SCALE * max(0, level - 1)
    for aid in attrs:
        attrs[aid] = int(attrs[aid] * growth)
    total_power = 0.0
    for inst in db.list_equipped_instances(char_id):
        item_id = inst["item_id"]
        total_power += instance_combat_value(profession, inst, item_id)
        total_power += weapon_skill_bonus(profession, inst, item_id)
        # base attrs of the piece (EquipData row) apply server-side
        for aid, val in armor_base_attrs(item_id):
            attrs[aid] = attrs.get(aid, 0) + val
        # weapons: the base attack is the EquipData BSValue atk
        w_atk = weapon_base_atk(item_id)
        if w_atk:
            attrs[1001] = attrs.get(1001, 0) + w_atk
        # random rolls from the persisted instance
        for aid, val in instance_attrs(inst):
            attrs[aid] = attrs.get(aid, 0) + val
    # skills: each learned skill level adds a flat power tick (SkillData
    # fvalue scaled by level — IsUpgrade==1 skills only on the client).
    for row in db.list_skills(char_id):
        sdef = SKILLS.get(row["skill_id"]) or {}
        if sdef.get("damage"):
            total_power += sdef["damage"] * max(0, row["level"] - 1) \
                * _attr_weight(profession, 1001) * 0.1
    attrs["power"] = int(total_power)
    return attrs


def weapon_base_atk(item_id: int) -> int:
    """The weapon's EquipData BSValue atk (server-side base attack)."""
    w = ITEMS.get(item_id, {})
    if w.get("slot") != 0 and "weapon_class" not in w:
        return 0
    return w.get("atk", 0) or w.get("power", 0) or 0


def armor_base_attrs(item_id: int) -> list:
    """[(attr_id, value)] base attrs of an armor piece from its recovered
    EquipData row (ARMOR_ROWS), matching what the client displays as the
    piece's base status."""
    info = ARMOR_ITEMS.get(item_id)
    return list(info["base_attrs"]) if info else []


# --- character random status -------------------------------------------------
# One genuinely random bonus status per character, rolled ONCE at creation and
# stored in characters.data["random_status"]. It is independent of the base
# status: the base row is never copied into it, and it is never re-rolled or
# overwritten at login — loaded verbatim from the account.
CHAR_RANDOM_STATUS_POOL = [
    (1001, 3, 10),    # atk
    (1002, 30, 120),  # hp
    (1003, 2, 8),     # def
    (1004, 2, 8),     # hit
    (1005, 1, 6),     # eva
    (1006, 1, 4),     # cri
    (1007, 1, 4),     # res
]


def roll_character_random_status(db, char_id: int, rng=None) -> dict:
    """Roll the character's single random status ONCE and persist it.

    Returns the saved {attr_id: value}. If the account already has one
    (migration for existing accounts), the stored value is returned
    unchanged — never regenerated, never replaced by the base status.
    """
    import random as _random
    rng = rng or _random
    saved = db.get_random_status(char_id)
    if saved:
        return saved
    aid, lo, hi = rng.choice(CHAR_RANDOM_STATUS_POOL)
    status = {aid: rng.randint(lo, hi)}
    db.set_random_status(char_id, status)
    return status


def recalc_character(db, char_id: int) -> dict:
    """Recompute + persist (characters.data) the attribute set; returns it."""
    row = db.get_character(char_id)
    if row is None:
        return {}
    attrs = character_attributes(db, char_id, row["level"], row["profession"])
    # the character's random status rides the final attribute set
    for aid, val in (db.get_random_status(char_id) or {}).items():
        attrs[aid] = attrs.get(aid, 0) + val
    db.save_attributes(char_id, attrs)
    max_hp = attrs.get(1002, 100)
    hp, _old_max = db.get_hp(char_id)
    db.set_max_hp(char_id, max_hp)
    if hp > max_hp:
        db.set_hp(char_id, max_hp)
    return attrs
# Wave-based PvE instances entered from the open world (client flow:
# enter_copy_scene -> npc_create per wave -> single_copy_scene_npc_die ->
# next_wave -> copy_scene_result). The client drives combat; the server
# validates reports and pays rewards on success.
#
# copy_id -> {"name", "waves": [[npc kind, ...], ...], "reward": {...},
#             "countdown": seconds per wave}
COPY_SCENES = {
    1: {
        "name": "Back Alley Brawl",
        "waves": [[1, 1], [1, 1, 2]],
        "countdown": 60,
        "reward": {"gold": 1500, "diamond": 1, "items": {1: 2}, "exp": 120},
    },
    2: {
        "name": "Docks Raid",
        "waves": [[2, 1], [2, 2], [3]],
        "countdown": 90,
        "reward": {"gold": 5000, "diamond": 3, "items": {20: 1}, "exp": 400},
    },
}

# --- tower (climb endless npc floors) ----------------------------------------
# client flow: request_tower_copy_info -> enter_tower_copy_info ->
# fight (single_copy_scene_npc_die) -> grant_tower_reward per floor block
TOWER = {
    "max_floor": 100,
    "floors_per_reward_block": 5,
    "gold_per_floor": 150,
    "exp_per_floor": 60,
    "reset_diamond_cost": 20,
}

# --- rank pvp (tianTi ladder) ------------------------------------------------
# client flow: request_random_rank_pvp_opponent -> rank_pvp_start ->
# simulated 1v1 resolved server-side from reported attacks
# (rank_pvp_player_attack / rank_pvp_other_player_die) -> tiantti_result
RANK_PVP = {
    "base_score": 1000,
    "win_score": 25,
    "lose_score": -15,
    "win_gold": 1200,
    "win_diamond": 2,
    "win_count_reward": 500,     # gold per 5 cumulative wins
}

# --- slot machine ------------------------------------------------------------
# three reels of 0..5; three of a kind pays 10x, a pair pays 2x
SLOT = {
    "spin_cost": 100,
    "reels": 6,
    "triple_multiplier": 10,
    "pair_multiplier": 2,
}

# --- wild boss (open-world raid boss) ----------------------------------------
# client flow: request_wild_boss_info(200) -> enter_wild_boss(201) ->
# fight via the standard combat tags -> shared HP pool per map; respawns
# on demand at full strength once killed
WILD_BOSS = {
    "kind": 3,                      # Mob Boss stats
    "spawn": {"x": 1200, "y": 0, "z": 1200, "o": 0},
    "countdown": 120,
}

# --- survive (survival assault) ----------------------------------------------
# client flow: request_survive_top(245) -> enter_survive_batttle(246) ->
# endless escalating npc waves (kills reported via single_copy_scene_npc_die)
# -> survive_battle_finish(637) pays scaled rewards and records the best wave
SURVIVE = {
    "countdown": 90,
    "reward": {"gold": 300, "exp": 100},   # multiplied by the wave reached
}
