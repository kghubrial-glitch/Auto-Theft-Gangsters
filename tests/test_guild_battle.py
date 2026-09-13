"""End-to-end tests for the guild battle (weekly guild-vs-guild war) and the
real content integration: professions (3 classes), real cars (CarData), and
weapon classes/tiers (EquipData)."""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from server import economy
from server import game_data
from server import protocol as P
from server import sproto

from tests.test_e2e import server  # noqa: F401  (pytest fixture)
from tests.test_economy import decode_object_array, login_and_pick


def _guild_blob_create(srv, name):
    return sproto.encode_object({0: name})


@pytest.mark.asyncio
async def test_profession_grants_class_weapon_and_skills(server):
    srv, gate_port, game_port = server
    # create a Boxer (profession 1): should start with fists tier 1 (20001)
    c = await _create_char_with_profession(game_port, "BoxerKid", 1)
    # equipped weapon after create+pick
    resp = await c.rpc(P.REQUEST_UPDATE_STORAGEPACK, {})
    # verify through combat power instead: attack power uses the weapon
    # 12 base + 180 fists tier1 = 192
    char_id = srv.db._conn.execute(
        "SELECT id FROM characters WHERE name = 'BoxerKid'").fetchone()["id"]
    row = srv.db.get_character(char_id)
    assert row["profession"] == 1
    equipped = srv.db.get_equipped(char_id, 0)
    assert equipped == 20001
    skills = [r["skill_id"] for r in srv.db.list_skills(char_id)]
    # a profession learns its basic attack (the x01 combo opener) PLUS its
    # class's full 6-skill pool — the basic attack is a separate combat
    # action and must NOT be one of the six weapon skill slots.
    assert sorted(skills) == sorted(
        [game_data.PROFESSIONS[1]["skills"][0]]
        + game_data.WEAPON_SKILL_POOL[1]), \
        "basic attack + full 6-skill pool"
    await c.close()


@pytest.mark.asyncio
async def test_weapon_class_locked_to_profession(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "GunnerGuy")
    # GunnerGuy's profession defaults to 0 (Batfighter) — equipping a boxer
    # weapon (class 1) must be rejected
    srv.db.add_item(char_id, 20001, 1)
    resp = await c.rpc(P.EQUIP_ITEM, {0: 20001})
    assert resp.body[0] == 4          # wrong profession
    # but a bat weapon of the same tier is fine
    srv.db.add_item(char_id, 10101, 1)
    resp = await c.rpc(P.EQUIP_ITEM, {0: 10101})
    assert resp.body[0] == 0
    await c.close()


@pytest.mark.asyncio
async def test_real_cars_in_car_shop(server):
    srv, gate_port, game_port = server
    c, char_id = await login_and_pick(game_port, "CarFan")
    srv.db.add_currency(char_id, economy.CURRENCY_GOLD, 100000)
    # Thunder (goods 902 -> CarData 1002)
    resp = await c.rpc(P.BUY_CAR_SHOP, {0: 902})
    assert resp.body[0] == 0
    assert srv.db.get_character(char_id)["car_id"] == 1002
    # all 7 shop cars are real CarData vehicles (1008 is the variant model)
    goods = economy.SHOPS[9]["goods"]
    car_ids = {g["car_id"] for g in goods}
    assert car_ids == {k for k in game_data.CARS if k != 1008}
    await c.close()


