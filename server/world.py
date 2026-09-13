"""World state: per-map player + NPC registry with AOI broadcast helpers.

The original game used interest-management pushes (aoi_add / aoi_remove /
aoi_update_move ...). This revival keeps it simple: every player in the same
map + line sees every other player and every NPC in that map + line, and
movement/chat/combat are broadcast to the map.

NPCs are server-simulated: they stand at their spawn point, take damage from
player attacks, die, drop loot + exp + gold, and respawn after a delay.
"""

import random

from . import economy
from . import protocol as P


class WorldPlayer:
    __slots__ = ("conn", "char_id", "name", "level", "sex", "profession",
                 "map_id", "line_index", "pos", "moving", "walk", "dead",
                 "comb_value", "fashion_parts", "weapon_item_id",
                 "fashion_item_id")

    def __init__(self, conn, char_id: int, name: str, level: int = 1,
                 sex: int = 0, profession: int = 0) -> None:
        self.conn = conn
        self.char_id = char_id
        self.name = name
        self.level = level
        self.sex = sex
        self.profession = profession
        self.map_id = economy.MAIN_CITY_MAP
        self.line_index = 0
        self.pos = {"x": 0, "y": 0, "z": 0, "o": 0}
        self.moving = False
        self.walk = True
        self.dead = False
        self.comb_value = 100 * level
        # fashion look carried into the spawn blob's characterVisual
        self.fashion_parts = (None, None, None, None)
        self.weapon_item_id = None
        self.fashion_item_id = None

    def movement_blob(self) -> bytes:
        return P._enc.encode_object({
            0: P.encode_position(**self.pos),
        })


class WorldNpc:
    __slots__ = ("npc_id", "kind", "map_id", "pos", "hp", "max_hp",
                 "dead", "level", "name")

    _next_id = [9000]

    def __init__(self, kind: int, map_id: str, pos: dict) -> None:
        WorldNpc._next_id[0] += 1
        self.npc_id = WorldNpc._next_id[0]
        kind_def = economy.NPC_KINDS[kind]
        self.kind = kind
        self.name = kind_def["name"]
        self.level = kind_def["level"]
        self.map_id = map_id
        self.pos = dict(pos)
        self.max_hp = kind_def["max_hp"]
        self.hp = self.max_hp
        self.dead = False

    def blob(self) -> bytes:
        return P.encode_npc(self.npc_id, self.kind, self.level, self.hp,
                            self.max_hp, self.pos)


