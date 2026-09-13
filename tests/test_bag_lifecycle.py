"""End-to-end Bag-lifecycle tests.

Covers the three reported symptom clusters after the Bag system rework:

1. Currency — new account starts with non-zero Cash/Gold/Diamond, the
   values ride `main_player_create` and `aoi_update_attribute`, and they
   survive relogin.
2. Unequip — an unequipped item stays owned, stays "seen" (parm[5]=1 / not
   freshly acquired), and can immediately be equipped again.
3. Wardrobe — fashion lives ONLY in FASHION_BACKPACK (not duplicated in the
   EQUIP_BACKPACK bag), the full intended set is present, and equipped
   fashion survives relogin.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from server import economy
from server import protocol as P
from server import sproto

from tests.test_e2e import _connect, server  # noqa: F401  (pytest fixture)
from tests.test_economy import login_and_pick

PROPERTY_SPEC = {13: "i", 14: "i", 15: "i", 16: "i", 17: "i", 18: "i"}


def decode_object_array(blob):
    """Object-array payload -> list of raw element bytes (list or blob)."""
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


def gameitem_parm5(gameitem_blob) -> int:
    """parm[5] from a wire gameitem (the client's new-item flag)."""
    values = sproto.decode_typed(gameitem_blob, GAMEITEM_SPEC).get(7)
    if values is None:
        return None
    return values[5] if len(values) > 5 else None


GAMEITEM_SPEC = {
    0: "i", 1: "s", 2: "i", 3: "i", 4: "i", 5: "i", 6: "i",
    7: "ia", 8: "i", 9: "oa", 10: "oa",
}


@pytest.mark.asyncio
async def test_currency_present_and_persisted(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Wallet")
    db = srv.db

    cash = db.get_currency(char_id, economy.CURRENCY_CASH)
    gold = db.get_currency(char_id, economy.CURRENCY_GOLD)
    diamond = db.get_currency(char_id, economy.CURRENCY_DIAMOND)
    assert cash > 0, "new account starts with cash"
    assert gold > 0, "new account starts with gold"
    assert diamond > 0, "new account starts with diamond"

    # main_player_create carries the wallet in property money1/2/3
    mpc = await c.next_push(P.MAIN_PLAYER_CREATE, timeout=6)
    char = sproto.decode_fields(sproto.as_bytes(mpc.body[0]))
    prop = sproto.decode_typed(sproto.as_bytes(char.get(5)), PROPERTY_SPEC)
    assert prop[13] == cash, "money1 = cash"
    assert prop[14] == gold, "money2 = gold"
    assert prop[15] == diamond, "money3 = diamond"
    await c.close()

    # relogin keeps the same wallet
    c2 = await _connect(game_port)
    resp = await c2.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    resp = await c2.rpc(P.VERFIY, {0: account_id, 1: resp.body[1],
                                   2: "14119"})
    await c2.rpc(P.LOGIN, {0: resp.body[1], 1: account_id, 2: 0,
                           3: "1.012.017", 4: "Unity4.7", 5: 1, 6: 12345})
    await c2.rpc(P.CHARACTER_PICK, {0: char_id})
    await c2.drain(0.8)
    assert db.get_currency(char_id, economy.CURRENCY_CASH) == cash
    assert db.get_currency(char_id, economy.CURRENCY_GOLD) == gold
    assert db.get_currency(char_id, economy.CURRENCY_DIAMOND) == diamond
    await c2.close()


@pytest.mark.asyncio
async def test_unequip_keeps_owned_seen_and_reequippable(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "TakeOff")
    db = srv.db
    await c.drain(0.5)

    # grant a second weapon (not equipped) so we can test the bag copy
    prof = db.get_character(char_id)["profession"]
    weapon = (prof + 1) * 10000 + 101
    db.add_item(char_id, weapon, 1, seen=1)

    resp = await c.rpc(P.EQUIP_ITEM, {0: weapon})
    assert resp.body[0] == 0
    index_id = db.get_equipped_index(char_id, 0)
    assert index_id is not None
    inst = db.get_instance(index_id)
    assert inst is not None and inst["item_id"] == weapon
    # the fresh sync marks the item seen and equipped
    await c.drain(0.6)

    # unequip via the real client's indexId
    resp = await c.rpc(P.UNEQUIP_ITEM, {0: index_id})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 0) is None
    assert db.get_item_count(char_id, weapon) == 1, "still owned"
    assert db.get_instance(index_id) is not None, "instance kept"

    # the re-added bag item must NOT appear freshly acquired (parm[5]=1)
    seen_after_unequip = None
    for _ in range(20):
        fr = await c.next_push(P.SYNC_BACKPACK_ITEM, timeout=3)
        if fr is None:
            break
        for blob in decode_object_array(fr.body[0]):
            d = sproto.decode_fields(blob)
            if str(d.get(1)) == str(weapon):
                seen_after_unequip = gameitem_parm5(blob)
                break
        if seen_after_unequip is not None:
            break
    assert seen_after_unequip == 1, "unequipped item stays seen (not new)"

    # re-equip immediately without any unlock click
    resp = await c.rpc(P.EQUIP_ITEM, {0: weapon})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 0) == weapon, "immediately re-equippable"
    assert db.get_equipped_index(char_id, 0) == index_id, "same instance"
    await c.close()