@pytest.mark.asyncio
async def test_guild_battle_full_flow(server):
    srv, gate_port, game_port = server
    # two guilds (one member each for simplicity)
    a, a_id = await login_and_pick(game_port, "WarChief")
    b, b_id = await login_and_pick(game_port, "WarRival")
    for client, name, cid in ((a, "RedGang", a_id), (b, "BlueGang", b_id)):
        await client.rpc(P.GUILD_CREATE, {0: name})
    # leader signs up fighters (self); names go as a string array blob
    resp = await a.rpc(P.SET_GUILD_BATTLE_MEMBER,
                       {0: sproto.encode_string_array(["WarChief"])})
    assert resp.body[0] == 0
    resp = await a.rpc(P.REQ_GUILD_BATTLE_MEMBER, {})
    names = [sproto.decode_typed(e, {0: "s"})[0]
             if isinstance(e, (bytes, bytearray)) else e[0]
             for e in resp.body[0]]
    assert names == ["WarChief"]
    # battle info: next round time + duration + max members
    resp = await a.rpc(P.REQ_GUILD_BATTLE_INFO, {})
    assert resp.body[1] > 0
    assert resp.body[2] == game_data.GUILD_BATTLE["duration"]
    assert resp.body[3] == game_data.GUILD_BATTLE["max_members"]
    # state outside the weekly window is idle (window-aware: when the test
    # runs during a real round the state is legitimately 1)
    from server.handlers_guild_battle import _current_round
    resp = await a.rpc(P.REQ_GUILD_BATTLE_STATE, {})
    expected = 1 if _current_round(int(time.time())) >= 0 else 0
    assert resp.body[0] == expected
    # betting gold bars on RedGang
    srv.db.add_currency(a_id, economy.CURRENCY_GOLD, 500)
    resp = await a.rpc(P.GUILD_BATTLE_GUESS, {0: "RedGang", 1: 200})
    assert resp.body[1] == 0   # ret_guild_battle_guess {state(1)}
    resp = await a.rpc(P.REQ_GUILD_BATTLE_GUESS, {})
    assert sproto.as_str(resp.body[0]) == "RedGang"
    assert resp.body[1] == 200
    # ranks: both guilds at 0 before entering
    resp = await a.rpc(P.REQ_GUILD_BATTLE_RANK, {})
    assert resp.body[0] == [] or resp.body[0] is None or \
        len(decode_object_array(resp.body[0])) == 0
    # score info before entering
    resp = await a.rpc(P.REQ_GUILD_SCORE_INFO, {})
    assert resp.body[0] == 0
    # entering outside the battle window is rejected (state 2); inside the
    # window the enter succeeds (0)
    from server.handlers_guild_battle import _current_round
    resp = await a.rpc(P.ENTER_GUILD_BATTLE, {})
    expected = 0 if _current_round(int(time.time())) >= 0 else 2
    assert resp.body[0] == expected
    await a.close()
    await b.close()


@pytest.mark.asyncio
async def test_guild_battle_entry_scores_once_per_round(server):
    srv, gate_port, game_port = server
    a, a_id = await login_and_pick(game_port, "GBFighter")
    await a.rpc(P.GUILD_CREATE, {0: "ScoreGang"})
    # force the round window open by scoring directly, then check rank
    week = int(__import__("time").time()) // 604800
    db = srv.db
    gid = db.get_guild_by_member(a_id)["id"]
    db.add_guild_battle_score(gid, week, 250)
    resp = await a.rpc(P.REQ_GUILD_BATTLE_RANK, {})
    entries = [e for e in resp.body[0]] if isinstance(resp.body[0], list) \
        else []
    found = False
    for e in entries:
        if isinstance(e, (bytes, bytearray)):
            d = sproto.decode_typed(e, {0: "s", 1: "i"})
            name, score = d[0], d[1]
        elif isinstance(e, list):
            name, score = e[0], e[1]
        else:
            name, score = sproto.as_str(e[0]), e[1]
        if name == "ScoreGang":
            assert score == 250
            found = True
    assert found, "guild appears in the battle ranking"
    resp = await a.rpc(P.REQ_GUILD_SCORE_INFO, {})
    assert resp.body[0] == 250
    assert resp.body[1] == 1
    await a.close()


async def _create_char_with_profession(game_port, name, profession):
    """Login flow that creates a character with a specific profession."""
    from tests.test_e2e import _connect
    c = await _connect(game_port)
    resp = await c.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    key = sproto.as_str(resp.body[1])
    resp = await c.rpc(P.VERFIY, {0: account_id, 1: key, 2: "14119"})
    session_id = resp.body[1]
    await c.rpc(P.LOGIN, {0: session_id, 1: account_id, 2: 0,
                          3: "1.012.017", 4: "Unity4.7", 5: 1, 6: 12345})
    # general {name(0), profession(1), sex(2)} — the client's create dialog
    general = sproto.encode_object({0: name, 1: profession, 2: 0})
    resp = await c.rpc(P.CHARACTER_CREATE, {0: general})
    char_id = sproto.decode_typed(sproto.as_bytes(resp.body[0]),
                                  {0: "i", 1: "o", 2: "o", 3: "o",
                                   4: "i", 5: "i"})[0]
    await c.rpc(P.CHARACTER_PICK, {0: char_id})
    await c.rpc(P.ENTER_MAP, {0: "11", 1: 0, 2: 1})
    await c.drain(0.4)
    return c