class World:
    def __init__(self) -> None:
        # map_id -> {char_id: WorldPlayer}
        self.maps: dict = {}
        # map_id -> {npc_id: WorldNpc}
        self.npcs: dict = {}
        # map_id -> the live wild boss (raid boss) WorldNpc, if spawned
        self.bosses: dict = {}
        self._spawn_npcs()

    def _spawn_npcs(self) -> None:
        for map_id, spawns in economy.NPC_SPAWNS.items():
            for kind, x, y, z in spawns:
                npc = WorldNpc(kind, map_id, {"x": x, "y": y, "z": z, "o": 0})
                self.npcs.setdefault(map_id, {})[npc.npc_id] = npc

    # -- players --------------------------------------------------------
    def join(self, player: WorldPlayer) -> None:
        self.maps.setdefault(player.map_id, {})[player.char_id] = player

    def leave(self, player: WorldPlayer) -> None:
        m = self.maps.get(player.map_id)
        if m and player.char_id in m:
            del m[player.char_id]
            if not m:
                del self.maps[player.map_id]
        # notify everyone else
        self.broadcast(player.map_id, P.AOI_REMOVE,
                       {0: _encode_aoi_remove(player.char_id)},
                       exclude=player.char_id)

    def others(self, map_id: str, exclude_char_id: int):
        return [p for p in self.maps.get(map_id, {}).values()
                if p.char_id != exclude_char_id]

    def get(self, map_id: str, char_id: int):
        return self.maps.get(map_id, {}).get(char_id)

    def get_player_anywhere(self, char_id: int):
        for m in self.maps.values():
            if char_id in m:
                return m[char_id]
        return None

    def npcs_in(self, map_id: str):
        return list(self.npcs.get(map_id, {}).values())

    def get_npc(self, map_id: str, npc_id: int):
        return self.npcs.get(map_id, {}).get(npc_id)

    # -- messaging ------------------------------------------------------
    def broadcast(self, map_id: str, tag: int, body: dict,
                  exclude: int = None, session: int = None) -> None:
        frame = P.encode_frame(tag, session, body)
        for p in self.maps.get(map_id, {}).values():
            if exclude is not None and p.char_id == exclude:
                continue
            p.conn.send_raw(frame)

    # -- combat -----------------------------------------------------------
    def player_attack(self, player: WorldPlayer, attack: int) -> int:
        return max(1, attack + random.randint(-2, 2))

    def npc_attack(self, npc: WorldNpc) -> int:
        kind_def = economy.NPC_KINDS[npc.kind]
        return max(1, kind_def["damage"] + random.randint(-1, 1))

    def kill_npc(self, npc: WorldNpc, char_id: int, char_name: str):
        """Kill an NPC; returns (exp, gold, drops {item_id: count})."""
        kind_def = economy.NPC_KINDS[npc.kind]
        npc.dead = True
        npc.hp = 0
        rng = random.Random()
        drops = {}
        for item_id, (chance, count) in kind_def["loot"].items():
            if rng.random() < chance:
                drops[item_id] = drops.get(item_id, 0) + count
        return kind_def["exp"], kind_def["gold"], drops

    def respawn_npc(self, npc: WorldNpc) -> None:
        kind_def = economy.NPC_KINDS[npc.kind]
        npc.dead = False
        npc.hp = npc.max_hp


# --- wire blob helpers shared by handlers -----------------------------------

def _encode_aoi_remove(char_id: int) -> bytes:
    # SprotoType.aoi_remove.request {characterId(0)}
    return P._enc.encode_object({0: char_id})


# --- wire schemas, straight from the decompiled Assembly-CSharp.dll ----------
#
# The client's sproto types are distinguished ONLY by tag order, so every
# blob must use the exact wire tags of the matching SprotoType.* class.
# WARNING: the has_field bitset indices in the decompiled classes are NOT
# the wire tags — always read the decode() switch.
#
# SprotoType.character (main_player_create): id(0) general(1)
#   attribute_other(2) property(5) visual(6) movement(7) skills(8)
#   runtime(13) download(15) skill_index(16)
# SprotoType.character_aoi (aoi_add): id(0) visual(1) general(2)
#   attribute_other(3) movement(5) runtime(6)
# SprotoType.character_overview (character_list / character_create resp):
#   id(0) general(1) attribute_other(2, attribute_overview) visual(3)
#   createtime(4) forbidden(5)
#
# Sub-schemas (tags the client hard-dereferences in ObjInitPlayerData /
# main_player_create_handler / CreateMainPlayer — a missing OBJECT crashes
# the handler and the loading widget hangs forever):
#   general:            name(0) profession(1) lineIndex(2) mapInfoId(3)
#                       tutorial(4)
#   attribute_other:    hp(0) exp(1) level(2) combValue(3) camp(15)
#                       pkMode(16) dance_state(17) dance_id(18)
#   attribute_overview: level(0) combValue(1)
#   property:           money1(13)..money6(18)
#   visual:             name(0) ModeId(1) HeadId(2) BodyId(3) LegId(4)
#                       WeaponId(5) showType(10) MountId(12) mount_state(13)
#                       mount_color(14)
#   runtime_agent:      attribute(6) attribute_all(7)  (both SprotoType.attribute)
#   attribute (SprotoType.attribute.cs, 25 fields — CharacterAttributeData.
#   InitData reads ALL of these; exd/exr/crd/crr/anti_stun/anti_knock_down
#   are ×10000 fixed-point, speed = mov/100):
#     max_hp(0) exp(1) atk(2) def(3) hit(4) eva(5) cri(6) res(7) exd(8)
#     exr(9) crd(10) crr(11) defa(12) mov(13) rec(14) anti_stun(15)
#     anti_knock_down(16) dgea(17) resa(18) hita(19) cria(20) ate(21)
#     satm(22) satc(23) satp(24)
#
# Client EQUIP_BACKPACK_TYPE slots: WEAPON=0 HEAD=1 BODY=2 LEG=3 BELT=4
# NECKLACE=5. The db adds badge(8)/fashion(9) so all indexes stay unique.
# On the character.equip(9) map the indexId (slot+1) keys the gameitem.

