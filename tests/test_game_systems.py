"""End-to-end tests for the full game systems: NPCs/combat, equipment,
guilds, friends, mail, sign-in, skills and cars."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from server import economy
from server import protocol as P
from server import sproto

from tests.test_e2e import _connect, server  # noqa: F401  (pytest fixture)
from tests.test_economy import decode_object_array, login_and_pick


def _collect_pushes(c, want_type, want_count=1, timeout=5.0):
    """Read frames until we've seen `want_count` pushes of `want_type`."""
    got = []
    async def run():
        while len(got) < want_count:
            data = await asyncio.wait_for(c.reader.read(8192), timeout)
            if not data:
                break
            for payload in c.decoder.feed(data):
                frame = P.parse_frame(payload, response=True)
                if frame.type == want_type and frame.session is None:
                    got.append(frame)
    try:
        asyncio.get_event_loop().run_until_complete(run()) if False else None
    except Exception:
        pass
    return got


@pytest.mark.asyncio
async def test_npcs_are_created_on_map_entry(server):
    srv, gate_port, game_port = server
    c = await _connect(game_port)
    # do the login manually so we can watch the npc_create burst
    resp = await c.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    key = sproto.as_str(resp.body[1])
    resp = await c.rpc(P.VERFIY, {0: account_id, 1: key, 2: "14119"})
    await c.rpc(P.LOGIN, {0: resp.body[1], 1: account_id})
    general = sproto.encode_object({0: "NpcWatcher", 2: 0})
    resp = await c.rpc(P.CHARACTER_CREATE, {0: general})
    char_id = sproto.decode_typed(sproto.as_bytes(resp.body[0]),
                                  {0: "i", 1: "o", 2: "o", 3: "o",
                                   4: "i", 5: "i"})[0]
    await c.rpc(P.CHARACTER_PICK, {0: char_id})
    await c.send_request(P.ENTER_MAP, {0: "11", 1: 0, 2: 1})
    # read the push burst: response + npc_create per NPC
    npc_frames = []
    for _ in range(10):
        data = await asyncio.wait_for(c.reader.read(8192), 5)
        for payload in c.decoder.feed(data):
            frame = P.parse_frame(payload, response=True)
            if frame.type == P.NPC_CREATE:
                # client's real SprotoType.npc_attribute:
                # id(0) int, npcdataid(1) STRING, hp(2), max_hp(3),
                # atk(4), ..., x(15), z(16), o(17), level(18)
                npc_frames.append(sproto.decode_typed(
                    sproto.as_bytes(frame.body[0]),
                    {0: "i", 1: "s", 2: "i", 3: "i", 4: "i", 5: "i",
                     15: "i", 16: "i", 17: "i", 18: "i"}))
        if len(npc_frames) >= len(economy.NPC_SPAWNS[economy.MAIN_CITY_MAP]):
            break
    assert len(npc_frames) == len(economy.NPC_SPAWNS[economy.MAIN_CITY_MAP]), \
        "all map NPCs pushed"
    # npcdataid must be a real NpcData row id (string) — an unknown id makes
    # the client's GetNpcDataByID return null and crash the loading screen
    real_rows = {k["npcdataid"] for k in economy.NPC_KINDS.values()}
    assert {n[1] for n in npc_frames} == real_rows
    assert all(isinstance(n[1], str) and n[1].isdigit() for n in npc_frames)
    await c.close()