@pytest.mark.asyncio
async def test_fashion_wardrobe_separate_and_complete(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Closet")
    db = srv.db
    await c.drain(0.5)

    # every intended fashion id is owned
    for fid in economy.ALL_FASHION_IDS:
        assert db.get_item_count(char_id, fid) == 1, \
            "fashion %d owned" % fid

    # FASHION_BACKPACK (616) carries the full set
    sf = await c.next_push(P.SYNC_FASHION_BACKPACK_ITEM, timeout=6)
    fash = decode_object_array(sf.body[0])
    fids = {sproto.decode_fields(b).get(1) for b in fash}
    assert fids == {str(f) for f in economy.ALL_FASHION_IDS}, \
        "complete wardrobe"

    # EQUIP_BACKPACK (592) carries NO fashion (bag vs wardrobe separation)
    sb = await c.next_push(P.SYNC_BACKPACK_ITEM, timeout=6)
    bag = decode_object_array(sb.body[0])
    for b in bag:
        d = sproto.decode_fields(b)
        assert d.get(1) not in {str(f) for f in economy.ALL_FASHION_IDS}, \
            "fashion leaked into the equipment bag"

    # equip a fashion piece; it stays owned and lands in FASHION_EQUIPPACK
    fid = economy.ALL_FASHION_IDS[0]
    resp = await c.rpc(P.EQUIP_FASHION_ITEM, {0: fid})
    assert resp.body[0] == 0
    slot = economy.fashion_slot_for(fid)
    assert db.get_equipped(char_id, slot) == fid
    assert db.get_item_count(char_id, fid) == 1, "still owned while worn"
    await c.drain(0.5)

    # unequip: still owned, still present in the wardrobe
    idx = db.get_equipped_index(char_id, slot)
    resp = await c.rpc(P.UNEQUIP_FASHION_ITEM, {0: idx})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, slot) is None
    assert db.get_item_count(char_id, fid) == 1, "owned after unequip"
    await c.close()


@pytest.mark.asyncio
async def test_currency_and_state_survive_relogin(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "PersistBag")
    db = srv.db
    await c.drain(0.5)

    # grant + equip a second weapon, unequip it, equip a fashion piece
    prof = db.get_character(char_id)["profession"]
    weapon = (prof + 1) * 10000 + 201
    db.add_item(char_id, weapon, 1, seen=1)
    await c.rpc(P.EQUIP_ITEM, {0: weapon})
    index_id = db.get_equipped_index(char_id, 0)
    await c.rpc(P.UNEQUIP_ITEM, {0: index_id})
    fid = economy.ALL_FASHION_IDS[1]
    await c.rpc(P.EQUIP_FASHION_ITEM, {0: fid})
    await c.drain(0.6)

    cash = db.get_currency(char_id, economy.CURRENCY_CASH)
    gold = db.get_currency(char_id, economy.CURRENCY_GOLD)
    diamond = db.get_currency(char_id, economy.CURRENCY_DIAMOND)
    weapon_owned = db.get_item_count(char_id, weapon)
    fashion_slot = economy.fashion_slot_for(fid)
    fashion_idx = db.get_equipped_index(char_id, fashion_slot)
    fashion_equipped = db.get_equipped(char_id, fashion_slot)
    await c.close()

    # relogin
    c2 = await _connect(game_port)
    resp = await c2.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    resp = await c2.rpc(P.VERFIY, {0: account_id, 1: resp.body[1],
                                   2: "14119"})
    await c2.rpc(P.LOGIN, {0: resp.body[1], 1: account_id, 2: 0,
                           3: "1.012.017", 4: "Unity4.7", 5: 1, 6: 12345})
    await c2.rpc(P.CHARACTER_PICK, {0: char_id})
    await c2.drain(0.8)

    assert db.get_currency(char_id, economy.CURRENCY_CASH) == cash
    assert db.get_currency(char_id, economy.CURRENCY_GOLD) == gold
    assert db.get_currency(char_id, economy.CURRENCY_DIAMOND) == diamond
    assert db.get_item_count(char_id, weapon) == weapon_owned
    assert db.get_equipped(char_id, fashion_slot) == fashion_equipped
    assert db.get_equipped_index(char_id, fashion_slot) == fashion_idx
    assert db.get_equipped_index(char_id, 0) is None, \
        "weapon stayed unequipped after relogin"
    await c2.close()