# CharacterModelData row ids (from the APK's Data.bundle): 100=XD_A
# (Batfighter), 104=QJ_A (Boxer), 105=NQS_A (Gunner). Body parts live in
# the ModelData table: *_WQ weapon / *_T head / *_S body / *_X legs
# (their ModelType ints map onto the client's MODEL_TYPE enum 0..3).
PROFESSION_MODELS = {
    0: ("100", "XD_A"),
    1: ("104", "QJ_A"),
    2: ("105", "NQS_A"),
}


# Default movement speed the client derives as attribute_all.mov / 100.
_DEFAULT_MOV = 500
_DEFAULT_HP = 120


def _general_blob(name: str, profession: int, line_index: int = 0,
                  map_id: str = economy.MAIN_CITY_MAP,
                  tutorial: int = None) -> bytes:
    """SprotoType.general: name(0) profession(1) lineIndex(2) mapInfoId(3)
    tutorial(4). `tutorial` drives the client's IsTutorialFinish —
    ChooseRoleRootLogic sets PlayerData.IsTutorialFinish =
    general.HasTutorial && general.tutorial == 1, and
    NewTutorialSceneManager only runs the tutorial sequence when that flag
    is false. Existing accounts MUST get tutorial=1 or the tutorial
    replays on every login."""
    fields = {
        0: name, 1: profession, 2: line_index, 3: map_id,
    }
    if tutorial is not None:
        fields[4] = tutorial
    return P._enc.encode_object(fields)


def _visual_blob(profession: int, name: str, show_type: int = 0,
                 fashion_parts: tuple = None,
                 weapon_item_id: str = None,
                 fashion_item_id: str = None) -> bytes:
    """SprotoType.characterVisual — UpdateMainPlayerVisual/ResetMainPlayer
    read the fashion part ids (6-9: Fashion_Head/Body/Leg/Weapon), the
    WeaponItemId/FashionItemId (14/15) and showType (10). Fashion part ids
    default to the normal part when absent (client rule: HasFashion_X ?
    Fashion_X : X), so the model renders the worn fashion set on spawn
    instead of always the default skin."""
    model_id, base = PROFESSION_MODELS.get(profession, PROFESSION_MODELS[0])
    fp = fashion_parts or (None, None, None, None)
    fields = {
        0: name,
        1: model_id,          # ModeId -> CharacterModelData row
        2: base + "_T",       # HeadId
        3: base + "_S",       # BodyId
        4: base + "_X",       # LegId
        5: base + "_WQ",      # WeaponId
        10: show_type,        # showType: 1 = wearing fashion, 0 = normal
        12: "",               # MountId
        13: 0,                # mount_state
        14: "",               # mount_color
    }
    # only send the fashion fields when the fashion look is actually shown —
    # otherwise leave them absent (the client falls back to the base parts)
    if show_type == 1:
        head, body, weapon, leg = fp
        for tag, val in ((6, head), (7, body), (8, leg), (9, weapon)):
            if val:
                fields[tag] = val
        if weapon_item_id:
            fields[14] = str(weapon_item_id)
        if fashion_item_id:
            fields[15] = str(fashion_item_id)
    return P._enc.encode_object(fields)