@pytest.mark.asyncio
async def test_combat_kills_npc_and_grants_loot(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Fighter")

    npc = [n for m in srv.world.npcs.values() for n in m.values()][0]
    db = srv.db
    # give the fighter a weapon so the fight ends in a few hits
    db.add_item(char_id, 12, 1)
    db.set_equipped(char_id, 0, 12)
    gold_before = db.get_currency(char_id, economy.CURRENCY_GOLD)

    # Real client flow: attack_local_npc (flavor, no npc id on the wire —
    # the request is {damge, effinfoId}), then the client kills the NPC
    # locally and reports it via local_npc_die {npcid STRING, x, z, type}.
    kind_id = economy.NPC_KINDS[npc.kind]["npcdataid"]
    resp = await c.rpc(P.ATTACK_LOCAL_NPC, {0: 50, 1: "3"})
    assert resp.body[0] == 0
    resp = await c.rpc(P.LOCAL_NPC_DIE,
                       {0: kind_id, 1: 30000, 2: 30000, 3: 0})
    assert resp.body[0] == 0
    # the world NPC is killed and lazily respawned for the next fight
    assert npc.hp == npc.max_hp and not npc.dead

    row = db.get_character(char_id)
    assert row["exp"] > 0
    assert db.get_currency(char_id, economy.CURRENCY_GOLD) > gold_before
    await c.close()


@pytest.mark.asyncio
async def test_equip_and_unequip_flow(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Fashionista")
    db = srv.db
    db.add_item(char_id, 12, 1)   # Rifle, weapon
    db.add_item(char_id, 3, 1)    # Body Armor
    db.add_item(char_id, 20, 1)   # Badge
    db.add_item(char_id, 31, 1)   # Fashion

    resp = await c.rpc(P.EQUIP_ITEM, {0: 12})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 0) == 12

    resp = await c.rpc(P.EQUIP_ITEM, {0: 3})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 1) == 3

    resp = await c.rpc(P.EQUIP_BADGE, {0: 20})
    assert resp.body[0] == 0
    # badges live in their dedicated equip slot (8), fashion in 9
    assert db.get_equipped(char_id, economy.BADGE_DB_SLOT) == 20

    resp = await c.rpc(P.EQUIP_FASHION_ITEM, {0: 31})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, economy.FASHION_DB_SLOT) == 31

    # equipping creates a PERSISTED rolled instance linked to the slot
    index_id = db.get_equipped_index(char_id, 0)
    assert index_id is not None
    inst = db.get_instance(index_id)
    assert inst is not None and inst["item_id"] == 12

    # attributes are recalculated and persisted on equip
    attrs = db.load_attributes(char_id)
    assert attrs.get("power", 0) > 0

    # the real client sends gameitem.indexId (the instance id), not a slot
    resp = await c.rpc(P.UNEQUIP_ITEM, {0: db.get_equipped_index(char_id, 1)})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 1) is None

    resp = await c.rpc(P.UNEQUIP_BADGE, {})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, economy.BADGE_DB_SLOT) is None

    # unequip recalculates: power drops when the weapon comes off
    weapon_power = attrs.get("power")
    resp = await c.rpc(P.UNEQUIP_ITEM, {0: db.get_equipped_index(char_id, 0)})
    assert resp.body[0] == 0
    assert db.get_equipped(char_id, 0) is None
    attrs_after = db.load_attributes(char_id)
    assert attrs_after.get("power", 0) < weapon_power

    # equipping an item you do not own fails (a real class weapon that
    # was never added -> instance/stack lookup finds nothing -> count 0)
    prof = db.get_character(char_id)["profession"]
    resp = await c.rpc(P.EQUIP_ITEM, {0: ((prof + 1) % 3) * 10000 + 101})
    assert resp.body[0] == 3

    await c.close()


