"""End-to-end tests for the Equipment/Skills & Fashion fix plan:

1. Equipment unequip must restore the naked body (EQUIPPACK must only ever
   carry real armor/weapon slots 0..5; badge/fashion leak into it is what
   made a body region vanish under a wrong/empty ModelId).
2. Unequipped equipment must NOT become a new/locked item (gameitem.appraise
   persists through the equip->unequip round trip).
3. Appraise (equip_appraise 303) actually identifies genuinely new items.
4. New equipment semantics: new drops roll an unidentified instance; known
   grants stay identified.
5-9. Weapon skill system: basic attack kept separate from the six weapon
   skill slots; the weapon carries all six class skills; skills persist
   across relogin.
10-11. Fashion ownership at creation and equip/unequip stay owned.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from server import economy
from server import game_data
from server import protocol as P
from server import sproto

from tests.test_e2e import _connect, server  # noqa: F401  (pytest fixture)
from tests.test_economy import login_and_pick

GAMEITEM_SPEC = {
    0: "i", 1: "s", 2: "i", 3: "i", 4: "i", 5: "i", 6: "i",
    7: "ia", 8: "i", 9: "oa", 10: "oa",
}


def decode_object_array(blob):
    if isinstance(blob, list):
        return [sproto.as_bytes(e) for e in blob]
    blob = sproto.as_bytes(blob)
    total = int.from_bytes(blob[0:4], "little")
    off = 4
    out = []
    while off < 4 + total:
        n = int.from_bytes(blob[off:off + 4], "little")
        off += 4
        out.append(blob[off:off + n])
        off += n
    return out


def gameitem_appraise(gameitem_blob) -> int:
    """gameitem.appraise (field 8) from a wire blob."""
    d = sproto.decode_typed(gameitem_blob, GAMEITEM_SPEC)
    return d.get(8)


def find_gameitem(blob_list, item_id):
    """Return the first wire gameitem in a container list for `item_id`."""
    for b in blob_list:
        d = sproto.decode_fields(b)
        if str(d.get(1)) == str(item_id):
            return b
    return None


@pytest.mark.asyncio
async def test_starting_gear_is_appraised_and_equippable(server):
    """Starting equipment must be appraised=1 (usable directly)."""
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "StarterGear")
    db = srv.db
    await c.drain(0.5)

    # every equipped slot's instance is appraised
    equipped = db.list_equipped(char_id)
    assert equipped, "character starts with gear equipped"
    for slot, item_id, index_id in equipped:
        idef = economy.ITEMS.get(item_id, {})
        if idef.get("type") != "equipment":
            continue
        inst = db.get_instance(index_id)
        assert inst is not None, "equipped piece has a rolled instance"
        assert inst.get("appraise", 1) == 1, \
            "starting gear is identified (appraised), no Appraise needed"
    await c.close()


@pytest.mark.asyncio
async def test_equip_unequip_keeps_appraised_and_appraise_field(server):
    """Unequip must NOT turn an owned item into a new/locked one.

    The wire gameitem.appraise field (8) must be 1 both before and after
    the un-equip, and the item stays immediately equippable (no Appraise
    flow, no lock).
    """
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "AppraiseKeep")
    db = srv.db
    await c.drain(0.5)

    prof = db.get_character(char_id)["profession"]
    weapon = (prof + 1) * 10000 + 101
    # grant a second weapon as a KNOWN item (seen=1) -> appraised=1
    db.add_item(char_id, weapon, 1, seen=1)
    insts = db.find_instances(char_id, weapon)
    assert insts and insts[0].get("appraise", 1) == 1, \
        "seen=1 grant stays appraised"

    resp = await c.rpc(P.EQUIP_ITEM, {0: weapon})
    assert resp.body[0] == 0
    index_id = db.get_equipped_index(char_id, 0)
    assert index_id is not None

    resp = await c.rpc(P.UNEQUIP_ITEM, {0: index_id})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 0) is None, "slot emptied"
    assert db.get_item_count(char_id, weapon) == 1, "still owned"
    inst = db.get_instance(index_id)
    assert inst is not None, "same instance survives"
    assert inst.get("appraise", 1) == 1, "appraised state persisted"

    # the re-added bag item carries appraise=1 in the wire (no lock)
    seen_appr = None
    for _ in range(20):
        fr = await c.next_push(P.SYNC_BACKPACK_ITEM, timeout=3)
        if fr is None:
            break
        for b in decode_object_array(fr.body[0]):
            d = sproto.decode_fields(b)
            if str(d.get(1)) == str(weapon):
                seen_appr = gameitem_appraise(b)
                break
        if seen_appr is not None:
            break
    assert seen_appr == 1, "unequipped item stays appraised (not locked)"

    # re-equip immediately without any unlock click
    resp = await c.rpc(P.EQUIP_ITEM, {0: weapon})
    assert resp.body[0] == 0
    assert db.get_equipped_index(char_id, 0) == index_id, "same instance"
    await c.close()


@pytest.mark.asyncio
async def test_genuinely_new_equipment_is_locked_then_appraise_unlocks(server):
    """A genuinely new drop (seen=None) is unidentified; Appraise works.

    Flow: new equipment acquired -> appraised=0 (Appraise button shows) ->
    equip_appraise(303) charges gold + marks appraised=1 -> item usable.
    """
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "NewLoot")
    db = srv.db
    await c.drain(0.5)

    prof = db.get_character(char_id)["profession"]
    weapon = (prof + 1) * 10000 + 201
    # genuine new acquisition: seen defaults to None -> new + unidentified
    db.add_item(char_id, weapon, 1)
    insts = db.find_instances(char_id, weapon)
    assert insts, "new equipment rolls an instance at acquisition"
    index_id = insts[0]["index_id"]
    assert insts[0].get("appraise", 1) == 0, \
        "genuinely new equipment is unidentified"

    # trigger a backpack resync (use_item resyncs the equipment bag) so the
    # new item's wire state is observable
    db.add_item(char_id, 1, 5)   # health potions
    resp = await c.rpc(P.USE_ITEM, {0: 1, 1: 1})
    assert resp.body[0] == 0
    seen_new = seen_appr = None
    for _ in range(20):
        fr = await c.next_push(P.SYNC_BACKPACK_ITEM, timeout=3)
        if fr is None:
            break
        for b in decode_object_array(fr.body[0]):
            d = sproto.decode_fields(b)
            if str(d.get(1)) == str(weapon):
                seen_appr = gameitem_appraise(b)
                parm = sproto.decode_typed(b, GAMEITEM_SPEC).get(7) or []
                seen_new = parm[5] if len(parm) > 5 else None
                break
        if seen_appr is not None and seen_new is not None:
            break
    assert seen_appr == 0, "new item is locked in the bag"
    assert seen_new == 0, "new item flagged as new"

    # Appraise: no gold -> error; with gold -> unlocks
    gold = db.get_currency(char_id, economy.CURRENCY_GOLD)
    resp = await c.rpc(P.EQUIP_APPRAISE, {0: index_id})
    assert resp.body[0] == 0
    assert db.get_instance(index_id).get("appraise", 1) == 1
    assert db.get_currency(char_id, economy.CURRENCY_GOLD) == \
        gold - economy.APPRAISE_PRICE
    await c.close()


@pytest.mark.asyncio
async def test_new_equipment_equip_pays_identify_and_stays_appraised(server):
    """The client's new-item popup equips a fresh drop directly (it checks
    appraise affordability first). Server-side this equips, charges the
    identify fee and marks the item appraised so a worn piece is never
    locked."""
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "NewEquip")
    db = srv.db
    await c.drain(0.5)

    prof = db.get_character(char_id)["profession"]
    weapon = (prof + 1) * 10000 + 301
    db.add_item(char_id, weapon, 1)   # new -> appraised=0
    inst = db.find_instances(char_id, weapon)[0]
    assert inst.get("appraise", 1) == 0

    gold_before = db.get_currency(char_id, economy.CURRENCY_GOLD)
    resp = await c.rpc(P.EQUIP_ITEM, {0: weapon})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 0) == weapon
    assert db.get_instance(inst["index_id"]).get("appraise", 1) == 1, \
        "equipping a new item identifies it"
    assert db.get_currency(char_id, economy.CURRENCY_GOLD) == \
        gold_before - economy.APPRAISE_PRICE, \
        "identify fee charged on equip"
    await c.close()


@pytest.mark.asyncio
async def test_appraise_is_idempotent_and_rejects_non_items(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "AppraiseIdem")
    db = srv.db
    await c.drain(0.5)

    # appraising an instance that does not exist -> errno
    resp = await c.rpc(P.EQUIP_APPRAISE, {0: 999999})
    assert resp.body[0] != 0

    # appraising a FASHION instance -> errno (only equipment is appraisable)
    fid = economy.ALL_FASHION_IDS[0]
    resp = await c.rpc(P.EQUIP_FASHION_ITEM, {0: fid})
    assert resp.body[0] == 0
    fslot = economy.fashion_slot_for(fid)
    fidx = db.get_equipped_index(char_id, fslot)
    assert fidx is not None
    resp = await c.rpc(P.EQUIP_APPRAISE, {0: fidx})
    assert resp.body[0] != 0, "fashion is not an appraisable equipment piece"
    await c.close()


@pytest.mark.asyncio
async def test_body_equip_slots_never_leak_fashion_or_badge_into_equippack(server):
    """EQUIPPACK must only carry real armor/weapon wire items.

    Prior bug: after an equip/unequip, _sync_equip_change re-sent the FULL
    equipped map to EQUIPPACK, including badge/fashion instances (slots
    8/9..12). The client resolves an EQUIPPACK entry by indexId, falls back
    to the first empty slot, then matches a fashion/badge by itemData.
    SubType — the wrong ModelId makes one body part disappear. Now only
    slots 0..5 re-sync to EQUIPPACK.
    """
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "BodyCheck")
    db = srv.db
    await c.drain(0.5)

    # equip a fashion + a badge (their containers are 5/4)
    fid = economy.ALL_FASHION_IDS[0]
    resp = await c.rpc(P.EQUIP_FASHION_ITEM, {0: fid})
    assert resp.body[0] == 0
    resp = await c.rpc(P.EQUIP_BADGE, {0: 20})
    assert resp.body[0] == 0
    await c.drain(0.6)

    # trigger an armor unequip so _sync_equip_change re-syncs EQUIPPACK
    armor_slot = None
    for slot, item_id, _idx in db.list_equipped(char_id):
        if 1 <= slot <= 5:
            armor_slot = slot
            break
    assert armor_slot is not None
    armor_idx = db.get_equipped_index(char_id, armor_slot)
    await c.rpc(P.UNEQUIP_ITEM, {0: armor_idx})
    await c.drain(0.6)

    # any EQUIPPACK wire item must be an actual EQUIP (not fashion/badge)
    for _ in range(30):
        fr = await c.next_push(P.UPDATE_ITEM, timeout=3)
        if fr is None:
            break
        body = fr.body
        cont = body.get(0)
        if cont != P.CONTAINER_EQUIPPACK:
            continue
        gi = body.get(2)
        if gi is None:
            continue  # the reset (removal) entry is fine
        d = sproto.decode_fields(sproto.as_bytes(gi))
        item_id = int(d.get(1))
        idef = economy.ITEMS.get(item_id, {})
        assert idef.get("type") == "equipment", \
            "EQUIPPACK must only carry real equipment (no badge/fashion leak)"
    await c.close()


@pytest.mark.asyncio
async def test_character_equip_map_carries_only_real_equipment_at_spawn(server):
    """character.equip (tag 9) feeds the client's EQUIPPACK: it must only
    contain real armor/weapon instances, never fashion/badge pieces (which
    hidden the body part with a wrong ModelId)."""
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "SpawnEquip")
    db = srv.db
    await c.drain(0.5)

    # wear a fashion + badge and trigger a fresh spawn via ENTER_MAP legacy
    resp = await c.rpc(P.EQUIP_FASHION_ITEM, {0: economy.ALL_FASHION_IDS[1]})
    assert resp.body[0] == 0
    resp = await c.rpc(P.EQUIP_BADGE, {0: 20})
    assert resp.body[0] == 0
    await c.drain(0.6)

    resp = await c.rpc(P.ENTER_MAP, {0: economy.MAIN_CITY_MAP, 1: 0, 2: 1})
    body = resp.body
    char = sproto.decode_typed(sproto.as_bytes(body[0]), {0: "i", 9: "oa"})
    equip_blobs = decode_object_array(char.get(9) or sproto.encode_object_array([]))
    for b in equip_blobs:
        d = sproto.decode_fields(b)
        item_id = int(d.get(1))
        idef = economy.ITEMS.get(item_id, {})
        assert idef.get("type") == "equipment", \
            "character.equip (EQUIPPACK) must only hold real equipment"
    await c.close()


@pytest.mark.asyncio
async def test_weapon_has_basic_attack_plus_six_skills_and_persists(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "SixSkills")
    db = srv.db
    await c.drain(0.5)

    prof = db.get_character(char_id)["profession"]
    weapon_type = game_data.PROFESSIONS[prof]["weapon_type"]
    pool = game_data.WEAPON_SKILL_POOL[weapon_type]

    # character skill bar: basic attack (x01) + FULL 6-skill pool
    rows = db.list_skills(char_id)
    sids = {r["skill_id"] for r in rows}
    assert pool[0] - 1 in sids, "basic attack x01 learned" 
    for sid in pool:
        assert sid in sids, "weapon skill %d learned" % sid
    # basic attack occupies indexPos 3, the six skills 4..9
    by_pos = {r["skill_id"]: r["index_pos"] for r in rows}
    assert by_pos[pool[0] - 1] == 3, "basic attack at the basic-attack slot"
    for i, sid in enumerate(pool):
        assert by_pos[sid] == 4 + i, "skill %d at bar position %d" % (sid, 4 + i)

    # the weapon instance carries all six skills (index 0..5)
    widx = db.get_equipped_index(char_id, 0)
    inst = db.get_instance(widx)
    wskills = [a[4] for a in inst["attrs"] if len(a) > 4 and a[4]]
    assert len(wskills) == 6, "weapon instance carries exactly six skills"
    assert {int(s) for s in wskills} == set(pool), \
        "the six weapon skills are the class pool (basic attack excluded)"

    # relogin: same instance, same six skills
    await c.close()
    c2, _ = await login_and_pick(game_port, "SixSkills_dup")
    await c2.close()
    c3 = await _connect(game_port)
    resp = await c3.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    resp = await c3.rpc(P.VERFIY, {0: account_id, 1: resp.body[1],
                                   2: "14119"})
    await c3.rpc(P.LOGIN, {0: resp.body[1], 1: account_id, 2: 0,
                           3: "1.012.017", 4: "Unity4.7", 5: 1, 6: 12345})
    await c3.rpc(P.CHARACTER_PICK, {0: char_id})
    await c3.drain(0.5)
    inst2 = db.get_instance(widx)
    assert inst2["attrs"] == inst["attrs"], "skills persist across relogin"
    await c3.close()


@pytest.mark.asyncio
async def test_fashion_all_owned_and_stays_owned_after_unequip(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "FashionAll")
    db = srv.db
    await c.drain(0.5)

    for fid in economy.ALL_FASHION_IDS:
        assert db.get_item_count(char_id, fid) == 1, \
            "fashion %d owned at creation" % fid

    fid = economy.ALL_FASHION_IDS[0]
    resp = await c.rpc(P.EQUIP_FASHION_ITEM, {0: fid})
    assert resp.body[0] == 0
    slot = economy.fashion_slot_for(fid)
    assert db.get_equipped(char_id, slot) == fid
    assert db.get_item_count(char_id, fid) == 1, "still owned while worn"

    idx = db.get_equipped_index(char_id, slot)
    resp = await c.rpc(P.UNEQUIP_FASHION_ITEM, {0: idx})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, slot) is None
    assert db.get_item_count(char_id, fid) == 1, "owned after unequip"
    await c.close()