def _attribute_blob(hp: int, exp: int, atk: int = 10, attrs: dict = None) -> bytes:
    """Full SprotoType.attribute — CharacterAttributeData.InitData reads every
    field, so all 25 arrive (values from the persisted attribute set when
    given; the ×10000 fields are the client's fixed-point convention)."""
    attrs = attrs or {}
    return P._enc.encode_object({
        0: hp,                    # max_hp
        1: exp,                   # exp
        2: attrs.get(1001, atk),  # atk
        3: attrs.get(1003, 2),    # def
        4: attrs.get(1004, 10),   # hit
        5: attrs.get(1005, 5),    # eva (DGE)
        6: attrs.get(1006, 0),    # cri
        7: attrs.get(1007, 0),    # res
        8: 0, 9: 0,               # exd / exr (×10000)
        10: 0, 11: 0,             # crd / crr (×10000)
        12: 0,                    # defa
        13: _DEFAULT_MOV,         # mov -> client speed = mov / 100
        14: 0,                    # rec
        15: 0, 16: 0,             # anti_stun / anti_knock_down (×10000)
        17: 0, 18: 0,             # dgea / resa
        19: 0, 20: 0,             # hita / cria
        21: 0,                    # ate
        22: 0, 23: 0, 24: 0,      # satm / satc / satp
    })


def _runtime_blob(hp: int, exp: int, attrs: dict = None) -> bytes:
    attr = _attribute_blob(hp, exp, attrs=attrs)
    return P._enc.encode_object({6: attr, 7: attr})


def _attribute_other_blob(hp: int, exp: int, level: int,
                          comb_value: int = 0) -> bytes:
    return P._enc.encode_object({
        0: hp, 1: exp, 2: level,
        3: comb_value,        # combValue (combat power shown on the profile)
        4: 0, 5: 0,           # title_level / title_exp
        15: 0,                # camp
        16: 0,                # pkMode
        17: 0,                # dance_state
        18: "",               # dance_id
    })


def _property_blob(gold: int = 0, diamond: int = 0) -> bytes:
    return P._enc.encode_object({13: gold, 14: diamond, 15: 0, 16: 0,
                                 17: 0, 18: 0})


def _attribute_overview_blob(level: int, comb_value: int = 0) -> bytes:
    return P._enc.encode_object({0: level, 1: comb_value})


def _default_hp(level: int) -> int:
    return _DEFAULT_HP + 20 * max(0, level - 1)


def _char_stats(level: int, exp: int = 0):
    """(hp, exp) pair used by the character blobs."""
    return _default_hp(level), exp