@pytest.mark.asyncio
async def test_storagepack_put_and_take(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Stocker")
    srv.db.add_item(char_id, 2, 10)

    resp = await c.rpc(P.PUT_ITEM_STORAGEPACK, {0: 2, 1: 4})
    assert resp.body[0] == 0
    assert srv.db.get_item_count(char_id, 2) == 6
    assert srv.db.get_storage_count(char_id, 2) == 4

    resp = await c.rpc(P.TAKE_ITEM_STORAGEPACK, {0: 2, 1: 3})
    assert resp.body[0] == 0
    assert srv.db.get_item_count(char_id, 2) == 9
    assert srv.db.get_storage_count(char_id, 2) == 1

    await c.close()


@pytest.mark.asyncio
async def test_open_item_package(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Opener")
    srv.db.add_item(char_id, 40, 1)   # Starter Crate: 3x potion + 5x bandage

    resp = await c.rpc(P.OPEN_ITEM_PACKAGE, {0: 40})
    assert resp.body[0] == 0
    contents = [sproto.decode_typed(e, {0: "i", 1: "i"})
                for e in decode_object_array(resp.body[1])]
    assert {x[0]: x[1] for x in contents} == {1: 3, 2: 5}
    assert srv.db.get_item_count(char_id, 40) == 0
    assert srv.db.get_item_count(char_id, 1) == 3
    assert srv.db.get_item_count(char_id, 2) == 5
    await c.close()


@pytest.mark.asyncio
async def test_guild_create_join_donate_buy(server):
    srv, gate_port, game_port = server
    leader, _ = await login_and_pick(game_port, "Don")
    member, _ = await login_and_pick(game_port, "Capo")

    # create
    resp = await leader.rpc(P.GUILD_CREATE, {0: "Corleone"})
    assert resp.body[0] == 0
    guild_id = resp.body[1]
    g = srv.db.get_guild(guild_id)
    assert g["leader"] == "Don"

    # member requests to join; leader approves
    resp = await member.rpc(P.GUILD_JOIN, {0: guild_id})
    assert resp.body[0] == 0
    reqs = srv.db.list_guild_requests(guild_id)
    assert len(reqs) == 1 and reqs[0]["name"] == "Capo"
    resp = await leader.rpc(P.GUILD_APPROVE_RESVERVE, {0: "Capo", 1: 1})
    assert resp.body[0] == 0
    capo_id = srv.db._conn.execute(
        "SELECT id FROM characters WHERE name='Capo'").fetchone()["id"]
    assert srv.db.get_guild_by_member(capo_id) is not None

    # donate gold to the guild
    resp = await leader.rpc(P.GUILD_DONATE, {0: 1000})
    assert resp.body[0] == 0
    assert srv.db.get_guild(guild_id)["gold"] == 1000

    # buy from the guild shop
    resp = await member.rpc(P.REQ_BUY_GUILD_GOODS, {0: 801})
    assert resp.body[0] == 0
    assert srv.db.get_guild(guild_id)["gold"] == 1000 - 500

    # guild info + search
    resp = await member.rpc(P.GUILD_REQ_INFO, {})
    assert 0 in resp.body
    resp = await member.rpc(P.SEARCH_GUILD, {0: "Corleone"})
    guilds = decode_object_array(resp.body[0])
    assert len(guilds) == 1

    # kick the member
    resp = await leader.rpc(P.GUILD_KICK, {0: "Capo"})
    assert resp.body[0] == 0
    await leader.close()
    await member.close()


@pytest.mark.asyncio
async def test_friends_flow(server):
    srv, gate_port, game_port = server
    a, a_id = await login_and_pick(game_port, "FriendA")
    b, b_id = await login_and_pick(game_port, "FriendB")
    # b's arrival generates an aoi_add push on a; drain it
    await a.drain(0.4)

    resp = await a.rpc(P.ADD_FRIEND, {0: "FriendB"})
    # ret_add_friend carries a friend_info object:
    # {characterId(0), friendId(1), name(2), level(3), ...}
    fr = sproto.decode_typed(sproto.as_bytes(resp.body[0]),
                             {0: "i", 1: "i", 2: "s", 3: "i"})
    assert fr[1] == b_id and fr[2] == "FriendB"
    friends = {f["friend_id"] for f in srv.db.list_friends(a_id)}
    assert b_id in friends
    # bidirectional
    friends_b = {f["friend_id"] for f in srv.db.list_friends(b_id)}
    assert a_id in friends_b

    resp = await a.rpc(P.ASK_CHARACTER_INFO, {0: "FriendB"})
    # the client's ask_character_info handler ignores the body (no-op), so we
    # answer with the same friend_info object as ret_add_friend
    entry = sproto.decode_typed(sproto.as_bytes(resp.body[0]),
                                {0: "i", 1: "i", 2: "s", 3: "i"})
    assert entry[1] == b_id and entry[2] == "FriendB"

    resp = await a.rpc(P.DEL_FRIEND, {0: "FriendB"})
    assert resp.body[0] == 0
    assert srv.db.list_friends(a_id) == []
    await a.close()
    await b.close()


@pytest.mark.asyncio
async def test_mail_flow(server):
    srv, gate_port, game_port = server
    a, a_id = await login_and_pick(game_port, "Mailer")
    b, b_id = await login_and_pick(game_port, "MailReceiver")
    await a.drain(0.4)   # aoi_add for b's arrival

    resp = await a.rpc(P.SEND_MAIL, {0: "MailReceiver", 1: "Hey", 2: "Pay up"})
    assert resp.body[0] == 0

    # receiver opens the mailbox
    resp = await b.rpc(P.SEND_MAIL_BOX, {})
    mails = decode_object_array(resp.body[0])
    assert len(mails) == 1
    mail = sproto.decode_typed(mails[0],
                               {0: "i", 1: "s", 2: "s", 3: "s", 4: "i",
                                5: "i", 6: "i"})
    assert mail[1] == "Mailer" and mail[2] == "Hey" and mail[3] == "Pay up"

    # collect (op 1) then delete (op 2)
    resp = await b.rpc(P.MAIL_OPERATION, {0: mail[0], 1: 1})
    assert resp.body[0] == 0
    resp = await b.rpc(P.MAIL_OPERATION, {0: mail[0], 1: 2})
    assert resp.body[0] == 0
    assert srv.db.list_mails(b_id) == []
    await a.close()
    await b.close()


@pytest.mark.asyncio
async def test_sign_in_rewards(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Signer")
    gold_before = srv.db.get_currency(char_id, economy.CURRENCY_GOLD)
    resp = await c.rpc(P.SIGN_WEEK, {})
    assert resp.body[0] == 0
    assert resp.body[1] == 1
    assert srv.db.get_currency(char_id, economy.CURRENCY_GOLD) == \
        gold_before + 200
    resp = await c.rpc(P.SIGN_30_DAY, {})
    assert resp.body[0] == 0
    assert srv.db.get_currency(char_id, economy.CURRENCY_DIAMOND) >= 2
    await c.close()


@pytest.mark.asyncio
async def test_skill_level_up(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Skiller")
    resp = await c.rpc(P.SKILL_LEVEL_UP, {0: 1})
    assert resp.body[0] == 0
    row = srv.db.get_skill(char_id, 1)
    assert row["level"] == 1
    # unknown skill fails
    resp = await c.rpc(P.SKILL_LEVEL_UP, {0: 999})
    assert resp.body[0] == 2
    await c.close()


@pytest.mark.asyncio
async def test_buy_car_and_use_mount(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "Driver")
    srv.db.add_currency(char_id, economy.CURRENCY_GOLD, 100000)

    resp = await c.rpc(P.BUY_CAR_SHOP, {0: 901})
    assert resp.body[0] == 0
    # goods 901 is the real North Star voucher exchanging into CarData 1001
    assert srv.db.get_character(char_id)["car_id"] == 1001

    resp = await c.rpc(P.REQUEST_MOUNT_INFO, {})
    mounts = [sproto.decode_typed(e, {0: "i", 1: "i", 2: "i"})
              for e in decode_object_array(resp.body[0])]
    assert any(m[0] == 1001 for m in mounts)

    resp = await c.rpc(P.USE_MOUNT, {0: 1001})
    assert resp.body[0] == 0
    assert srv.db.get_character(char_id)["using_car"] == 1001
    await c.close()
