"""Regression tests for the real client world-entry flow.

The actual v1.19 client never sends an enter_map request: after character_pick
the SERVER pushes enter_map(503) AND main_player_create(504) back-to-back.
enter_map makes the client stop processing frames and load the map scene;
the buffered main_player_create is processed when SceneController.Awake
re-enables the packet pump, which spawns the main player and sets
GameManager.IsSceneReady = true. Only then does LoadingUIRoot let the
loading bar pass 90% (it is hard-capped at 0.9 while !IsSceneReady), fire
OnLoadingOver and send map_ready(100). The server answers map_ready with
the aoi/npc bursts.

A server that waits for map_ready before pushing main_player_create
deadlocks: the client will not send map_ready until its main player
exists, so the loading window sits at exactly 90% with only the BGM
playing. The wire-blob field-tag assertions below caught the earlier
loading-hang bug (character.movement encoded at tag 5 instead of 7).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from server import protocol as P
from server import sproto
from server.world import encode_character_blob, encode_character_aoi_blob, \
    encode_character_overview

from tests.test_e2e import _connect, server  # noqa: F401  (pytest fixture)
from tests.test_economy import decode_object_array

GENERAL_SPEC = {0: "s", 1: "i", 2: "i", 3: "s"}
CHARACTER_SPEC = {0: "i", 1: "o", 2: "o", 5: "o", 6: "o", 7: "o",
                  13: "o"}
CHARACTER_AOI_SPEC = {0: "i", 1: "o", 2: "o", 3: "o", 5: "o", 6: "o"}
ATTRIBUTE_OTHER_SPEC = {0: "i", 1: "i", 2: "i", 15: "i", 16: "i",
                        17: "i"}
PROPERTY_SPEC = {13: "i", 14: "i"}
VISUAL_SPEC = {0: "s", 1: "s", 2: "s", 3: "s", 4: "s", 5: "s", 10: "i"}
RUNTIME_SPEC = {6: "o", 7: "o"}
OVERVIEW_SPEC = {0: "i", 1: "o", 2: "o", 3: "o", 4: "i", 5: "i"}
MOVEMENT_SPEC = {0: "o", 1: "o"}
POSITION_SPEC = {0: "i", 1: "i", 2: "i", 3: "i"}


async def _login_and_create(game_port, name, profession=0):
    """visitor -> verfiy -> login -> character_create -> character_pick.

    Returns (client, char_id). Does NOT send the legacy enter_map request —
    the real client never does.
    """
    c = await _connect(game_port)
    resp = await c.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    key = sproto.as_str(resp.body[1])
    resp = await c.rpc(P.VERFIY, {0: account_id, 1: key, 2: "14119"})
    session_id = resp.body[1]
    await c.rpc(P.LOGIN, {0: session_id, 1: account_id, 2: 0,
                          3: "1.012.017", 4: "Unity4.7", 5: 1, 6: 12345})
    general = sproto.encode_object({0: name, 2: profession})
    resp = await c.rpc(P.CHARACTER_CREATE, {0: general})
    # character_create.response {character(0): character_overview, errno(1)}
    overview = sproto.decode_typed(sproto.as_bytes(resp.body[0]),
                                   OVERVIEW_SPEC)
    char_id = overview[0]
    await c.rpc(P.CHARACTER_PICK, {0: char_id})
    return c, char_id


def test_character_blob_movement_at_wire_tag_7():
    """SprotoType.character: movement is wire tag 7, tag 5 is property.

    Encoding movement at tag 5 makes the client parse it as `property`,
    leaving character.movement null — the main player never spawns and the
    loading screen hangs forever.
    """
    pos = P.encode_position(11, 0, 22, 90)
    movement = P.encode_movement({"x": 11, "y": 0, "z": 22, "o": 90})
    blob = encode_character_blob(42, "TagSeven", 3, movement,
                                 profession=1)

    d = sproto.decode_typed(blob, CHARACTER_SPEC)
    assert d[0] == 42
    general = sproto.decode_typed(sproto.as_bytes(d[1]), GENERAL_SPEC)
    assert general == {0: "TagSeven", 1: 1, 2: 0, 3: "11"}
    # attribute_other / property / visual / runtime must be present too —
    # the client hard-dereferences all of them in ObjInitPlayerData.
    attr = sproto.decode_typed(sproto.as_bytes(d[2]), ATTRIBUTE_OTHER_SPEC)
    assert attr[2] == 3                      # level
    prop = sproto.decode_typed(sproto.as_bytes(d[5]), PROPERTY_SPEC)
    assert 13 in prop and 14 in prop         # money1 / money2
    vis = sproto.decode_typed(sproto.as_bytes(d[6]), VISUAL_SPEC)
    assert vis[1] == "104"                   # QJ_A CharacterModelData row
    assert vis[0] == "TagSeven"
    # movement must NOT be at tags 3/5/6 — only 7
    move = sproto.decode_typed(sproto.as_bytes(d[7]), MOVEMENT_SPEC)
    assert sproto.decode_typed(sproto.as_bytes(move[0]), POSITION_SPEC) == \
        {0: 11, 1: 0, 2: 22, 3: 90}
    rt = sproto.decode_typed(sproto.as_bytes(d[13]), RUNTIME_SPEC)
    assert 6 in rt and 7 in rt               # attribute / attribute_all
    assert pos in blob  # sanity: position bytes present


def test_visual_uses_real_profession_models():
    """visual.ModeId must use the REAL per-profession model rows.

    A previous "fix" remapped Batfighter visuals to QJ_A believing the APK
    lacked XD_A bundles — but the APK ships the full set (Bundle/Animation/
    baiRen_XD.bundle exists and character select animates the Batfighter),
    and the remap broke the Batfighter's idle animation. The wire blobs must
    carry the real CharacterModelData row for each profession.
    """
    movement = P.encode_movement({"x": 1, "y": 0, "z": 2, "o": 0})
    expected = {0: "100", 1: "104", 2: "105"}   # XD_A / QJ_A / NQS_A
    for profession, mode_id in expected.items():
        blob = encode_character_blob(9, "Model", 1, movement,
                                     profession=profession)
        d = sproto.decode_typed(blob, CHARACTER_SPEC)
        vis = sproto.decode_typed(sproto.as_bytes(d[6]), VISUAL_SPEC)
        assert vis[1] == mode_id
        # aoi blobs and overviews use the same model
        aoi = encode_character_aoi_blob(9, "Model", 1, movement,
                                        profession=profession)
        d2 = sproto.decode_typed(aoi, CHARACTER_AOI_SPEC)
        vis2 = sproto.decode_typed(sproto.as_bytes(d2[1]), VISUAL_SPEC)
        assert vis2[1] == mode_id
        ov = encode_character_overview(
            {"id": 9, "name": "Model", "level": 1, "sex": 0,
             "profession": profession, "created_at": 0})
        d3 = sproto.decode_typed(ov, OVERVIEW_SPEC)
        vis3 = sproto.decode_typed(sproto.as_bytes(d3[3]), VISUAL_SPEC)
        assert vis3[1] == mode_id


@pytest.mark.asyncio
async def test_login_info_burst_is_answered(server):
    """The client fires request_activity_info(225) + friends right after
    login; every one must get its dedicated ret_* response (possibly empty).

    Previously the server dropped them ("unhandled protocol tag"), leaving
    those UI panels waiting on a response forever.
    """
    srv, gate_port, game_port = server
    c = await _connect(game_port)
    resp = await c.rpc(P.VISITOR, {})
    account_id = sproto.as_str(resp.body[0])
    key = sproto.as_str(resp.body[1])
    resp = await c.rpc(P.VERFIY, {0: account_id, 1: key, 2: "14119"})
    session_id = resp.body[1]
    await c.rpc(P.LOGIN, {0: session_id, 1: account_id, 2: 0,
                          3: "1.012.017", 4: "Unity4.7", 5: 1, 6: 12345})

    burst = {
        225: 619,   # request_activity_info -> ret_request_activity_info
        227: 623,   # dance
        195: 599,   # guild boss
        252: 640,   # sign 30-day info
        253: 641,   # sign week info
        257: 645,   # invest pack
        258: 646,   # daily buy
        261: 649,   # daily active
        278: 658,   # retrieve info
        296: 674,   # level reward
        299: 678,   # vip info
        310: 684,   # domin info
        313: 686,   # dance state info -> sync_dance_state_info
        319: 689,   # guild map info
    }
    for req_tag, ret_tag in burst.items():
        resp = await c.rpc(req_tag, {})
        assert resp is not None, f"tag {req_tag} must be answered"
        assert resp.session is not None, \
            f"tag {req_tag} must get an RPC response (session echo)"
        # the ret_* tag must have a registered response schema
        assert P.RESPONSE_ALIASES.get(req_tag) == ret_tag
    await c.close()


def test_character_aoi_blob_uses_aoi_tags():
    """aoi_add carries character_aoi (movement=5, visual=1), NOT character."""
    movement = P.encode_movement({"x": 1, "y": 0, "z": 2, "o": 0})
    blob = encode_character_aoi_blob(7, "AoiGuy", 2, movement,
                                     profession=2)
    d = sproto.decode_typed(blob, CHARACTER_AOI_SPEC)
    assert d[0] == 7
    vis = sproto.decode_typed(sproto.as_bytes(d[1]), VISUAL_SPEC)
    assert vis[1] == "105"                   # NQS_A model
    general = sproto.decode_typed(sproto.as_bytes(d[2]), GENERAL_SPEC)
    assert general[1] == 2                   # profession
    move = sproto.decode_typed(sproto.as_bytes(d[5]), MOVEMENT_SPEC)
    assert 0 in move
    rt = sproto.decode_typed(sproto.as_bytes(d[6]), RUNTIME_SPEC)
    assert 7 in rt                           # attribute_all (mov speed)


def test_character_overview_blob():
    """character_list / character_create carry character_overview objects
    whose general/attribute_other/visual/createtime are all dereferenced."""
    row = {"id": 5, "name": "Over", "level": 4, "sex": 0,
           "profession": 1, "created_at": 1700000000}
    blob = encode_character_overview(row)
    d = sproto.decode_typed(blob, OVERVIEW_SPEC)
    assert d[0] == 5
    general = sproto.decode_typed(sproto.as_bytes(d[1]), GENERAL_SPEC)
    assert general[1] == 1                   # profession
    attr = sproto.decode_typed(sproto.as_bytes(d[2]), {0: "i", 1: "i"})
    assert attr[0] == 4                      # attribute_overview.level
    vis = sproto.decode_typed(sproto.as_bytes(d[3]), VISUAL_SPEC)
    assert vis[1] == "104"
    assert d[4] == 1700000000                # createtime


@pytest.mark.asyncio
async def test_real_client_world_entry_flow(server):
    """pick -> (push) enter_map + main_player_create -> map_ready -> (push) aoi/npc.

    Regression: main_player_create MUST arrive WITHOUT the client sending
    map_ready first. The real client sends map_ready only after its main
    player spawned (IsSceneReady), so waiting for map_ready first freezes
    the loading window at 90% forever.
    """
    srv, gate_port, game_port = server
    c, char_id = await _login_and_create(game_port, "FlowRider")

    # 1) the server must PUSH enter_map {mapInfoId(0), line_index(1),
    # line_count(2)} — parsed by the test client with the push spec
    enter = await c.next_push(P.ENTER_MAP)
    assert enter is not None, "server must push enter_map after pick"
    assert sproto.as_str(enter.body[0]) == "11"

    # 2) main_player_create must follow immediately — the client buffers it
    # during the scene load and spawns the player from it. It must NOT be
    # gated on map_ready (that ordering deadlocks the real client at 90%).
    mpc = await c.next_push(P.MAIN_PLAYER_CREATE)
    assert mpc is not None, \
        "main_player_create must arrive before map_ready is sent"
    top = sproto.decode_typed(sproto.as_bytes(mpc.body[0]),
                              {0: "o", 1: "o"})
    char = sproto.decode_typed(sproto.as_bytes(top[0]), CHARACTER_SPEC)
    assert char[0] == char_id
    move = sproto.decode_typed(sproto.as_bytes(char[7]), MOVEMENT_SPEC)
    assert move is not None and 0 in move
    pos = sproto.decode_typed(sproto.as_bytes(move[0]), POSITION_SPEC)
    assert set(pos.keys()) == {0, 1, 2, 3}
    # everything ObjInitPlayerData hard-dereferences must be present
    assert 2 in char and 5 in char and 6 in char and 13 in char

    # the standalone movement field (tag 1) is a valid movement blob too
    move2 = sproto.decode_typed(sproto.as_bytes(top[1]), MOVEMENT_SPEC)
    assert 0 in move2

    # 3) the client (now past the loading window) answers map_ready and the
    # server delivers the world contents: aoi/npc bursts, and no duplicate
    # main_player_create (the client ignores a second one anyway).
    await c.send_request(P.MAP_READY, {})
    npc = await c.next_push(P.NPC_CREATE, timeout=3.0)
    assert npc is not None, "map npcs must be pushed after map_ready"
    assert sproto.decode_typed(sproto.as_bytes(npc.body[0]),
                               {1: "s"})[1], "npc blob must carry npcdataid"
    dup = await c.next_push(P.MAIN_PLAYER_CREATE, timeout=0.5)
    assert dup is None, "main_player_create must not be re-sent after map_ready"

    await c.close()


@pytest.mark.asyncio
async def test_map_ready_without_pick_is_ignored(server):
    srv, gate_port, game_port = server
    c = await _connect(game_port)
    await c.rpc(P.VISITOR, {})
    # map_ready with no pending world entry must not crash or join a map
    await c.send_request(P.MAP_READY, {})
    await asyncio.sleep(0.1)
    assert srv.world.maps == {}
    await c.close()


@pytest.mark.asyncio
async def test_aoi_add_uses_character_aoi_blob(server):
    """aoi_add bodies carry SprotoType.character_aoi (movement at tag 5)."""
    srv, gate_port, game_port = server
    a, _ = await _login_and_create(game_port, "AoiA")
    b, b_id = await _login_and_create(game_port, "AoiB")

    for c in (a, b):
        await c.next_push(P.ENTER_MAP)
        await c.send_request(P.MAP_READY, {})
        await c.next_push(P.MAIN_PLAYER_CREATE)

    # AoiA must receive AoiB through aoi_add with movement at tag 7
    aoi = await a.next_push(P.AOI_ADD, timeout=3.0)
    assert aoi is not None, "aoi_add for the second player"
    char = sproto.decode_typed(sproto.as_bytes(aoi.body[0]), {0: "o"})[0]
    char = sproto.decode_typed(sproto.as_bytes(char), CHARACTER_AOI_SPEC)
    assert char[0] == b_id
    # character_aoi: movement=5, visual=1, general=2, attribute_other=3
    assert 7 not in char, "aoi_add must use character_aoi, not character"
    assert 5 in char and 1 in char and 2 in char

    await a.close()
    await b.close()


@pytest.mark.asyncio
async def test_sync_skill_info_parses_with_client_schema(server):
    """sync_skill_info: map<string, skill_info> — skillId must be a STRING.

    The real client crashed with "Exception: invalid pos" in
    SprotoType.skill_info.decode() when the server sent skillId as an
    integer (read_string on an int-encoded field runs off the buffer),
    killing the packet loop and freezing the loading window at 90%.
    """
    srv, gate_port, game_port = server
    c, char_id = await _login_and_create(game_port, "SkillStr")

    skill = await c.next_push(P.SYNC_SKILL_INFO)
    assert skill is not None, "sync_skill_info pushed after pick"
    # client: deserialize.read_map((skill_info v) => v.skillId) == object array
    entries = decode_object_array(skill.body[0])
    assert entries, "at least one skill synced"
    for entry in entries:
        d = sproto.decode_typed(sproto.as_bytes(entry),
                                {0: "s", 1: "i"})
        assert isinstance(d[0], str) and d[0], "skillId must be a string"
        assert d[0].isdigit()
    await c.close()


@pytest.mark.asyncio
async def test_syn_friend_info_single_object(server):
    """syn_friend_info carries ONE friend_info object at tag 0 (fields:
    characterId(0), friendId(1), name(2), level(3), profession(4))."""
    srv, gate_port, game_port = server
    a, a_id = await _login_and_create(game_port, "FriendSyncA")
    b, b_id = await _login_and_create(game_port, "FriendSyncB")
    for c in (a, b):
        await c.next_push(P.ENTER_MAP)
        await c.send_request(P.MAP_READY, {})
        await c.next_push(P.MAIN_PLAYER_CREATE)
    await a.drain(0.3)

    resp = await a.rpc(P.ADD_FRIEND, {0: "FriendSyncB"})
    # ret_add_friend must carry a friend_info OBJECT
    fr = sproto.decode_typed(sproto.as_bytes(resp.body[0]),
                             {0: "i", 1: "i", 2: "s", 3: "i"})
    assert fr[0] == b_id and fr[1] == b_id and fr[2] == "FriendSyncB"

    # any syn_friend_info push must parse as a single friend_info
    push = await a.next_push(P.SYN_FRIEND_INFO, timeout=1.5)
    if push is not None:
        d = sproto.decode_typed(sproto.as_bytes(push.body[0]),
                                {0: "i", 1: "i", 2: "s", 3: "i"})
        assert d[2] == "FriendSyncB"
    await a.close()
    await b.close()