def encode_character_blob(char_id: int, name: str, level: int,
                          pos_blob: bytes, profession: int = 0,
                          line_index: int = 0,
                          map_id: str = economy.MAIN_CITY_MAP,
                          exp: int = 0, gold: int = 0, diamond: int = 0,
                          hp: int = None, skills: list = None,
                          comb_value: int = 0,
                          equips: list = None,
                          attrs: dict = None,
                          badge_equips: list = None,
                          fashion_equips: list = None,
                          show_type: int = 0,
                          fashion_parts: tuple = None,
                          weapon_item_id: str = None,
                          fashion_item_id: str = None) -> bytes:
    """Full SprotoType.character blob for main_player_create.

    The client's ObjInitPlayerData.InitData(character) hard-dereferences
    general, attribute_other, property (money1..6), visual, movement and
    runtime.attribute_all — every one of those objects must be present at
    its exact wire tag or the handler throws and the main player never
    spawns (eternal loading). download=2 also marks the client as fully
    downloaded (main_player_create_handler sets IsFinishDownload).

    `skills` is an optional [(skill_id, level)] list encoded at tag 8 as
    map<string, skill_info>; skillId is decoded with read_string, so the id
    MUST be a string ("101"), never an integer.

    `attrs` is the persisted attribute map (economy.CHAR_BASE_ATTRS + gear);
    it fills both runtime.attribute and runtime.attribute_all so the client's
    CurATK/CurDEF/... match the server-authoritative combValue.
    """
    if hp is None:
        hp, _ = _char_stats(level, exp)
    if attrs is not None:
        # max_hp (attribute field 0) comes from the persisted attribute set.
        hp = attrs.get(1002, hp)
    fields = {
        0: char_id,
        1: _general_blob(name, profession, line_index, map_id),
        2: _attribute_other_blob(hp, exp, level, comb_value),
        5: _property_blob(gold, diamond),
        6: _visual_blob(profession, name, show_type,
                        fashion_parts=fashion_parts,
                        weapon_item_id=weapon_item_id,
                        fashion_item_id=fashion_item_id),
        7: pos_blob,
        13: _runtime_blob(hp, exp, attrs),
        15: 2,                # download = 2 -> IsFinishDownload = true
    }
    if skills:
        skill_blobs = [
            P.encode_skill_info(sid, lvl, index_pos=(s[2] if len(s) > 2
                                                     else 0))
            for s in skills for sid, lvl in [s[:2]]
        ]
        fields[8] = P._enc.encode_object_array(skill_blobs)
        fields[16] = 0        # skill_index: hard-dereferenced by InitData
    if equips:
        # character.equip(9): map<indexId, gameitem> of EQUIPPACK items.
        # The client SyncPacks these into its EQUIPPACK container at spawn,
        # which is what puts the gear on the character's back.
        equip_blobs = [P.encode_gameitem(idx, iid, stack=1, quality=q,
                                         level=lvl, random_attris=attrs_)
                       for idx, iid, q, lvl, attrs_ in equips]
        fields[9] = P._enc.encode_object_array(equip_blobs)
    if badge_equips:
        # character.badge_equip(10): map<indexId, gameitem> of BADGE_EQUIPPACK.
        # The spawn handler resolves each entry with GetItemByIndex((int)
        # gameitem.parm[0]) — parm[0] MUST carry the badge's equip position
        # (0), and parm is an int-list of single-field objects.
        badge_blobs = [P.encode_gameitem(idx, iid, stack=1, quality=q,
                                         level=lvl, random_attris=attrs_,
                                         parm=[0])
                       for idx, iid, q, lvl, attrs_ in badge_equips]
        fields[10] = P._enc.encode_object_array(badge_blobs)
    if fashion_equips:
        # character.fashion_equip(11): map<indexId, gameitem> of
        # FASHION_EQUIPPACK pieces — the wardrobe's worn set at spawn
        fashion_blobs = [P.encode_gameitem(idx, iid, stack=1, quality=q,
                                           level=lvl, random_attris=attrs_)
                         for idx, iid, q, lvl, attrs_ in fashion_equips]
        fields[11] = P._enc.encode_object_array(fashion_blobs)
    return P._enc.encode_object(fields)


def encode_character_aoi_blob(char_id: int, name: str, level: int,
                              pos_blob: bytes, profession: int = 0,
                              line_index: int = 0,
                              map_id: str = economy.MAIN_CITY_MAP,
                              exp: int = 0, hp: int = None) -> bytes:
    """SprotoType.character_aoi blob for aoi_add (NOT SprotoType.character!).

    aoi_add_handler calls ObjInitPlayerData.InitData(character_aoi), which
    hard-dereferences visual, general, attribute_other, movement and
    runtime.attribute_all — at character_aoi's own wire tags.
    """
    if hp is None:
        hp, _ = _char_stats(level, exp)
    return P._enc.encode_object({
        0: char_id,
        1: _visual_blob(profession, name),
        2: _general_blob(name, profession, line_index, map_id),
        3: _attribute_other_blob(hp, exp, level, 100 * level),
        5: pos_blob,
        6: _runtime_blob(hp, exp),
    })


