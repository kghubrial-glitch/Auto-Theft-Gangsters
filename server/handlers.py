"""Protocol handlers — the revival server's game logic.

Implements the login flow from docs/protocol.md §8:
    update_game_server -> visitor / verfiy -> login -> character_list ->
    character_create -> character_pick -> map_ready -> enter_map ->
    move / chat / heart_beat / leave_game
"""

import logging
import time

from . import config
from . import economy
from . import protocol as P
from . import sproto
from . import world as W
from .session import Session
from .handlers_pvp import PvpHandlersMixin
from .handlers_wild import WildHandlersMixin
from .handlers_guild_battle import GuildBattleHandlersMixin

log = logging.getLogger("atg.handlers")

# verfiy response states (observed in client LoginRootLogic)
VERIFY_OK = 0
VERIFY_NEW_ACCOUNT = 2


class Handlers(PvpHandlersMixin, WildHandlersMixin,
               GuildBattleHandlersMixin):
    """Registry of tag -> async handler(session, msg)."""

    def __init__(self, server) -> None:
        self.server = server
        self.map = {
            P.UPDATE_GAME_SERVER: self.h_update_game_server,
            P.VISITOR: self.h_visitor,
            P.VERFIY: self.h_verfiy,
            P.LOGIN: self.h_login,
            P.CHARACTER_LIST: self.h_character_list,
            P.CHARACTER_CREATE: self.h_character_create,
            P.CHARACTER_PICK: self.h_character_pick,
            P.MAP_READY: self.h_map_ready,
            P.ENTER_MAP: self.h_enter_map,
            P.MOVE: self.h_move,
            P.CHAT: self.h_chat,
            P.HEART_BEAT: self.h_heart_beat,
            P.LEAVE_GAME: self.h_leave_game,
            P.REFRESH_ONLINE_STATE: self.h_refresh_online_state,
            P.UPDATE_CLIENT_STATE: self.h_update_client_state,
            P.GAME_CHECK: self.h_game_check,
            P.RETRIEVE_ACCOUNT: self.h_retrieve_account,
            # missions + items
            P.ACCEPT_MISSION: self.h_accept_mission,
            P.COMPLETE_MISSION: self.h_complete_mission,
            P.ABANDON_MISSION: self.h_abandon_mission,
            P.USE_ITEM: self.h_use_item,
            P.SELL_ITEM: self.h_sell_item,
            # shop
            P.ASK_SHOP_LIST: self.h_ask_shop_list,
            P.BUY_SHOP_ITEM: self.h_buy_shop_item,
            # inventory / equipment
            P.EQUIP_ITEM: self.h_equip_item,
            P.UNEQUIP_ITEM: self.h_unequip_item,
            P.EQUIP_BADGE: self.h_equip_badge,
            P.UNEQUIP_BADGE: self.h_unequip_badge,
            P.EQUIP_FASHION_ITEM: self.h_equip_fashion,
            P.UNEQUIP_FASHION_ITEM: self.h_unequip_fashion,
            P.OPEN_ITEM_PACKAGE: self.h_open_item_package,
            P.REQUEST_UPDATE_STORAGEPACK: self.h_request_update_storagepack,
            P.PUT_ITEM_STORAGEPACK: self.h_put_item_storagepack,
            P.TAKE_ITEM_STORAGEPACK: self.h_take_item_storagepack,
            P.REQUEST_RANDOM_NAME: self.h_request_random_name,
            P.CHANGE_ITEM_STATE: self.h_change_item_state,
            # combat / npcs
            P.SKILL_USE: self.h_skill_use,
            P.ATTACK_LOCAL_NPC: self.h_attack_local_npc,
            P.LOCAL_NPC_DIE: self.h_local_npc_die,
            P.ACCEPT_DAMGE: self.h_accept_damage,
            P.RELIFE_PLAYER: self.h_relife_player,
            P.SKILL_LEVEL_UP: self.h_skill_level_up,
            # guilds
            P.GUILD_CREATE: self.h_guild_create,
            P.GUILD_JOIN: self.h_guild_join,
            P.GUILD_LEAVE: self.h_guild_leave,
            P.GUILD_KICK: self.h_guild_kick,
            P.GUILD_JOB_CHANGE: self.h_guild_job_change,
            P.GUILD_REQ_LIST: self.h_guild_req_list,
            P.GUILD_REQ_INFO: self.h_guild_req_info,
            P.GUILD_APPROVE_RESVERVE: self.h_guild_approve,
            P.REQ_GUILD_NOTICE: self.h_req_guild_notice,
            P.REQ_OPEN_GUILD_SHOP: self.h_req_open_guild_shop,
            P.REQ_BUY_GUILD_GOODS: self.h_req_buy_guild_goods,
            P.GUILD_LOG: self.h_guild_log,
            P.GUILD_DONATE: self.h_guild_donate,
            P.SEARCH_GUILD: self.h_search_guild,
            # friends
            P.ADD_FRIEND: self.h_add_friend,
            P.DEL_FRIEND: self.h_del_friend,
            P.ASK_CHARACTER_INFO: self.h_ask_character_info,
            P.SYN_FRIEND_INFO: self.h_sync_friend_info,
            # mail
            P.SEND_MAIL: self.h_send_mail,
            P.MAIL_OPERATION: self.h_mail_operation,
            P.SEND_MAIL_BOX: self.h_send_mail_box,
            # daily / sign-in
            P.REQUEST_DAILY_MISSION: self.h_request_daily_mission,
            P.SIGN_WEEK: self.h_sign_week,
            P.SIGN_30_DAY: self.h_sign_30_day,
            # mounts / cars
            P.REQUEST_MOUNT_INFO: self.h_request_mount_info,
            P.MOUNT_EQUIP: self.h_mount_equip,
            P.MOUNT_UNEQUIP: self.h_mount_unequip,
            P.USE_MOUNT: self.h_use_mount,
            P.UNUSE_MOUNT: self.h_unuse_mount,
            P.BUY_CAR_SHOP: self.h_buy_car_shop,
            # copy scenes / dungeons
            P.ENTER_COPY_SCENE: self.h_enter_copy_scene,
            P.LEAVE_COPY_SCENE: self.h_leave_copy_scene,
            P.SINGLE_COPY_SCENE_NPC_DIE: self.h_single_copy_scene_npc_die,
            P.ASK_COPYSCENES_INFO: self.h_ask_copyscenes_info,
            P.ENTER_NEW_MAP: self.h_enter_new_map,
            P.CHANGE_SCENE_LINE: self.h_change_scene_line,
            P.REQUEST_LINE_STATE: self.h_request_line_state,
            P.ENTER_TELEPORT_POINT: self.h_enter_teleport_point,
            P.UPDATE_PLAYER_MAP_INFO: self.h_update_player_map_info,
            # rank pvp ladder
            P.REQUEST_RANDOM_RANK_PVP_OPPONENT:
                self.h_request_random_rank_pvp_opponent,
            P.RANK_PVP_PLAYER_ATTACK: self.h_rank_pvp_player_attack,
            P.RANK_PVP_OTHER_PLAYER_DIE: self.h_rank_pvp_other_player_die,
            P.REQUEST_TOP_RANK_PVP_LIST: self.h_request_top_rank_pvp_list,
            P.REQUEST_RANK_PVP_DATA: self.h_request_rank_pvp_data,
            P.REQUEST_RANK_PVP_HISTORY: self.h_request_rank_pvp_history,
            P.TIANTI_REQ_WIN_COUNT_REWARDS: self.h_tianti_rewards,
            # tower
            P.REQUEST_TOWER_COPY_INFO: self.h_request_tower_info,
            P.ENTER_TOWER_COPY_INFO: self.h_request_tower_info,
            P.CONTINUE_TOWER_COPY: self.h_continue_tower_copy,
            P.GRANT_TOWER_REWARD: self.h_grant_tower_reward,
            P.TOWER_RESET: self.h_tower_reset,
            P.TOWER_WIPE_OUT: self.h_tower_wipe_out,
            # slot machine
            P.REQUEST_SLOT_INFO: self.h_request_slot_info,
            P.SPIN_SLOT: self.h_spin_slot,
            P.REQUEST_SLOT_SUM_REWARD: self.h_request_slot_sum_reward,
            # misc client progress
            P.TUTORIAL_FINISH: self.h_tutorial_finish,
            P.UNLOCK_FUNCTION_COMPLETE: self.h_unlock_function_complete,
            P.START_DOWNLOAD: self.h_noop,
            P.DOWNLOAD_FINISH: self.h_noop,
            P.RE_NAME: self.h_re_name,
            P.CHANGE_SHOW_TYPE: self.h_change_show_type,
            P.IMPACT_NPC: self.h_impact_npc,
            # wild boss / survive
            P.REQUEST_WILD_BOSS_INFO: self.h_request_wild_boss_info,
            P.ENTER_WILD_BOSS: self.h_enter_wild_boss,
            P.REQUEST_SURVIVE_TOP: self.h_request_survive_top,
            P.ENTER_SURVIVE_BATTLE: self.h_enter_survive_battle,
            P.SURVIVE_BATTLE_FINISH: self.h_survive_battle_finish,
            # guild battle (weekly war)
            P.REQ_GUILD_BATTLE_INFO: self.h_req_guild_battle_info,
            P.REQ_GUILD_BATTLE_STATE: self.h_req_guild_battle_state,
            P.SET_GUILD_BATTLE_MEMBER: self.h_set_guild_battle_member,
            P.REQ_GUILD_BATTLE_MEMBER: self.h_req_guild_battle_member,
            P.GUILD_BATTLE_GUESS: self.h_guild_battle_guess,
            P.REQ_GUILD_BATTLE_GUESS: self.h_req_guild_battle_guess,
            P.REQ_GUILD_BATTLE_RANK: self.h_req_guild_battle_rank,
            P.REQ_GUILD_SCORE_INFO: self.h_req_guild_score_info,
            P.ENTER_GUILD_BATTLE: self.h_enter_guild_battle,
            # login-time info burst (client fires these right after login;
            # unanswered ones leave the corresponding UI panel waiting forever)
            P.REQUEST_ACTIVITY_INFO: self.h_info_burst,
            P.REQUEST_DANCE_INFO: self.h_info_burst,
            P.REQUEST_GUILD_BOSS: self.h_info_burst,
            P.REQUEST_SIGN_30_DAY_INFO: self.h_info_burst,
            P.REQUEST_SIGN_WEEK_INFO: self.h_info_burst,
            P.REQUEST_INVEST_PACK: self.h_info_burst,
            P.REQUEST_DAILY_BUY: self.h_info_burst,
            P.REQUEST_DAILY_ACTIVE: self.h_info_burst,
            P.REQUEST_RETRIEVE_INFO: self.h_info_burst,
            P.REQ_LEVEL_REWARD: self.h_info_burst,
            P.REQUIRE_VIP_INFO: self.h_info_burst,
            P.REQUEST_DOMIN_INFO: self.h_info_burst,
            P.REQUEST_DANCE_STATE_INFO: self.h_info_burst,
            P.REQUEST_GUILD_MAP_INFO: self.h_info_burst,
        }

    # ------------------------------------------------------------------
    # gate (login server, port 9777)
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # login-time info burst: activity / sign-in / dance / vip / daily etc.
    # Each request gets its dedicated ret_* response with an EMPTY or
    # minimal body — the client treats an absent list as "no entries".
    # Schemas recovered from Assembly-CSharp.dll (dnfile field order):
    #   activity_info  ID/CurNum/Type/State/Parm/Parmstr/sign/time/next
    #   dance_info     ID/enable/useType/endTime
    #   dance_state_info uuid/ID/start_time/end_time/state/parm/duration/
    #                  reset_time/parm2
    #   daily_active   ID/count/Type   daily_buy ID/state  invest_pack ID/state
    #   level_reward   ID/state        retrieve_info ID/state/count
    #   guild_boss     id/state/time/curNum/sort_item
    #   guild_map_info id/guildId/guildName/guildIcon/requireState/state
    # ------------------------------------------------------------------
    async def h_info_burst(self, s: Session, msg) -> None:
        s.respond(msg, {})

    async def h_update_game_server(self, s: Session, msg) -> None:
        servers = [P.encode_game_server(
            server_id=config.SERVER_ID,
            name=config.SERVER_NAME,
            ip=self.server.advertise_ip or s.local_ip,
            port=config.ADVERTISE_PORT,
            state=0,
            player_state=0,
            area=0,
            rank=1,
            tz=8,
            weight=0,
            new_server=0,
        )]
        s.respond(msg, {2: sproto.encode_object_array(servers)})

    async def h_visitor(self, s: Session, msg) -> None:
        account_id, key = self.server.db.create_account()
        s.account_id = account_id
        log.info("created visitor account %d", account_id)
        # response {id(0), key(1), state(2)}
        s.respond(msg, {
            0: str(account_id),
            1: key,
            2: VERIFY_OK,
        })

    async def h_verfiy(self, s: Session, msg) -> None:
        account_id = int(msg.body.get(0, "0"))
        key = msg.body.get(1, "")
        # tag 2 = versionCode (string) — accepted but not enforced
        row = self.server.db.verify_account(account_id, key)
        if row is None:
            log.info("verfiy failed for account %s", account_id)
            s.respond(msg, {0: 1})   # state 1 = bad account
            return
        s.account_id = account_id
        s.verified = True
        session_id = self.server.next_session()
        log.info("verfiy ok account %d session %d", account_id, session_id)
        servers = [P.encode_game_server(
            server_id=config.SERVER_ID,
            name=config.SERVER_NAME,
            ip=self.server.advertise_ip or s.local_ip,
            port=config.ADVERTISE_PORT,
        )]
        # response {state(0), session(1), game_server(2), user_server(3),
        #           facebook_bind(4), versionCode(5), dataVersionCode(6),
        #           downloadFlag(7), notice(8), notice_version(9)}
        # user_server is a '#'-separated list of SERVER IDS the client
        # int.Parse()s (MenuSceneController.SaveUseServer) — not a name.
        s.respond(msg, {
            0: VERIFY_OK,
            1: session_id,
            2: sproto.encode_object_array(servers),
            3: str(config.SERVER_ID),
            4: 0,
            5: config.GAME_VERSION,
            6: config.DATA_VERSION,
            7: 0,
        })

    # ------------------------------------------------------------------
    # game server (port 9555)
    # ------------------------------------------------------------------
    async def h_login(self, s: Session, msg) -> None:
        account_id = int(msg.body.get(1, "0"))
        row = self.server.db.verify_account(account_id, "")
        # login.request {session(0), id(1), logintype(2), version(3),
        #                unityVersion(4), serverId(5), time(6)}
        # The game server trusts the connection: account id comes from the
        # verfiy step on the gate. Here we just accept and record.
        s.account_id = account_id or s.account_id
        s.logged_in = True
        log.info("login account %s logintype=%s", account_id,
                 msg.body.get(2))
        # response {type(0), versionCode(1), dataVersionCode(2), serverLevel(3)}
        s.respond(msg, {
            0: P.LOGIN,
            1: config.GAME_VERSION,
            2: config.DATA_VERSION,
            3: 0,
        })

    async def h_character_list(self, s: Session, msg) -> None:
        rows = self.server.db.list_characters(s.account_id or 0)
        # character_list.response {character(0)} — read_map of
        # character_overview objects (same wire layout as an object array).
        # The client dereferences .general.profession, .attribute_other.level
        # and .visual on each — a flat {id,name,level,sex} blob crashes it.
        chars = [W.encode_character_overview(r) for r in rows]
        s.respond(msg, {0: sproto.encode_object_array(chars)})

    async def h_character_create(self, s: Session, msg) -> None:
        # character_create.request {character: general{...}(0)}
        # The client sends a `general` object; we extract name/sex and the
        # profession (field 2: 0 Batfighter, 1 Boxer, 2 Gunner — the three
        # playable classes; PROFESSIONS maps them to weapon class + skills).
        name = None
        sex = 0
        profession = 0
        raw = msg.body.get(0)
        if isinstance(raw, (bytes, bytearray)):
            g = sproto.decode_fields(bytes(raw))
            name = g.get(0) if isinstance(g.get(0), str) else None
            # `general` has no surviving class in the decompiled dump. Accept
            # the profession on field 1 (preferred) with field 2 as fallback;
            # sex falls back to field 2 when 1 carries the profession.
            prof1 = g.get(1)
            prof2 = g.get(2)
            if isinstance(prof1, int) and prof1 in economy.PROFESSIONS:
                profession = prof1
                if isinstance(prof2, int):
                    sex = prof2
            elif isinstance(prof2, int) and prof2 in economy.PROFESSIONS:
                profession = prof2
        if not name:
            name = "Gangster%d" % (self.server.next_session() % 100000)
        row = self.server.db.create_character(s.account_id or 0, name, sex=sex,
                                              profession=profession)
        if row is None:
            s.respond(msg, {1: 1})  # errno: name taken
            return
        # grant the profession's starting weapon (tier 1 of its class) and
        # its real skill group (economy.PROFESSIONS[prof].skills)
        prof_def = economy.PROFESSIONS[profession]
        start_weapon = (profession + 1) * 10000 + 1
        if start_weapon in economy.ITEMS:
            self.server.db.add_item(row["id"], start_weapon, 1)
            self.server.db.set_equipped(row["id"], 0, start_weapon)
        for skill_id in prof_def["skills"]:
            self.server.db.learn_skill(row["id"], skill_id)
        # character_create.response {character(0), errno(1)} — the client
        # reads .general.profession, .createtime and .attribute_other.level
        # off a character_overview, then immediately sends character_pick.
        overview = W.encode_character_overview(row)
        s.respond(msg, {0: overview, 1: 0})

    async def h_character_pick(self, s: Session, msg) -> None:
        char_id = msg.body.get(0)
        row = self.server.db.get_character(char_id)
        if row is None or (row["account_id"] != (s.account_id or 0)):
            s.respond(msg, {0: 1})  # errno 1: not found
            return
        s.picked_character = row
        # Success reply carries an EMPTY body. The client's PickResponse
        # treats ANY response with an errno field — including errno 0 — as a
        # failure: it shows "Please try later!" (#{100153}), calls
        # LeaveGame() (disconnect) and drops back to the login scene. The
        # success path is just CloseBox()... which never runs here, so the
        # wait box also hangs. The real flow is: empty response, then the
        # enter_map push drives the scene load.
        s.respond(msg, {})
        # baseline syncs right after pick: skills + friends + storage
        self._sync_skills(s, row["id"])
        await self._push_friend_info(s)
        rows_storage = self.server.db.list_storage(row["id"])
        s.push(P.RET_REQUEST_UPDATE_STORAGEPACK,
               {0: sproto.encode_object_array(
                   [P.encode_item_stack(r["item_id"], r["count"])
                    for r in rows_storage])})
        # kick off the server-driven world entry (enter_map push)
        self._begin_world_entry(s, row)

    def _push_main_player_create(self, s: Session, wp) -> None:
        s.push(P.MAIN_PLAYER_CREATE, {0: W.encode_main_player_create(
            wp, skills=[(r["skill_id"], r["level"])
                        for r in self.server.db.list_skills(wp.char_id)])})

    async def h_map_ready(self, s: Session, msg) -> None:
        # Client finished loading the map scene (sent after our enter_map +
        # main_player_create pushes). The main player is already spawned by
        # then (main_player_create was buffered during the scene load), so
        # here we only deliver everyone already on the map + the map NPCs.
        wp = getattr(s, "pending_world_player", None)
        if wp is None:
            return
        s.pending_world_player = None
        s.world_player = wp
        for other in self.server.world.others(wp.map_id, wp.char_id):
            s.push(P.AOI_ADD, {0: W.encode_aoi_add(other)})
        for npc in self.server.world.npcs_in(wp.map_id):
            s.push(P.NPC_CREATE, {0: npc.blob()})
        self.server.world.join(wp)
        # tell everyone already here about the newcomer
        self.server.world.broadcast(wp.map_id, P.AOI_ADD,
                                    {0: W.encode_aoi_add(wp)},
                                    exclude=wp.char_id)
        log.info("%s entered map %s (line %s)", wp.name, wp.map_id,
                 wp.line_index)

    def _begin_world_entry(self, s: Session, row) -> None:
        """Start the server-driven world entry for a picked character.

        Real client flow (NetReceiver / LoadingUIRoot / ObjManager):
        the SERVER pushes enter_map(503) {mapInfoId, line_index,
        line_count} and then main_player_create(504) immediately after.
        enter_map makes the client stop processing frames
        (NetLogic.CanProcessPack = false in enter_map_handler) and load the
        map scene; the buffered main_player_create is processed once the
        scene's SceneController.Awake re-enables the packet pump, spawning
        the main player (ObjManager.CreateMainPlayer ->
        GameManager.IsSceneReady = true). Only THEN does the loading bar
        pass 90% (LoadingUIRoot caps it at 0.9 while !IsSceneReady), fire
        OnLoadingOver and send map_ready(100) — so a server that waits for
        map_ready before sending main_player_create deadlocks the loading
        screen at exactly 90% with only the BGM playing. The aoi/npc bursts
        go out after map_ready, when the scene is truly ready for them.
        """
        # 0 means "never entered the world yet"; fall back to the main city.
        # NEVER default to map "1" — in the client's MapInfoData table that is
        # the LoadingScene placeholder, and entering it hangs the loader.
        map_id = row["map_id"] if row["map_id"] not in (None, "", "1") \
            else economy.MAIN_CITY_MAP
        wp = W.WorldPlayer(s, row["id"], row["name"], row["level"],
                           row["sex"], row["profession"])
        wp.map_id = map_id
        wp.line_index = 0
        wp.pos = {
            "x": row["pos_x"], "y": row["pos_y"],
            "z": row["pos_z"], "o": row["pos_o"],
        }
        s.pending_world_player = wp
        s.push(P.ENTER_MAP, {
            0: map_id,          # mapInfoId (string)
            1: 0,               # line_index
            2: 1,               # line_count
        })
        # main_player_create MUST follow enter_map right away: the client
        # buffers it while the scene loads and spawns the player from it
        # (which is what releases the 90% loading cap). Sending it only
        # after map_ready deadlocks — the client never sends map_ready
        # before its main player exists.
        self._push_main_player_create(s, wp)

    async def h_enter_map(self, s: Session, msg) -> None:
        # Legacy request form (tests / reconnect helpers). The real client
        # never requests enter_map — the server pushes it after pick, and
        # the client answers with map_ready.
        map_id = msg.body.get(0, economy.MAIN_CITY_MAP)
        line_index = msg.body.get(1, 0)
        row = getattr(s, "picked_character", None)
        if row is None:
            rows = self.server.db.list_characters(s.account_id or 0)
            row = rows[0] if rows else None
        if row is None:
            return
        if isinstance(map_id, int):
            map_id = str(map_id)
        wp = W.WorldPlayer(s, row["id"], row["name"], row["level"],
                           row["sex"], row["profession"])
        wp.map_id = map_id
        wp.line_index = line_index
        wp.pos = {
            "x": row["pos_x"], "y": row["pos_y"],
            "z": row["pos_z"], "o": row["pos_o"],
        }
        s.pending_world_player = wp
        s.respond(msg, {0: W.encode_main_player_create(wp)})
        for other in self.server.world.others(map_id, row["id"]):
            s.push(P.AOI_ADD, {0: W.encode_aoi_add(other)})
        for npc in self.server.world.npcs_in(map_id):
            s.push(P.NPC_CREATE, {0: npc.blob()})
        self.server.world.broadcast(map_id, P.AOI_ADD,
                                    {0: W.encode_aoi_add(wp)},
                                    exclude=row["id"])
        self.server.world.join(wp)
        s.world_player = wp
        log.info("%s entered map %s (line %s)", row["name"], map_id, line_index)

    async def h_move(self, s: Session, msg) -> None:
        wp = s.world_player
        if wp is None:
            return
        # move.request {pos(0), moving(1), index(2), parm(3)}
        pos_raw = msg.body.get(0)
        if isinstance(pos_raw, (bytes, bytearray)):
            wp.pos = P.decode_position(bytes(pos_raw))
        moving = bool(msg.body.get(1, False))
        wp.moving = moving
        wp.walk = moving
        self.server.world.broadcast(
            wp.map_id, P.AOI_UPDATE_MOVE,
            {0: W.encode_aoi_update_move(wp)},
            exclude=wp.char_id,
        )
        self._progress_visit_missions(s, wp.char_id, wp.map_id)

    def _progress_visit_missions(self, s: Session, char_id: int,
                                 map_id: str) -> None:
        """Advance active 'visit' missions whose target map the player entered."""
        for row in self.server.db.list_missions(char_id):
            if row["state"] != 0:
                continue
            mdef = economy.MISSIONS.get(row["mission_id"])
            if not mdef or mdef.get("type") != "visit":
                continue
            if str(mdef.get("map_id")) != str(map_id):
                continue
            target = mdef.get("count", 1)
            progress = min(row["progress"] + 1, target)
            self.server.db.set_mission_progress(
                char_id, row["mission_id"], progress,
                1 if progress >= target else 0)
        self._sync_missions(s, char_id)

    async def h_chat(self, s: Session, msg) -> None:
        wp = s.world_player
        if wp is None:
            return
        # echo the chat request to the map (ret_chat pushes the same body)
        self.server.world.broadcast(
            wp.map_id, P.RET_CHAT, dict(msg.body), exclude=None
        )

    async def h_heart_beat(self, s: Session, msg) -> None:
        # heart_beat.request {time(0), time2(1)}
        client_time = msg.body.get(0, 0)
        s.respond(msg, {0: client_time, 1: int(time.time())})

    async def h_leave_game(self, s: Session, msg) -> None:
        wp = s.world_player
        if wp is not None:
            row = self.server.db.get_character(wp.char_id)
            if row is not None:
                self.server.db.save_position(
                    wp.char_id, wp.map_id,
                    wp.pos["x"], wp.pos["y"], wp.pos["z"], wp.pos["o"])
            self.server.world.leave(wp)
            s.world_player = None
        s.respond(msg, {})
        await s.close()

    async def h_refresh_online_state(self, s: Session, msg) -> None:
        s.respond(msg, {})

    async def h_update_client_state(self, s: Session, msg) -> None:
        s.respond(msg, {})

    async def h_game_check(self, s: Session, msg) -> None:
        s.respond(msg, {})

    async def h_retrieve_account(self, s: Session, msg) -> None:
        # Not supported in the revival (Facebook/Google bind unavailable).
        s.respond(msg, {0: 1})

    # ------------------------------------------------------------------
    # economy helpers
    # ------------------------------------------------------------------
    def _require_char(self, s: Session):
        """Return the picked character row, or None (client not ready)."""
        row = getattr(s, "picked_character", None)
        if row is not None:
            return row
        rows = self.server.db.list_characters(s.account_id or 0)
        return rows[0] if rows else None

    def _grant_mission_rewards(self, s: Session, char_id: int,
                               reward: dict) -> None:
        db = self.server.db
        gold = reward.get("gold", 0)
        diamond = reward.get("diamond", 0)
        items = reward.get("items", {})
        if gold:
            db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        if diamond:
            db.add_currency(char_id, economy.CURRENCY_DIAMOND, diamond)
        for item_id, count in items.items():
            db.add_item(char_id, item_id, count)
        stacks = [P.encode_item_stack(int(k), v)
                  for k, v in items.items()]
        s.push(P.SHOW_REWARD_ITEMS_TIPS, {
            0: gold,
            1: diamond,
            2: sproto.encode_object_array(stacks),
        })

    def _sync_missions(self, s: Session, char_id: int) -> None:
        rows = self.server.db.list_missions(char_id)
        blobs = [P.encode_mission_state(r["mission_id"], r["progress"],
                                        r["state"]) for r in rows]
        s.push(P.SYNC_MISSION, {0: sproto.encode_object_array(blobs)})

    def _sync_backpack(self, s: Session, char_id: int) -> None:
        rows = self.server.db.list_items(char_id)
        blobs = [P.encode_item_stack(r["item_id"], r["count"]) for r in rows]
        s.push(P.SYNC_BACKPACK_ITEM, {0: sproto.encode_object_array(blobs)})

    def _check_auto_complete(self, s: Session, char_id: int,
                             mission_row) -> None:
        """Flip a mission to 'complete' when its progress target is met."""
        mdef = economy.MISSIONS.get(mission_row["mission_id"])
        if mdef is None or mission_row["state"] != 0:
            return
        target = mdef.get("count", 1)
        if mission_row["progress"] >= target:
            self.server.db.set_mission_progress(
                char_id, mission_row["mission_id"], mission_row["progress"], 1)

    def _progress_buy_missions(self, s: Session, char_id: int,
                               item_id: int, count: int) -> None:
        """Advance any active 'buy' missions matching a shop purchase."""
        for row in self.server.db.list_missions(char_id):
            if row["state"] != 0:
                continue
            mdef = economy.MISSIONS.get(row["mission_id"])
            if not mdef or mdef.get("type") != "buy" or mdef.get("item_id") != item_id:
                continue
            progress = min(row["progress"] + count, mdef.get("count", 1))
            self.server.db.set_mission_progress(
                char_id, row["mission_id"], progress,
                1 if progress >= mdef.get("count", 1) else 0)
        self._sync_missions(s, char_id)

    # ------------------------------------------------------------------
    # missions
    # ------------------------------------------------------------------
    async def h_accept_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        mission_id = msg.body.get(0)
        mdef = economy.MISSIONS.get(mission_id)
        if mdef is None:
            s.respond(msg, {0: 2})   # unknown mission
            return
        if not self.server.db.accept_mission(char_id, mission_id):
            s.respond(msg, {0: 3})   # already active
            return
        s.respond(msg, {0: 0})
        self._sync_missions(s, char_id)
        log.info("char %d accepted mission %d", char_id, mission_id)

    async def h_complete_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        mission_id = msg.body.get(0)
        mrow = self.server.db.get_mission(char_id, mission_id)
        mdef = economy.MISSIONS.get(mission_id)
        if mrow is None or mdef is None:
            s.respond(msg, {0: 2})   # not accepted / unknown
            return
        target = mdef.get("count", 1)
        if mrow["progress"] < target or mrow["state"] != 1:
            s.respond(msg, {0: 3})   # objectives not met
            return
        s.respond(msg, {0: 0})
        # pay out and remove the mission (rewards push after the response)
        self.server.db.finish_mission(char_id, mission_id)
        self._grant_mission_rewards(s, char_id, mdef.get("reward", {}))
        self._sync_missions(s, char_id)
        self._sync_backpack(s, char_id)
        nxt = mdef.get("next")
        if nxt and nxt in economy.MISSIONS:
            self.server.db.accept_mission(char_id, nxt)
            self._sync_missions(s, char_id)
        log.info("char %d completed mission %d", char_id, mission_id)

    async def h_abandon_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        mission_id = msg.body.get(0)
        if self.server.db.get_mission(char_id, mission_id) is None:
            s.respond(msg, {0: 2})
            return
        self.server.db.finish_mission(char_id, mission_id)
        s.respond(msg, {0: 0})
        self._sync_missions(s, char_id)

    # ------------------------------------------------------------------
    # items
    # ------------------------------------------------------------------
    async def h_use_item(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        count = msg.body.get(1, 1)
        have = self.server.db.get_item_count(char_id, item_id)
        if have < count:
            s.respond(msg, {0: 2})   # not enough items
            return
        self.server.db.add_item(char_id, item_id, -count)
        s.respond(msg, {0: 0})
        s.push(P.UPDATE_ITEM, {0: item_id,
                               1: self.server.db.get_item_count(char_id, item_id),
                               2: 0})
        self._sync_backpack(s, char_id)

    async def h_sell_item(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        count = msg.body.get(1, 1)
        if self.server.db.get_item_count(char_id, item_id) < count:
            s.respond(msg, {0: 2})
            return
        self.server.db.add_item(char_id, item_id, -count)
        # flat 50% of a nominal 1000-gold item value — provisional economy
        gold = 500 * count
        new_gold = self.server.db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        s.respond(msg, {0: 0})
        s.push(P.UPDATE_ITEM, {0: item_id,
                               1: self.server.db.get_item_count(char_id, item_id),
                               2: 0})
        self._sync_backpack(s, char_id)

    # ------------------------------------------------------------------
    # shop
    # ------------------------------------------------------------------
    async def h_ask_shop_list(self, s: Session, msg) -> None:
        shop_id = msg.body.get(0, 1)
        shop = economy.SHOPS.get(shop_id)
        if shop is None:
            s.respond(msg, {0: 1})   # unknown shop
            return
        goods = [P.encode_shop_good(g["goods_id"], g["item_id"], g["count"],
                                    g["currency"], g["price"])
                 for g in shop["goods"]]
        s.respond(msg, {0: 0, 1: sproto.encode_object_array(goods)})

    async def h_buy_shop_item(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        goods_id = msg.body.get(0)
        count = msg.body.get(1, 1)
        good = None
        for shop in economy.SHOPS.values():
            for g in shop["goods"]:
                if g["goods_id"] == goods_id:
                    good = g
        if good is None or "item_id" not in good:
            s.respond(msg, {0: 2})   # unknown goods
            return
        total = good["price"] * count
        db = self.server.db
        if db.get_currency(char_id, good["currency"]) < total:
            s.respond(msg, {0: 3})   # not enough currency
            return
        db.add_currency(char_id, good["currency"], -total)
        new_count = db.add_item(char_id, good["item_id"], good["count"] * count)
        s.respond(msg, {0: 0})
        s.push(P.UPDATE_ITEM, {0: good["item_id"], 1: new_count, 2: 0})
        self._sync_backpack(s, char_id)
        self._progress_buy_missions(s, char_id, good["item_id"], good["count"] * count)
        log.info("char %d bought goods %d x%d for %d", char_id, goods_id,
                 count, total)

    # ------------------------------------------------------------------
    # inventory / equipment
    # ------------------------------------------------------------------
    def _sync_badges(self, s: Session, char_id: int) -> None:
        badges = [item for item in self.server.db.list_items(char_id)
                  if economy.ITEMS.get(item["item_id"], {}).get("type") == "badge"]
        blobs = [P.encode_item_stack(r["item_id"], r["count"]) for r in badges]
        s.push(P.SYNC_BADGEPACK_ITEM, {0: sproto.encode_object_array(blobs)})

    def _sync_fashion(self, s: Session, char_id: int) -> None:
        fashion = [item for item in self.server.db.list_items(char_id)
                   if economy.ITEMS.get(item["item_id"], {}).get("type") == "fashion"]
        blobs = [P.encode_item_stack(r["item_id"], r["count"]) for r in fashion]
        s.push(P.SYNC_FASHION_BACKPACK_ITEM,
               {0: sproto.encode_object_array(blobs)})

    async def h_equip_item(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        idef = economy.ITEMS.get(item_id)
        if idef is None or idef.get("type") != "equipment":
            s.respond(msg, {0: 2})
            return
        if db.get_item_count(char_id, item_id) < 1:
            s.respond(msg, {0: 3})
            return
        # weapon class must match the character's profession (real EquipData
        # Job rule: Batfighter/Boxer/Gunner items are class-locked)
        if idef.get("slot") == 0 and "weapon_class" in idef:
            prof = db.get_character(char_id)["profession"]
            if idef["weapon_class"] != prof:
                s.respond(msg, {0: 4})   # wrong profession
                return
        db.set_equipped(char_id, idef["slot"], item_id)
        s.respond(msg, {0: 0})
        self._sync_backpack(s, char_id)

    def _unequip_slot(self, s: Session, msg, slot: int) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        if db.get_equipped(row["id"], slot) is None:
            s.respond(msg, {0: 2})
            return
        db.set_equipped(row["id"], slot, None)
        s.respond(msg, {0: 0})

    async def h_unequip_item(self, s: Session, msg) -> None:
        await self._unequip_slot(s, msg, 1)  # armor

    async def h_equip_badge(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        idef = economy.ITEMS.get(item_id)
        if idef is None or idef.get("type") != "badge":
            s.respond(msg, {0: 2})
            return
        if db.get_item_count(char_id, item_id) < 1:
            s.respond(msg, {0: 3})
            return
        db.set_equipped(char_id, 2, item_id)
        s.respond(msg, {0: 0})
        self._sync_badges(s, char_id)

    async def h_unequip_badge(self, s: Session, msg) -> None:
        await self._unequip_slot(s, msg, 2)

    async def h_equip_fashion(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        idef = economy.ITEMS.get(item_id)
        if idef is None or idef.get("type") != "fashion":
            s.respond(msg, {0: 2})
            return
        if db.get_item_count(char_id, item_id) < 1:
            s.respond(msg, {0: 3})
            return
        db.set_equipped(char_id, 3, item_id)
        s.respond(msg, {0: 0})
        self._sync_fashion(s, char_id)

    async def h_unequip_fashion(self, s: Session, msg) -> None:
        await self._unequip_slot(s, msg, 3)

    async def h_open_item_package(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        idef = economy.ITEMS.get(item_id)
        if idef is None or idef.get("type") != "package":
            s.respond(msg, {0: 2})
            return
        if db.get_item_count(char_id, item_id) < 1:
            s.respond(msg, {0: 3})
            return
        db.add_item(char_id, item_id, -1)
        contents = idef.get("contents", {})
        gold = idef.get("gold", 0)
        if gold:
            db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        stacks = []
        for iid, cnt in contents.items():
            db.add_item(char_id, iid, cnt)
            stacks.append(P.encode_item_stack(iid, cnt))
        s.respond(msg, {0: 0, 1: sproto.encode_object_array(stacks)})
        self._sync_backpack(s, char_id)

    async def h_request_update_storagepack(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        rows = self.server.db.list_storage(row["id"])
        blobs = [P.encode_item_stack(r["item_id"], r["count"]) for r in rows]
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    async def h_put_item_storagepack(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        count = msg.body.get(1, 1)
        if db.get_item_count(char_id, item_id) < count:
            s.respond(msg, {0: 2})
            return
        db.add_item(char_id, item_id, -count)
        db.add_storage(char_id, item_id, count)
        s.respond(msg, {0: 0})
        self._sync_backpack(s, char_id)

    async def h_take_item_storagepack(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        item_id = msg.body.get(0)
        count = msg.body.get(1, 1)
        if db.get_storage_count(char_id, item_id) < count:
            s.respond(msg, {0: 2})
            return
        db.add_storage(char_id, item_id, -count)
        db.add_item(char_id, item_id, count)
        s.respond(msg, {0: 0})
        self._sync_backpack(s, char_id)

    async def h_request_random_name(self, s: Session, msg) -> None:
        sex = msg.body.get(0, 0)
        first = ["Johnny", "Vito", "Lucky", "Tony", "Frankie", "Sonny"] \
            if not sex else ["Maria", "Angela", "Rosa", "Gina", "Carmela"]
        last = ["Gambino", "Corleone", "Moretti", "Santoro", "Bianchi"]
        import random
        name = "%s %s" % (random.choice(first), random.choice(last))
        s.respond(msg, {0: name})

    async def h_change_item_state(self, s: Session, msg) -> None:
        # state toggle (e.g. lock item) — acknowledged, stored in progress
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        item_id = msg.body.get(0)
        state = msg.body.get(1, 0)
        self.server.db.set_progress(row["id"], "item_state_%d" % item_id, state)
        s.respond(msg, {0: 0})

    # ------------------------------------------------------------------
    # combat / npcs
    # ------------------------------------------------------------------
    def _player_attack_power(self, char_id: int) -> int:
        db = self.server.db
        attack = economy.PLAYER_BASE_ATTACK
        weapon = db.get_equipped(char_id, 0)
        if weapon is not None:
            attack += economy.ITEMS.get(weapon, {}).get("power", 0)
        badge = db.get_equipped(char_id, 2)
        if badge is not None:
            attack += economy.ITEMS.get(badge, {}).get("power", 0)
        return attack

    def _sync_skills(self, s: Session, char_id: int) -> None:
        # The client parses tag 0 as map<string, skill_info>: an object array
        # of skill_info blobs whose string skillId becomes the dict key.
        # Elements must be skill_info objects (string skillId!) or the client
        # throws "invalid pos" inside read_string and drops the push.
        rows = self.server.db.list_skills(char_id)
        blobs = [P.encode_skill_info(r["skill_id"], r["level"]) for r in rows]
        s.push(P.SYNC_SKILL_INFO, {0: sproto.encode_object_array(blobs)})

    async def h_skill_use(self, s: Session, msg) -> None:
        wp = s.world_player
        if wp is None:
            return
        skill_id = msg.body.get(0)
        target = msg.body.get(1)
        self.server.world.broadcast(
            wp.map_id, P.RET_SKILL_USE,
            {0: skill_id, 1: wp.char_id}, exclude=None)

    async def h_attack_local_npc(self, s: Session, msg) -> None:
        db = self.server.db
        wp = s.world_player
        if wp is None:
            return
        npc_id = msg.body.get(0)
        skill_id = msg.body.get(1, 1)
        npc = self.server.world.get_npc(wp.map_id, npc_id)
        if npc is None:
            s.respond(msg, {0: 2})   # unknown
            return
        if npc.dead:
            # lazy respawn: the NPC is back at full strength for this fight
            self.server.world.respawn_npc(npc)
        skill = economy.SKILLS.get(skill_id, {"damage": 5})
        skill_level = db.get_skill(wp.char_id, skill_id)
        if skill_level is not None:
            skill = dict(skill)
            skill["damage"] += 5 * (skill_level["level"] - 1)
        attack = self._player_attack_power(wp.char_id)
        damage = attack + skill["damage"]
        npc.hp = max(0, npc.hp - damage)
        # damage popup to everyone on the map — show_damage_board carries
        # an object array of acceptdamge at tag 0 (client: request.damges)
        self.server.world.broadcast(
            wp.map_id, P.SHOW_DAMAGE_BOARD,
            {0: P.encode_damage_board([P.encode_acceptdamge(
                npc_id, damage, str(skill_id))])})
        if npc.hp > 0:
            s.respond(msg, {0: 0})
            # the NPC fights back
            hp, max_hp = db.get_hp(wp.char_id)
            counter = self.server.world.npc_attack(npc)
            hp = db.set_hp(wp.char_id, hp - counter)
            self.server.world.broadcast(
                wp.map_id, P.ACCEPT_DAMGE,
                {0: P.encode_damage_board([P.encode_acceptdamge(
                    wp.char_id, counter)])})
            if hp <= 0:
                wp.dead = True
                # notice_relife_player: type(0) int, cost(1) int,
                # itemId(2) STRING, characterid(3) int, name(4) STRING.
                # The client dereferences GetItemDataByID(itemId).BackPackIcon,
                # so a valid (string) item id is mandatory — the revive
                # potion row from ItemData.
                self.server.world.broadcast(
                    wp.map_id, P.NOTICE_RELIFE_PLAYER,
                    {0: 1, 1: 0, 2: "9011", 3: wp.char_id, 4: wp.name})
            return
        # --- npc died ---
        exp, gold, drops = self.server.world.kill_npc(npc, wp.char_id, wp.name)
        # local_npc_die.npcid is a STRING on the client (read_string) — send
        # the npc's NpcData row id, which is also what FindObjInScene keys on
        # via ObjInitNpcData (mServerID is the int id; the death lookup uses
        # the row id, matching what npc_create carried).
        self.server.world.broadcast(
            wp.map_id, P.LOCAL_NPC_DIE,
            {0: economy.NPC_KINDS[npc.kind]["npcdataid"], 3: 0})
        s.respond(msg, {0: 0})
        for item_id, cnt in drops.items():
            db.add_item(wp.char_id, item_id, cnt)
            # drop_item_info's body IS the flat SprotoType.drop_item_info
            # object (serverId/pos_x/pos_z/type/item/ownServerId) — wrapping
            # it in {0: blob} makes the real client throw on decode and
            # freeze the moment loot drops.
            self.server.world.broadcast(
                wp.map_id, P.DROP_ITEM_INFO,
                P.encode_drop_item_info(npc_id, item_id, cnt,
                                        npc.pos["x"], npc.pos["z"]))
        if gold:
            db.add_currency(wp.char_id, economy.CURRENCY_GOLD, gold)
        level, exp_left = db.add_exp(wp.char_id, exp)
        gold_total = db.get_currency(wp.char_id, economy.CURRENCY_GOLD)
        hp, max_hp = db.get_hp(wp.char_id)
        # aoi_update_attribute is the client's real exp/level/hp/money sync
        # (ExpLineRootLogic.UpdateExp); sync_common_data is serverTime state
        # and must NOT carry level/exp.
        s.push(P.AOI_UPDATE_ATTRIBUTE, {0: P.encode_aoi_update_attribute(
            wp.char_id, hp, exp_left, level, max_hp, gold_total)})
        self._sync_backpack(s, wp.char_id)
        log.info("char %d killed npc %d (exp +%d gold +%d)", wp.char_id,
                 npc_id, exp, gold)

    async def h_local_npc_die(self, s: Session, msg) -> None:
        # client-confirmed npc death (copy scenes); treat as an attack result
        await self.h_attack_local_npc(s, msg)

    async def h_accept_damage(self, s: Session, msg) -> None:
        wp = s.world_player
        if wp is None:
            return
        # accept_damge body is SprotoType.accept_damge.request: damges(0) is
        # an OBJECT ARRAY of acceptdamge — mirror it to the map verbatim.
        self.server.world.broadcast(
            wp.map_id, P.ACCEPT_DAMGE,
            {0: sproto.encode_object_array(msg.body.get(0) or [])},
            exclude=None)
        s.respond(msg, {})

    async def h_relife_player(self, s: Session, msg) -> None:
        db = self.server.db
        wp = s.world_player
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        max_hp = db.get_hp(row["id"])[1]
        db.set_hp(row["id"], max_hp)
        if wp is not None:
            wp.dead = False
        s.respond(msg, {0: 0})
        if wp is not None:
            self.server.world.broadcast(
                wp.map_id, P.AOI_RELIFE_PLAYER, {0: wp.char_id})

    async def h_skill_level_up(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        skill_id = msg.body.get(0)
        if skill_id not in economy.SKILLS:
            s.respond(msg, {0: 2})
            return
        gold = db.get_currency(char_id, economy.CURRENCY_GOLD)
        if gold < economy.SKILL_LEVELUP_COST:
            s.respond(msg, {0: 3})
            return
        db.add_currency(char_id, economy.CURRENCY_GOLD,
                        -economy.SKILL_LEVELUP_COST)
        level = db.learn_skill(char_id, skill_id)
        s.respond(msg, {0: 0})
        self._sync_skills(s, char_id)

    # ------------------------------------------------------------------
    # guilds
    # ------------------------------------------------------------------
    def _guild_blob(self, g) -> bytes:
        members = self.server.db.guild_member_count(g["id"])
        return P.encode_guild_info(g["id"], g["name"], g["leader"],
                                   members, g["notice"], g["gold"], g["level"])

    def _require_guild(self, s: Session):
        row = self._require_char(s)
        if row is None:
            return None, None
        g = self.server.db.get_guild_by_member(row["id"])
        return row, g

    async def h_guild_create(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        if db.get_guild_by_member(row["id"]) is not None:
            s.respond(msg, {0: 2})   # already in a guild
            return
        name = msg.body.get(0, "")
        g = db.create_guild(name, row["name"])
        if g is None:
            s.respond(msg, {0: 3})   # name taken
            return
        db.add_guild_member(g["id"], row["id"], row["name"], job=0)
        db.add_guild_log(g["id"], "%s founded the guild" % row["name"])
        s.respond(msg, {0: 0, 1: g["id"]})

    async def h_guild_join(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        if db.get_guild_by_member(row["id"]) is not None:
            s.respond(msg, {0: 2})
            return
        guild_id = msg.body.get(0)
        g = db.get_guild(guild_id)
        if g is None:
            s.respond(msg, {0: 3})
            return
        db.add_guild_request(guild_id, row["id"], row["name"])
        s.respond(msg, {0: 0})
        # notify online officers/leader
        for m in db.list_guild_members(guild_id):
            if m["job"] in (0, 1):
                other = self.server.world.get_player_anywhere(m["char_id"])
                if other is not None:
                    other.conn.push(P.SYNC_GUILD_NEW_MEMBER,
                                    {0: row["name"]})

    async def h_guild_leave(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        if g is None:
            s.respond(msg, {0: 2})
            return
        db.remove_guild_member(g["id"], row["id"])
        db.add_guild_log(g["id"], "%s left the guild" % row["name"])
        s.respond(msg, {0: 0})

    async def h_guild_kick(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        me = db.get_guild_member(g["id"], row["id"])
        if me is None or me["job"] not in (0, 1):
            s.respond(msg, {0: 2})   # no permission
            return
        target_name = msg.body.get(0, "")
        target = None
        for m in db.list_guild_members(g["id"]):
            if m["name"] == target_name:
                target = m
        if target is None or target["job"] == 0:
            s.respond(msg, {0: 3})
            return
        db.remove_guild_member(g["id"], target["char_id"])
        db.add_guild_log(g["id"], "%s kicked %s" % (row["name"], target_name))
        s.respond(msg, {0: 0})

    async def h_guild_job_change(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        me = db.get_guild_member(g["id"], row["id"])
        if me is None or me["job"] != 0:
            s.respond(msg, {0: 2})   # leader only
            return
        target_name = msg.body.get(0, "")
        job = msg.body.get(1, 2)
        for m in db.list_guild_members(g["id"]):
            if m["name"] == target_name:
                db.set_guild_job(g["id"], m["char_id"], job)
                s.respond(msg, {0: 0})
                return
        s.respond(msg, {0: 3})

    async def h_guild_req_list(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        reqs = db.list_guild_requests(g["id"])
        blobs = [P.encode_guild_member(r["name"], 2) for r in reqs]
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    async def h_guild_req_info(self, s: Session, msg) -> None:
        row, g = self._require_guild(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        if g is None:
            s.respond(msg, {0: 2})
            return
        s.respond(msg, {0: self._guild_blob(g)})

    async def h_guild_approve(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        me = db.get_guild_member(g["id"], row["id"])
        if me is None or me["job"] not in (0, 1):
            s.respond(msg, {0: 2})
            return
        target_name = msg.body.get(0, "")
        approve = msg.body.get(1, 0)
        target = None
        for r in db.list_guild_requests(g["id"]):
            if r["name"] == target_name:
                target = r
        if target is None:
            s.respond(msg, {0: 3})
            return
        db.remove_guild_request(g["id"], target["char_id"])
        if approve:
            db.add_guild_member(g["id"], target["char_id"], target["name"])
            db.add_guild_log(g["id"], "%s joined the guild" % target["name"])
        s.respond(msg, {0: 0})

    async def h_req_guild_notice(self, s: Session, msg) -> None:
        row, g = self._require_guild(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        if g is None:
            s.respond(msg, {0: 2})
            return
        members = [P.encode_guild_member(m["name"], m["job"], online=self.server
                                         .world.get_player_anywhere(m["char_id"])
                                         is not None)
                   for m in self.server.db.list_guild_members(g["id"])]
        s.respond(msg, {
            0: self._guild_blob(g),
            1: sproto.encode_object_array(members),
        })

    async def h_req_open_guild_shop(self, s: Session, msg) -> None:
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        goods = [P.encode_shop_good(item["goods_id"], item["item_id"],
                                    item["count"], economy.CURRENCY_GOLD,
                                    item["price"])
                 for item in economy.GUILD_SHOP]
        s.respond(msg, {0: 0, 1: sproto.encode_object_array(goods)})

    async def h_req_buy_guild_goods(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        goods_id = msg.body.get(0)
        good = next((x for x in economy.GUILD_SHOP
                     if x["goods_id"] == goods_id), None)
        if good is None:
            s.respond(msg, {0: 2})
            return
        if g["gold"] < good["price"]:
            s.respond(msg, {0: 3})   # guild funds too low
            return
        db.add_guild_gold(g["id"], -good["price"])
        db.add_item(row["id"], good["item_id"], good["count"])
        s.respond(msg, {0: 0})
        self._sync_backpack(s, row["id"])

    async def h_guild_log(self, s: Session, msg) -> None:
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        entries = [sproto.encode_object({0: r["entry"], 1: r["created_at"]})
                   for r in self.server.db.list_guild_log(g["id"])]
        s.respond(msg, {0: sproto.encode_object_array(entries)})

    async def h_guild_donate(self, s: Session, msg) -> None:
        db = self.server.db
        row, g = self._require_guild(s)
        if row is None or g is None:
            s.respond(msg, {0: 1})
            return
        amount = msg.body.get(0, 0)
        if amount <= 0 or db.get_currency(row["id"],
                                          economy.CURRENCY_GOLD) < amount:
            s.respond(msg, {0: 2})
            return
        db.add_currency(row["id"], economy.CURRENCY_GOLD, -amount)
        gold = db.add_guild_gold(g["id"], amount)
        db.add_guild_log(g["id"], "%s donated %d gold" % (row["name"], amount))
        s.respond(msg, {0: 0, 1: gold})

    async def h_search_guild(self, s: Session, msg) -> None:
        pattern = msg.body.get(0, "")
        guilds = self.server.db.search_guilds(pattern)
        blobs = [self._guild_blob(g) for g in guilds]
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    # ------------------------------------------------------------------
    # friends
    # ------------------------------------------------------------------
    def _find_character_by_name(self, name: str):
        # simple lookup used by friends/mail; fine at revival scale
        return self.server.db._conn.execute(
            "SELECT * FROM characters WHERE name = ?", (name,)
        ).fetchone()

    async def h_add_friend(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        name = msg.body.get(0, "")
        target = self._find_character_by_name(name)
        if target is None:
            s.respond(msg, {0: 2})
            return
        db.add_friend(row["id"], target["id"])
        db.add_friend(target["id"], row["id"])
        # ret_add_friend carries ONE friend_info object (see encode_friend_entry)
        online = self.server.world.get_player_anywhere(target["id"]) is not None
        s.respond(msg, {0: P.encode_friend_entry(
            target["id"], target["name"], target["level"], online)})
        other = self.server.world.get_player_anywhere(target["id"])
        if other is not None:
            other.conn.push(P.NOTICE_ADD_FRIEND, {0: P.encode_friend_entry(
                row["id"], row["name"], row["level"], True)})

    async def h_del_friend(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        name = msg.body.get(0, "")
        target = self._find_character_by_name(name)
        if target is None:
            s.respond(msg, {0: 2})
            return
        db.remove_friend(row["id"], target["id"])
        db.remove_friend(target["id"], row["id"])
        s.respond(msg, {0: 0})
        other = self.server.world.get_player_anywhere(target["id"])
        if other is not None:
            other.conn.push(P.BE_DELETED_FRIEND, {0: row["id"]})

    async def h_ask_character_info(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        name = msg.body.get(0, "")
        target = self._find_character_by_name(name)
        if target is None:
            s.respond(msg, {0: 2})
            return
        online = self.server.world.get_player_anywhere(target["id"]) is not None
        s.respond(msg, {0: P.encode_friend_entry(
            target["id"], target["name"], target["level"], online)})

    async def h_sync_friend_info(self, s: Session, msg) -> None:
        await self._push_friend_info(s)

    async def _push_friend_info(self, s: Session) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            return
        # The client's syn_friend_info handler adds ONE friend per push, so
        # send one friend_info object per message (empty pushes are fine and
        # simply no-op client-side — HasFriend is false).
        for f in db.list_friends(row["id"]):
            fr = db.get_character(f["friend_id"])
            if fr is None:
                continue
            online = self.server.world.get_player_anywhere(fr["id"]) is not None
            s.push(P.SYN_FRIEND_INFO, {0: P.encode_friend_entry(
                fr["id"], fr["name"], fr["level"], online)})

    # ------------------------------------------------------------------
    # mail
    # ------------------------------------------------------------------
    async def h_send_mail(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        to_name = msg.body.get(0, "")
        title = msg.body.get(1, "")
        body = msg.body.get(2, "")
        target = self._find_character_by_name(to_name)
        if target is None:
            s.respond(msg, {0: 2})
            return
        db.send_mail(target["id"], row["name"], title, body)
        s.respond(msg, {0: 0})
        other = self.server.world.get_player_anywhere(target["id"])
        if other is not None:
            other.conn.push(P.MAIL_UPDATE,
                            {0: P.encode_mail(0, row["name"], title, body)})

    async def h_mail_operation(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        mail_id = msg.body.get(0)
        op = msg.body.get(1, 0)
        mail = db.get_mail(row["id"], mail_id)
        if mail is None:
            s.respond(msg, {0: 2})
            return
        if op == 1 and not mail["collected"]:   # collect attachment
            if mail["gold"]:
                db.add_currency(row["id"], economy.CURRENCY_GOLD, mail["gold"])
            if mail["diamond"]:
                db.add_currency(row["id"], economy.CURRENCY_DIAMOND,
                                mail["diamond"])
            db.set_mail_collected(mail_id)
        elif op == 2:                            # delete
            db.delete_mail(row["id"], mail_id)
        s.respond(msg, {0: 0})

    async def h_send_mail_box(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        mails = [P.encode_mail(m["id"], m["sender"], m["title"], m["body"],
                               m["gold"], m["diamond"], m["collected"])
                 for m in db.list_mails(row["id"])]
        s.respond(msg, {0: sproto.encode_object_array(mails)})

    # ------------------------------------------------------------------
    # daily missions / sign-in
    # ------------------------------------------------------------------
    async def h_request_daily_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        blobs = [P.encode_mission_state(mid, 0, 0)
                 for mid in economy.DAILY_MISSION_IDS]
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    def _day_index(self) -> int:
        return int(time.time()) // 86400

    async def h_sign_week(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        key = "sign_week_%d" % (self._day_index() // 7)
        days = db.get_progress(row["id"], key)
        if days >= 7:
            s.respond(msg, {0: 2, 1: days})   # already signed all week
            return
        db.set_progress(row["id"], key, days + 1)
        reward = 200 * (days + 1)
        db.add_currency(row["id"], economy.CURRENCY_GOLD, reward)
        s.respond(msg, {0: 0, 1: days + 1})
        s.push(P.SHOW_REWARD_ITEMS_TIPS,
               {0: reward, 1: 0, 2: sproto.encode_object_array([])})

    async def h_sign_30_day(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        key = "sign30_%d" % (self._day_index() // 30)
        days = db.get_progress(row["id"], key)
        if days >= 30:
            s.respond(msg, {0: 2, 1: days})
            return
        db.set_progress(row["id"], key, days + 1)
        reward_diamond = 2 * (days + 1)
        db.add_currency(row["id"], economy.CURRENCY_DIAMOND, reward_diamond)
        s.respond(msg, {0: 0, 1: days + 1})
        s.push(P.SHOW_REWARD_ITEMS_TIPS,
               {0: 0, 1: reward_diamond, 2: sproto.encode_object_array([])})

    # ------------------------------------------------------------------
    # mounts / cars
    # ------------------------------------------------------------------
    async def h_request_mount_info(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        entries = [P.encode_mount_info(r["car_id"], True, bool(r["using_car"]))
                   for r in db.list_cars(row["id"])]
        s.respond(msg, {0: sproto.encode_object_array(entries)})

    async def h_mount_equip(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        db.set_using_car(row["id"], msg.body.get(0))
        s.respond(msg, {0: 0})

    async def h_mount_unequip(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        s.respond(msg, {0: 0})

    async def h_use_mount(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        car_id = msg.body.get(0)
        if not db.list_cars(row["id"]):
            s.respond(msg, {0: 2})   # no car owned
            return
        db.set_using_car(row["id"], car_id)
        s.respond(msg, {0: 0})
        wp = s.world_player
        if wp is not None:
            self.server.world.broadcast(wp.map_id, P.AOI_ADD,
                                        {0: W.encode_aoi_add(wp)})

    async def h_unuse_mount(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        car = db.list_cars(row["id"])
        db.set_using_car(row["id"], car[0]["car_id"] if car else None)
        s.respond(msg, {0: 0})

    async def h_buy_car_shop(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        goods_id = msg.body.get(0)
        good = None
        for g in economy.SHOPS.get(9, {"goods": []})["goods"]:
            if g["goods_id"] == goods_id:
                good = g
        if good is None:
            s.respond(msg, {0: 2})
            return
        if db.get_currency(row["id"], good["currency"]) < good["price"]:
            s.respond(msg, {0: 3})
            return
        db.add_currency(row["id"], good["currency"], -good["price"])
        db.buy_car(row["id"], good["car_id"])
        s.respond(msg, {0: 0})