def encode_character_overview(row, visual_profession: int = None,
                              comb_value: int = None,
                              db=None) -> bytes:
    """SprotoType.character_overview for character_list / character_create.

    The client dereferences .general.profession, .attribute_other.level,
    .visual and .createtime on this type (CreateRoleRootLogic /
    ChooseRoleRootLogic), so all four sub-objects must be present.
    attribute_overview.combValue (field 1) is the combat power the role
    select screen shows — a rolled base power, not 0.

    With `db`, general.tutorial (field 4) reflects the account's saved
    tutorial state: 1 once tutorial_finish(306) was received, absent for
    brand-new characters so only they run the tutorial.
    """
    profession = row["profession"] if visual_profession is None \
        else visual_profession
    if comb_value is None:
        comb_value = 100 * row["level"]
    tutorial = None
    if db is not None:
        tutorial = 1 if db.get_progress(row["id"], "tutorial_done") else None
    return P._enc.encode_object({
        0: row["id"],
        1: _general_blob(row["name"], profession, tutorial=tutorial),
        2: _attribute_overview_blob(row["level"], comb_value),
        3: _visual_blob(profession, row["name"]),
        4: row["created_at"],
        5: 0,                 # forbidden
    })


def encode_aoi_add(player: WorldPlayer) -> bytes:
    """SprotoType.aoi_add.request {character(0)} — a character_aoi blob."""
    character = encode_character_aoi_blob(
        player.char_id, player.name, player.level, player.movement_blob(),
        profession=player.profession, line_index=player.line_index,
        map_id=player.map_id)
    return P._enc.encode_object({0: character})


def encode_aoi_update_move(player: WorldPlayer) -> bytes:
    move = P.encode_character_aoi_move(player.char_id, player.movement_blob(),
                                       player.walk)
    return P._enc.encode_object({0: move})


def comb_value_for(db, char_id: int, level: int) -> int:
    """Server-authoritative combValue (attribute_other.combValue — every
    client UI prints this verbatim).

    Formula port: GetItemCombatVal() per equipped instance — Σ(attr ×
    GET_ATTRIBUTE_COMBAT_VAL) with the profession's weights — plus the
    weapon skill bonus and learned-skill ticks, on top of the base
    attribute power. The value is PERSISTED with the attribute set and only
    recomputed on change events (equip/unequip/upgrade/chest/level-up).
    """
    saved = db.load_attributes(char_id)
    if saved.get("power") is not None:
        return int(saved["power"])
    # migration: no saved attribute set yet (first login after this fix, or
    # a brand-new character) — compute from the client formula now.
    row = db.get_character(char_id)
    if row is None:
        return 0
    from . import economy as _eco
    attrs = _eco.character_attributes(db, char_id, row["level"],
                                      row["profession"])
    return int(attrs.get("power", 0))


def encode_main_player_create(player: WorldPlayer,
                              skills: list = None,
                              equips: list = None,
                              attrs: dict = None,
                              hp: int = None,
                              badge_equips: list = None,
                              fashion_equips: list = None,
                              show_type: int = 0) -> dict:
    """Field dict for the main_player_create PUSH body:
    {character(0), movement(1)}.

    The client's NetLogic.ProcessPack decodes a push body DIRECTLY as
    main_player_create.request (GenRequest(tag, buffer, offset, len)), so
    the body must BE the request fields — NOT an extra object wrapping
    them. Wrapping the request in {0: request} makes the client decode the
    request blob itself as SprotoType.character, whose first field is a
    length dword that read_integer rejects:
    "Exception: read invalid integer size (362)" -> the packet handler dies
    and the loading screen hangs forever.

    character is a full SprotoType.character blob (see encode_character_blob);
    a partial one crashes the client's spawn handler and hangs the loading
    screen. `skills` is an optional [(skill_id, level)] list encoded as the
    client's map<string, skill_info> (string skillId key!).
    """
    character = encode_character_blob(
        player.char_id, player.name, player.level, player.movement_blob(),
        profession=player.profession, line_index=player.line_index,
        map_id=player.map_id, skills=skills, equips=equips,
        comb_value=getattr(player, "comb_value", 0),
        attrs=attrs, hp=hp, badge_equips=badge_equips,
        fashion_equips=fashion_equips, show_type=show_type,
        fashion_parts=getattr(player, "fashion_parts", None),
        weapon_item_id=getattr(player, "weapon_item_id", None),
        fashion_item_id=getattr(player, "fashion_item_id", None))
    return {
        0: character,
        1: player.movement_blob(),
    }
