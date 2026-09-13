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
from . import mission_data as M
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
            # offline chat history (tag 168; fires when the chat panel opens)
            P.REQ_OFFLINE_CHAT: self.h_req_offline_chat,
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
            P.REQUEST_TOP_RANK_LIST: self.h_request_top_rank_list,
            P.REQUEST_SPECIAL_BIG_PACK: self.h_request_special_big_pack,
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
        # IsVersionSame does int.Parse(dataVersionCode) — it must be a plain
        # integer string, not a dotted version (a dotted value throws
        # FormatException inside LoginResponse and the login dies silently).
        s.respond(msg, {
            0: P.LOGIN,
            1: config.GAME_VERSION,
            2: config.DATA_VERSION_INT,
            3: 0,
        })

    async def h_character_list(self, s: Session, msg) -> None:
        rows = self.server.db.list_characters(s.account_id or 0)
        # character_list.response {character(0)} — read_map of
        # character_overview objects (same wire layout as an object array).
        # The client dereferences .general.profession, .attribute_other.level
        # and .visual on each — a flat {id,name,level,sex} blob crashes it.
        chars = [W.encode_character_overview(
            r, db=self.server.db,
            comb_value=W.comb_value_for(self.server.db, r["id"],
                                         r["level"]))
            for r in rows]
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
        # Testing build: every new character starts at the max level with
        # maxed gold/diamond so all content is reachable immediately.
        row = self.server.db.create_character(
            s.account_id or 0, name, sex=sex, profession=profession,
            level=economy.TEST_MAX_LEVEL,
            extra={"gold": economy.TEST_START_GOLD,
                   "diamond": economy.TEST_START_DIAMOND})
        if row is None:
            s.respond(msg, {1: 1})  # errno: name taken
            return
        # grant the profession's starting weapon (tier 1 of its class), the
        # real tier-1 armor set (helmet/chest/legs/belt/necklace from the
        # recovered EquipData rows), the starter badge, and the class's real
        # skill group (economy.PROFESSIONS[prof].skills)
        prof_def = economy.PROFESSIONS[profession]
        start_weapon = (profession + 1) * 10000 + 1
        char_id = row["id"]
        if start_weapon in economy.ITEMS:
            self.server.db.add_item(char_id, start_weapon, 1)
            self.server.db.set_equipped(char_id, 0, start_weapon)
        # Real tier-1 armor per profession: helmet(2)/chest(3)/legs(4)/
        # belt(5)/necklace(6) -> db slots 1..5.
        for slot, item_id in economy.starter_armor(profession):
            self.server.db.add_item(char_id, item_id, 1)
            self.server.db.set_equipped(char_id, slot, item_id)
        # starter badge lives in its dedicated slot (8) so it never collides
        # with the six real equip slots
        for _slot, item_id in economy.STARTER_GEAR:
            if item_id in economy.ITEMS:
                self.server.db.add_item(char_id, item_id, 1)
                self.server.db.set_equipped(char_id,
                                            economy.BADGE_DB_SLOT, item_id)
        # EVERY new account gets the full fashion wardrobe (usable
        # immediately via the player-model page: equip/unequip + show/hide)
        for fashion_id in economy.ALL_FASHION_IDS:
            self.server.db.add_item(char_id, fashion_id, 1)
        # the class's real skill bar: x01 = basic attack (indexPos 3, the
        # client's basic-attack slot), the remaining five skills from the
        # 6-skill pool fill the two switch groups (indexPos 4..6 / 7..9 —
        # ObjMainPlayer.UpdateSkillIdList maps them onto the action slots)
        from . import game_data as GD
        pool = GD.WEAPON_SKILL_POOL.get(
            prof_def.get("weapon_type", 0), [])
        skill_plan = [(prof_def["skills"][0], 3)]  # basic attack
        for i, sid in enumerate(pool[:5]):
            skill_plan.append((sid, 4 + i))
        for sid, index_pos in skill_plan:
            self.server.db.learn_skill(char_id, sid)
            self.server.db.set_skill_index_pos(char_id, sid, index_pos)
        # the character's RANDOM STATUS: one genuinely random bonus rolled
        # ONCE at creation, independent of the base/default status, and
        # persisted in characters.data so login loads it instead of
        # regenerating or copying the base values.
        economy.roll_character_random_status(self.server.db, char_id)
        # Roll + persist a REAL instance for every starting piece ONCE (the
        # rolled skill/colors/attrs become permanent for this character),
        # then compute + persist the initial attribute set / power.
        for slot, item_id, _idx in self.server.db.list_equipped(char_id):
            idef = economy.ITEMS.get(item_id, {})
            if idef:
                self._get_or_create_instance(char_id, slot, item_id, idef)
        economy.recalc_character(self.server.db, char_id)
        # character_create.response {character(0), errno(1)} — the client
        # reads .general.profession, .createtime and .attribute_other.level
        # off a character_overview, then immediately sends character_pick.
        # combValue comes from the real formula (base attack + weapon +
        # badge power, scaled) — NOT 100*level, which showed a bogus
        # "power 8000" on the role-select screen at the test level 80.
        overview = W.encode_character_overview(
            row, comb_value=W.comb_value_for(self.server.db, row["id"],
                                             row["level"]))
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
        # sync_common_data BEFORE world entry: its seed fills the client's
        # randomArray (without it the first combat hit throws
        # DivideByZeroException in GetRandom) and its func_info unlocks the
        # bag/character/gang/vehicle/ranking buttons from level 1.
        s.push(P.SYNC_COMMON_DATA, P.encode_sync_common_data(
            int(time.time()), self.server.next_rng_seed()))
        # baseline syncs right after pick: skills + friends + storage +
        # the mission list (auto-accepts the tutorial main mission on new
        # accounts so the client has something to track from level 1)
        self._sync_skills(s, row["id"])
        self._ensure_first_mission(s, row["id"])
        # baseline CONTAINER syncs: main_player_create only fills the three
        # EQUIPPACK containers — the bag (592 EQUIP_BACKPACK), items (611
        # ITEM_BACKPACK), badges (604) and fashion wardrobe (616) must be
        # filled here or they render empty after every login.
        # fashion wardrobe top-up: accounts created before the grant existed
        # (or that somehow lost pieces) get the full set here — idempotent
        # (add_item caps at 1 per fashion id via count)
        for fashion_id in economy.ALL_FASHION_IDS:
            if self.server.db.get_item_count(row["id"], fashion_id) < 1:
                self.server.db.add_item(row["id"], fashion_id, 1)
        self._sync_backpack(s, row["id"])
        self._sync_item_pack(s, row["id"])
        self._sync_badges(s, row["id"])
        self._sync_fashion(s, row["id"])
        await self._push_friend_info(s)
        rows_storage = self.server.db.list_storage(row["id"])
        s.push(P.RET_REQUEST_UPDATE_STORAGEPACK,
               {0: sproto.encode_object_array(
                   [P.encode_item_stack(r["item_id"], r["count"])
                    for r in rows_storage])})
        # kick off the server-driven world entry (enter_map push)
        self._begin_world_entry(s, row)

    async def h_map_ready(self, s: Session, msg) -> None:
        # Client finished loading the map scene AND created the main player
        # (map_ready is only sent after main_player_create was processed).
        # Deliver the world contents: everyone already here, then the NPCs.
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

        Real client flow (NetReceiver / LoadingUIRoot): the SERVER pushes
        enter_map(503) {mapInfoId, line_index, line_count}; the client loads
        the map scene (CanProcessPack=false until SceneController.Awake).
        main_player_create(504) must ride WITH the enter_map push: the client
        only sends map_ready(100) AFTER its loading bar passes 0.9, and that
        bar is capped at 0.9 until GameManager.IsSceneReady — which is set by
        ObjManager.CreateMainPlayer, i.e. by the main_player_create push.
        Waiting for map_ready first deadlocks both sides at 90% with no
        exception (the eternal loading screen). Only the aoi/npc burst waits
        for map_ready.
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
        wp.comb_value = W.comb_value_for(self.server.db, row["id"],
                                         row["level"])
        s.pending_world_player = wp
        s.push(P.ENTER_MAP, {
            0: map_id,          # mapInfoId (string)
            1: 0,               # line_index
            2: 1,               # line_count
        })
        # main_player_create must arrive together with enter_map: the client
        # cannot send map_ready until the main player exists.
        # Equipped gear rides along as the character.equip gameitem map so
        # the spawn handler SyncPacks it into the client's EQUIPPACK. Every
        # piece is the PERSISTED rolled instance (index_id-linked): weapons
        # keep the skill/color they rolled once at creation, armor keeps its
        # rolled stat/color — never re-rolled at login.
        # (indexId, itemId, quality, level, random_attrs) - indexId must be
        # non-zero (0 is the client's "unknown" sentinel).
        equips = self._equipped_wire_items(wp.char_id)
        # the WORN fashion set + badge ride their own character-blob maps
        # (badge_equip tag 10 / fashion_equip tag 11) so the wardrobe and
        # the model's fashion visuals are correct at spawn
        fashion_equips = self._equipped_wire_items(
            wp.char_id, slots=tuple(range(economy.FASHION_DB_SLOT_BASE,
                                          economy.FASHION_DB_SLOT_BASE + 4)))
        badge_equips = self._equipped_wire_items(
            wp.char_id, slots=(economy.BADGE_DB_SLOT,))
        show_type = int(self.server.db.get_progress(wp.char_id, "show_type")
                        or 0)
        # the visual blob's fashion part ids: the worn FASHION_EQUIPPACK set
        # renders on spawn (the client falls back to the base parts when a
        # piece is missing, so a partially worn set is fine)
        # the worn weapon / fashion item ids ride the visual blob (fields
        # 14/15): the client's PlayerData uses WeaponItemId to pick the
        # weapon's render model and FashionItemId for the fashion weapon
        weapon_item = self.server.db.get_equipped(wp.char_id, 0)
        fashion_item = None
        wp.fashion_parts = (None, None, None, None)
        for slot, item_id, _idx in self.server.db.list_equipped(wp.char_id):
            if not (economy.FASHION_DB_SLOT_BASE <= slot
                    <= economy.FASHION_DB_SLOT_BASE + 3):
                continue
            model = economy.ITEMS.get(item_id, {}).get("model") or ""
            fslot = slot - economy.FASHION_DB_SLOT_BASE  # 0 head/1 body/2 wpn/3 leg
            if fslot == 0:
                wp.fashion_parts = (model or None,) + wp.fashion_parts[1:]
            elif fslot == 1:
                wp.fashion_parts = (wp.fashion_parts[0], model or None,
                                    wp.fashion_parts[2], wp.fashion_parts[3])
            elif fslot == 2:
                wp.fashion_parts = (wp.fashion_parts[0], wp.fashion_parts[1],
                                    model or None, wp.fashion_parts[3])
            elif fslot == 3:
                wp.fashion_parts = (wp.fashion_parts[0], wp.fashion_parts[1],
                                    wp.fashion_parts[2], model or None)
            if fslot == 2:
                fashion_item = item_id
        wp.weapon_item_id = str(weapon_item) if weapon_item else None
        wp.fashion_item_id = str(fashion_item) if fashion_item else None
        s.push(P.MAIN_PLAYER_CREATE, W.encode_main_player_create(
            wp, skills=[(r["skill_id"], r["level"], r["index_pos"])
                        for r in self.server.db.list_skills(wp.char_id)],
            equips=equips,
            attrs=self.server.db.load_attributes(wp.char_id) or None,
            hp=self.server.db.get_hp(wp.char_id)[1],
            badge_equips=badge_equips, fashion_equips=fashion_equips,
            show_type=show_type))

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
        s.respond(msg, W.encode_main_player_create(
            wp, skills=[(r["skill_id"], r["level"], r["index_pos"])
                        for r in self.server.db.list_skills(row["id"])],
            equips=self._equipped_wire_items(row["id"]),
            attrs=self.server.db.load_attributes(row["id"]) or None,
            hp=self.server.db.get_hp(row["id"])[1]))
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
        # persist the live position so a re-login resumes exactly where the
        # player was (and tutorial checkpoints are not replayed from spawn)
        self.server.db.save_position(
            wp.char_id, wp.map_id,
            wp.pos["x"], wp.pos["y"], wp.pos["z"], wp.pos["o"])
        self.server.world.broadcast(
            wp.map_id, P.AOI_UPDATE_MOVE,
            {0: W.encode_aoi_update_move(wp)},
            exclude=wp.char_id,
        )
        self._progress_visit_missions(s, wp.char_id, wp.map_id)

    def _progress_visit_missions(self, s: Session, char_id: int,
                                 map_id: str) -> None:
        """Advance active 'visit' missions whose target map the player entered."""
        changed = False
        for row in self.server.db.list_missions(char_id):
            if row["state"] != 0:
                continue
            mdef = economy.MISSIONS.get(str(row["mission_id"]))
            if not mdef or mdef.get("type") != "visit":
                continue
            if str(mdef.get("map_id")) != str(map_id):
                continue
            target = mdef.get("count", 1)
            progress = min(row["progress"] + 1, target)
            self.server.db.set_mission_progress(
                char_id, str(row["mission_id"]), progress,
                1 if progress >= target else 0)
            changed = True
        if changed:
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

    async def h_req_offline_chat(self, s: Session, msg) -> None:
        """req_offline_chat (168) fires when the client's chat panel first
        opens (PlayerChatHistory.InitOfflineChat). Reply with ret_offline_chat
        (579) carrying an EMPTY chat_list — the handler iterates it, so an
        unanswered request just leaves tag 168 'unhandled' in the logs.
        """
        s.respond(msg, {0: sproto.encode_object_array([])})

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
        exp = reward.get("exp", 0)
        items = reward.get("items", {})
        if gold:
            db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        if diamond:
            db.add_currency(char_id, economy.CURRENCY_DIAMOND, diamond)
        if exp:
            db.add_exp(char_id, exp)
            economy.recalc_character(self.server.db, char_id)
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
        """sync_mission(519) push with the real map<string, ownmission> body.

        last_missionId carries the highest *reached* main mission: when the
        active main mission is not in the map (e.g. after completion) the
        client auto-accepts its NextID from its local MissionData table —
        the chain advances even for client-tracked logic (level-up, copies).
        """
        rows = self.server.db.list_missions(char_id)
        blobs = []
        for r in rows:
            state = P.MISSION_COMPLETE if r["state"] == 1 \
                else P.MISSION_ACCEPTED
            # parm: [0]=kill/progress count, [7]=mission change time
            parm = [0] * 8
            parm[0] = r["progress"]
            parm[7] = r["accepted_at"]
            blobs.append(P.encode_ownmission(r["mission_id"], state, parm))
        last = self._last_main_mission(char_id)
        s.push(P.SYNC_MISSION, P.encode_sync_mission(blobs, last))

    def _last_main_mission(self, char_id: int) -> str:
        """Highest main-chain mission this character has reached."""
        mid = self.server.db.get_progress(char_id, "main_mission")
        return str(mid) if mid else M.first_main_mission()

    def _advance_main_chain(self, char_id: int) -> None:
        """Seed the main-chain cursor at the first mission (new accounts)."""
        cur = self._last_main_mission(char_id)
        if not self.server.db.get_progress(char_id, "main_mission"):
            self.server.db.set_progress(char_id, "main_mission",
                                        int(M.first_main_mission()))

    def _ensure_first_mission(self, s: Session, char_id: int) -> None:
        """Auto-accept the first main mission (tutorial kill) on new accounts
        and push the initial sync_mission so the tutorial car task exists."""
        for row in self.server.db.list_missions(char_id):
            if M.is_main_mission(str(row["mission_id"])):
                return
        first = M.first_main_mission()
        if self.server.db.accept_mission(char_id, first, int(time.time())):
            self.server.db.set_progress(char_id, "main_mission", int(first))
            self._sync_missions(s, char_id)

    def _push_mission_state(self, s: Session, mission_id: str,
                            state: int) -> None:
        """set_mission_state(523) — targeted single-mission state change."""
        s.push(P.SET_MISSION_STATE,
               P.encode_set_mission_state(mission_id, state))

    def _sync_backpack(self, s: Session, char_id: int) -> None:
        # sync_backpack_item(592) decodes map<indexId, gameitem> and only
        # updates entries found by indexId (or the first empty slot) — every
        # element must be a FULL gameitem blob or the bag renders empty.
        # Container: ITEM_CONTAINER_TYPE.EQUIP_BACKPACK = 0.
        # EXCLUDE equipped items: the client's equipment tab reads the
        # EQUIPPACK, but the bag grid shows every EQUIP_BACKPACK entry —
        # a worn piece that also appears here renders as a duplicate
        # ("items im wearing is the same as items in the bag").
        equipped_ids = {item_id for _slot, item_id, _idx in
                        self.server.db.list_equipped(char_id)}
        rows = [r for r in self.server.db.list_items(char_id)
                if r["item_id"] not in equipped_ids]
        instances = {i["item_id"]: i for i in
                     self.server.db.list_instances(char_id)}
        blobs = []
        for r in rows:
            blob = P.encode_backpack_gameitem(
                r, instances.get(r["item_id"]))
            blobs.append(blob)
        s.push(P.SYNC_BACKPACK_ITEM, {0: sproto.encode_object_array(blobs)})

    def _check_auto_complete(self, s: Session, char_id: int,
                             mission_row) -> None:
        """Flip a mission to 'complete' when its progress target is met."""
        mdef = economy.MISSIONS.get(str(mission_row["mission_id"]))
        if mdef is None or mission_row["state"] != 0:
            return
        target = mdef.get("count", 1)
        if mission_row["progress"] >= target:
            self.server.db.set_mission_progress(
                char_id, str(mission_row["mission_id"]),
                mission_row["progress"], 1)
    def _progress_buy_missions(self, s: Session, char_id: int,
                               item_id: int, count: int) -> None:
        """Legacy side-mission progression (buy-type missions)."""
        changed = False
        for row in self.server.db.list_missions(char_id):
            if row["state"] != 0:
                continue
            mdef = economy.MISSIONS.get(str(row["mission_id"]))
            if not mdef or mdef.get("type") != "buy" or mdef.get("item_id") != item_id:
                continue
            progress = min(row["progress"] + count, mdef.get("count", 1))
            self.server.db.set_mission_progress(
                char_id, str(row["mission_id"]), progress,
                1 if progress >= mdef.get("count", 1) else 0)
            changed = True
        if changed:
            self._sync_missions(s, char_id)

    # ------------------------------------------------------------------
    # missions (real protocol: string mission ids + ret_* RPC responses)
    # ------------------------------------------------------------------
    @staticmethod
    def _norm_mission_id(raw) -> str:
        """accept/complete/abandon requests carry the id as a STRING."""
        if isinstance(raw, bytes):
            return raw.decode("utf-8", "replace")
        return str(raw)

    async def h_accept_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: "", 2: 1})
            return
        char_id = row["id"]
        mission_id = self._norm_mission_id(msg.body.get(0, ""))
        if mission_id and self.server.db.accept_mission(
                char_id, mission_id, int(time.time())):
            ret = 0
        elif mission_id and self.server.db.get_mission(
                char_id, mission_id) is not None:
            # already active — the client auto-accepts the next main mission
            # from last_missionId and then re-sends accept_mission, so this
            # must be an idempotent success, not an error.
            ret = 0
        else:
            ret = 1   # unknown mission
        # ret_accept_mission {missionId(0), missionquality(1), ret(2),
        #                     mission(3) ownmission} — the client only
        # proceeds through AcceptMissionSuccess when ret succeeds.
        parm = [0] * 8
        parm[7] = int(time.time())
        s.respond(msg, {
            0: mission_id,
            2: ret,
            3: P.encode_ownmission(mission_id, P.MISSION_ACCEPTED, parm),
        })
        if ret == 0 and M.is_main_mission(mission_id):
            self.server.db.set_progress(char_id, "main_mission",
                                        int(mission_id))
        self._sync_missions(s, char_id)
        log.info("char %d accepted mission %s (ret=%d)", char_id,
                 mission_id, ret)

    async def h_complete_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: "", 1: 1})
            return
        char_id = row["id"]
        mission_id = self._norm_mission_id(msg.body.get(0, ""))
        mrow = self.server.db.get_mission(char_id, mission_id)
        if mrow is None:
            s.respond(msg, {0: mission_id, 1: 1})   # not accepted
            return
        # ret_complete_mission {missionId(0), ret(1)}
        s.respond(msg, {0: mission_id, 1: 0})
        # pay out and remove the mission
        self.server.db.finish_mission(char_id, mission_id)
        reward = M.mission_reward(mission_id)
        if reward:
            self._grant_mission_rewards(s, char_id, reward)
        # NOTE: the main-chain cursor stays on the COMPLETED mission — the
        # client sees last_missionId with no Class-1 mission in the map and
        # auto-accepts its NextID from its local table (SyncMissionList),
        # then the accept_mission RPC moves the cursor forward.
        self._sync_missions(s, char_id)
        self._sync_backpack(s, char_id)
        log.info("char %d completed mission %s", char_id, mission_id)

    async def h_abandon_mission(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: "", 1: 1})
            return
        char_id = row["id"]
        mission_id = self._norm_mission_id(msg.body.get(0, ""))
        if self.server.db.get_mission(char_id, mission_id) is None:
            s.respond(msg, {0: mission_id, 1: 1})
            return
        self.server.db.finish_mission(char_id, mission_id)
        # ret_abandon_mission {missionId(0), ret(1)}
        s.respond(msg, {0: mission_id, 1: 0})
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
        # use_item(115).request is {indexId(0), x(1), z(2)} — the real
        # client sends the ITEM INSTANCE id (ObjMainPlayer.UseDrag);
        # fall back to a raw item id for legacy tests.
        raw = msg.body.get(0)
        item_id, _idx = self._resolve_item_raw(self.server.db, char_id, raw)
        if item_id is None:
            s.respond(msg, {0: 2})   # unknown item
            return
        count = msg.body.get(1, 1)
        have = self.server.db.get_item_count(char_id, item_id)
        if have < count:
            s.respond(msg, {0: 2})   # not enough items
            return
        self.server.db.add_item(char_id, item_id, -count)
        s.respond(msg, {0: 0})
        # update_item {containertype=ITEM_BACKPACK(2), indexId, NO gameitem}
        # RESETS the old stack in the client's container; the fresh
        # container sync below re-adds the exact remaining stack.
        s.push(P.UPDATE_ITEM, {0: P.CONTAINER_ITEM_BACKPACK, 1: item_id})
        self._sync_backpack(s, char_id)

    async def h_sell_item(self, s: Session, msg) -> None:
        """sell_item(129) = the client's RECYCLE action (AppraiseRootLogic
        .OnClickRecycleBtn): {indexId(0), itemCount(1), type(2) container}.
        Accept the indexId form (the real client) and fall back to item-id
        stacks for legacy tests."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        raw = msg.body.get(0)
        count = msg.body.get(1, 1)
        item_id, index_id = self._resolve_item_raw(db, char_id, raw)
        if item_id is None or db.get_item_count(char_id, item_id) < count:
            s.respond(msg, {0: 2})
            return
        if index_id is not None:
            # a recycled instance disappears with its rolled attrs
            if db.find_slot_by_index(char_id, index_id) is not None:
                slot = db.find_slot_by_index(char_id, index_id)
                db.set_equipped(char_id, slot, None)
                self._push_item_update(
                    s, index_id, None, container=P.CONTAINER_EQUIPPACK)
            db.delete_instance(index_id)
        db.add_item(char_id, item_id, -count)
        # flat 50% of a nominal 1000-gold item value — provisional economy
        gold = 500 * count
        new_gold = db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        s.respond(msg, {0: 0})
        # reset the recycled stack in the client's ITEM_BACKPACK, then the
        # container sync re-adds whatever remains
        s.push(P.UPDATE_ITEM, {0: P.CONTAINER_ITEM_BACKPACK, 1: item_id})
        self._sync_backpack(s, char_id)
        self._recalc_and_sync(s, char_id)

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
        s.push(P.UPDATE_ITEM, {0: P.CONTAINER_ITEM_BACKPACK,
                               1: good["item_id"]})
        self._sync_backpack(s, char_id)
        self._progress_buy_missions(s, char_id, good["item_id"], good["count"] * count)
        log.info("char %d bought goods %d x%d for %d", char_id, goods_id,
                 count, total)

    # ------------------------------------------------------------------
    # inventory / equipment
    # ------------------------------------------------------------------
    @staticmethod
    def _index_is_instance(db, index_id) -> bool:
        """True when `index_id` names a real persisted item instance."""
        return isinstance(index_id, int) and db.get_instance(index_id) is not None

    def _resolve_item_raw(self, db, char_id: int, raw):
        """Resolve an item/itemInstance id from a client request into
        (item_id, index_id).

        Item instance ids and (legacy) item ids share the same small int
        space, so the resolver prefers the ITEM interpretation when the
        character actually owns a stack of that item id; otherwise a real
        persisted instance of the character wins. Stackables never have
        instances (their container indexId IS the item id), while equipment
        instance ids never collide with the owned stackable ids in
        practice.
        """
        if isinstance(raw, int) and raw in economy.ITEMS \
                and db.get_item_count(char_id, raw) > 0:
            return raw, None
        if self._index_is_instance(db, raw):
            inst = db.get_instance(raw)
            return inst["item_id"], inst["index_id"]
        if isinstance(raw, int) and raw in economy.ITEMS:
            return raw, None
        return None, None

    def _get_or_create_instance(self, char_id: int, slot: int, item_id: int,
                                idef: dict):
        """Return the persisted instance for an equipped item, rolling one
        ONLY if the slot has no instance yet (first equip). The rolled
        quality/attrs/skill are stored on item_instances and stay with the
        item for the item's lifetime — never re-rolled at login."""
        db = self.server.db
        index_id = db.get_equipped_index(char_id, slot)
        if index_id is not None:
            inst = db.get_instance(index_id)
            if inst is not None and inst["item_id"] == item_id:
                return inst
        is_weapon = idef.get("slot") == 0 or "weapon_class" in idef
        if is_weapon:
            quality, attrs = economy.roll_weapon_instance(item_id)
        else:
            # armor AND any other equippable: only the random rolls ride the
            # instance; base attrs come from the client's own EquipData
            quality, attrs = economy.roll_armor_instance(item_id)
        index_id = db.create_instance(char_id, item_id, quality, attrs)
        db.set_equipped(char_id, slot, item_id, index_id)
        return db.get_instance(index_id)

    def _equipped_wire_items(self, char_id: int, slots=None) -> list:
        """[(indexId, itemId, quality, level, random_attrs)] for every
        equipped slot, from the PERSISTED instances (no re-roll). Slots
        without a stored instance yet get one created exactly once.
        `slots` optionally restricts which db slots are returned (fashion
        9..12 / badge 8 have no rolled attrs and skip instance creation)."""
        equips = []
        for slot, item_id, index_id in self.server.db.list_equipped(char_id):
            if slots is not None and slot not in slots:
                continue
            idef = economy.ITEMS.get(item_id, {})
            inst = self._get_or_create_instance(char_id, slot, item_id, idef) \
                if index_id is None else self.server.db.get_instance(index_id)
            if inst is None:
                continue
            # gameitem.random_attri entries: (index, attr_id, value,
            # quality, skillId) — the client reads skillId as a string.
            wire_attrs = [(a[0], a[1], a[2], a[3], str(a[4]) if len(a) > 4
                           and a[4] else "") for a in inst["attrs"]]
            equips.append((index_id if index_id is not None else inst["index_id"],
                           item_id, inst["quality"], inst["level"],
                           wire_attrs))
        return equips

    @staticmethod
    def _push_item_update(s: Session, index_id: int, item_id: int,
                          container: int = None, quality: int = None,
                          level: int = 0, attrs: list = None) -> None:
        """update_item(525): {containertype(0), indexId(1), gameitem(2)}.

        The client's update_item_handler updates the GameItem found by
        indexId in that container (or Reset()s it when the gameitem field
        is ABSENT) — this is the real-time equip/unequip visual sync:
        EQUIPPACK (1) adds/removes gear from the character's back,
        EQUIP_BACKPACK (0) fills the bag slot.
        """
        body = {0: container if container is not None
                else P.CONTAINER_EQUIP_BACKPACK,   # EQUIP_BACKPACK = 0
                1: index_id}
        if item_id is not None:
            body[2] = P.encode_gameitem(
                index_id, item_id, stack=1,
                quality=quality if quality is not None else 2,
                level=level, random_attris=attrs)
        s.push(P.UPDATE_ITEM, body)

    def _sync_equip_change(self, s: Session, char_id: int,
                           equipped_slot: int = None,
                           removed: tuple = None) -> None:
        """Push the client-side container updates after an equip/unequip.

        `removed` is (indexId, itemId) of the piece that left the EQUIPPACK
        (update_item without a gameitem resets the slot -> naked model);
        `equipped_slot` re-syncs the whole EQUIPPACK map afterwards.
        """
        if removed is not None:
            idx, iid = removed
            # EQUIPPACK = 1: a gameitem-less update_item RESETS the slot —
            # this is what takes the piece off the character's model.
            self._push_item_update(s, idx, None,
                                   container=P.CONTAINER_EQUIPPACK)
            inst = self.server.db.get_instance(idx)
            if inst is not None:
                self._push_item_update(
                    s, idx, iid, container=P.CONTAINER_EQUIP_BACKPACK,
                    quality=inst["quality"], level=inst["level"],
                    attrs=[(a[0], a[1], a[2], a[3],
                            str(a[4]) if len(a) > 4 and a[4] else "")
                           for a in inst["attrs"]])
            else:
                self._push_item_update(s, idx, iid,
                                       container=P.CONTAINER_EQUIP_BACKPACK,
                                       quality=1)
        self._sync_backpack(s, char_id)
        if equipped_slot is not None or removed is not None:
            # re-send the full equip map so EQUIPPACK stays authoritative
            for widx, wiid, q, lvl, wattrs in \
                    self._equipped_wire_items(char_id):
                self._push_item_update(s, widx, wiid,
                                       container=P.CONTAINER_EQUIPPACK,
                                       quality=q, level=lvl, attrs=wattrs)

    def _recalc_and_sync(self, s: Session, char_id: int) -> None:
        """Recalculate the attribute set + power from the equipped instances
        and skills, persist it (characters.data), and push the new values
        with aoi_update_attribute. Called ONLY on change events."""
        row = self.server.db.get_character(char_id)
        if row is None:
            return
        attrs = economy.recalc_character(self.server.db, char_id)
        level, exp = row["level"], row["exp"]
        hp, max_hp = self.server.db.get_hp(char_id)
        gold = self.server.db.get_currency(char_id, economy.CURRENCY_GOLD)
        diamond = self.server.db.get_currency(char_id,
                                              economy.CURRENCY_DIAMOND)
        s.push(P.AOI_UPDATE_ATTRIBUTE, {0: P.encode_aoi_update_attribute(
            char_id, hp, exp, level, max_hp, gold, diamond,
            attrs=attrs, comb_value=attrs.get("power", 0))})

    def _sync_badges(self, s: Session, char_id: int) -> None:
        # sync_badgepack_item(604) fills the BADGE_BACKPACK container (3).
        badges = [item for item in self.server.db.list_items(char_id)
                  if economy.ITEMS.get(item["item_id"], {}).get("type") == "badge"]
        blobs = [P.encode_backpack_gameitem(r) for r in badges]
        s.push(P.SYNC_BADGEPACK_ITEM, {0: sproto.encode_object_array(blobs)})

    def _sync_fashion(self, s: Session, char_id: int) -> None:
        # sync_fashion_backpack_item(616) fills the FASHION_BACKPACK
        # container (5) — full gameitem blobs required.
        fashion = [item for item in self.server.db.list_items(char_id)
                   if economy.ITEMS.get(item["item_id"], {}).get("type") == "fashion"]
        blobs = [P.encode_backpack_gameitem(r) for r in fashion]
        s.push(P.SYNC_FASHION_BACKPACK_ITEM,
               {0: sproto.encode_object_array(blobs)})

    def _sync_item_pack(self, s: Session, char_id: int) -> None:
        """sync_item_pack(611) fills the ITEM_BACKPACK container (2) with
        every non-equipment/badge/fashion item. main_player_create only
        fills the three EQUIPPACK containers, so the baseline container
        syncs MUST ride with character_pick — without them the bag/wardrobe
        render empty after login (the disappearing-item report)."""
        blobs = []
        instances = {i["item_id"]: i for i in
                     self.server.db.list_instances(char_id)}
        for r in self.server.db.list_items(char_id):
            idef = economy.ITEMS.get(r["item_id"], {})
            if idef.get("type") in ("equipment", "badge", "fashion"):
                continue
            blobs.append(P.encode_backpack_gameitem(
                r, instances.get(r["item_id"])))
        s.push(P.SYNC_ITEM_PACK, {0: sproto.encode_object_array(blobs)})

    def _sync_show_type(self, s: Session, char_id: int,
                        show_type: int) -> None:
        """change_show_type(223) push: 1 = show fashion, 0 = show normal
        gear (the wardrobe's Show/Hide toggle)."""
        s.push(P.CHANGE_SHOW_TYPE, {0: int(show_type)})

    async def h_equip_item(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        raw = msg.body.get(0)
        # equip_item(115).request is {indexId(0), inhert(1)} — the ITEM
        # INSTANCE id (ObjMainPlayer.EquipItem), with a raw item id
        # fallback for legacy tests.
        item_id, _idx = self._resolve_item_raw(db, char_id, raw)
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
        # slot: use the recovered client Position for armor pieces
        # (Position p -> db slot p-1); weapons stay at slot 0.
        slot = economy.slot_for(item_id)
        if slot is None:
            slot = idef.get("slot", 0)
        # roll + persist a REAL instance on first equip; re-equips reuse it
        inst = self._get_or_create_instance(char_id, slot, item_id, idef)
        s.respond(msg, {0: 0})
        # real-time visual sync: put the piece on the character's back
        # (EQUIPPACK = 1) and REMOVE it from the bag grid (a gameitem-less
        # EQUIP_BACKPACK update_item resets that bag slot — otherwise the
        # item shows both worn and in the bag)
        self._push_item_update(
            s, inst["index_id"], item_id, container=P.CONTAINER_EQUIPPACK,
            quality=inst["quality"], level=inst["level"],
            attrs=[(a[0], a[1], a[2], a[3],
                    str(a[4]) if len(a) > 4 and a[4] else "")
                   for a in inst["attrs"]])
        self._push_item_update(s, inst["index_id"], None,
                               container=P.CONTAINER_EQUIP_BACKPACK)
        self._sync_equip_change(s, char_id)
        self._recalc_and_sync(s, char_id)

    def _unequip_index(self, s: Session, msg, index_id: int) -> None:
        """Unequip by ITEM INSTANCE id. The real client's UnEquipItem sends
        gameitem.indexId (ObjMainPlayer.UnEquipItem), never a slot number —
        the slot is derived by finding which equip slot holds the instance.
        The item stays in the backpack as its persisted instance; stats and
        power are recalculated without it and the new state is saved (the
        equip_slots row is deleted, so relogin cannot re-equip it)."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        slot = db.find_slot_by_index(char_id, index_id)
        if slot is None:
            # not equipped (or a legacy slot-only id) — idempotent success
            # so the client's equipment UI always clears.
            s.respond(msg, {0: 0})
            self._recalc_and_sync(s, char_id)
            return
        removed_inst = self.server.db.get_instance(index_id)
        db.set_equipped(char_id, slot, None)
        s.respond(msg, {0: 0})
        # real-time visual sync: reset the EQUIPPACK slot (naked model),
        # re-add the item to the bag, then recalc stats/power
        self._sync_equip_change(s, char_id,
                                removed=(index_id, removed_inst["item_id"]
                                         if removed_inst else None))
        self._recalc_and_sync(s, char_id)

    def _unequip_slot(self, s: Session, msg, slot: int) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        # empty the slot (item stays in the backpack as its persisted
        # instance) then recalc stats/power without it
        index_id = db.get_equipped_index(char_id, slot)
        item_id = db.get_equipped(char_id, slot)
        if item_id is None:
            s.respond(msg, {0: 2})
            return
        db.set_equipped(char_id, slot, None)
        s.respond(msg, {0: 0})
        self._sync_equip_change(s, char_id,
                                removed=(index_id, item_id)
                                if index_id else None)
        self._recalc_and_sync(s, char_id)

    async def h_unequip_item(self, s: Session, msg) -> None:
        # unequip_item(117).request is {indexId(0)} — the ITEM INSTANCE id
        # (SprotoType.unequip_item + ObjMainPlayer.UnEquipItem), NOT a slot.
        # The legacy path by slot number stays as a fallback for ids that
        # don't match an equipped instance.
        raw = msg.body.get(0)
        if self._index_is_instance(self.server.db, raw):
            self._unequip_index(s, msg, raw)
            return
        # fallback: treat small ints as EQUIP_BACKPACK_TYPE slots
        # (0 weapon, 1 head, 2 body, 3 legs, 4 belt, 5 necklace).
        # NOTE: _unequip_slot is a plain (sync) method — it must NOT be
        # awaited or the dispatch raises "object NoneType can't be used in
        # 'await' expression" and tag 117 never gets a response.
        slot = raw
        if slot is None or slot == 0:
            self._unequip_slot(s, msg, 0)   # weapon
        elif isinstance(slot, int) and 1 <= slot <= 5:
            self._unequip_slot(s, msg, slot)
        else:
            s.respond(msg, {0: 2})

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
        db.set_equipped(char_id, economy.BADGE_DB_SLOT, item_id)
        s.respond(msg, {0: 0})
        self._sync_badges(s, char_id)
        self._recalc_and_sync(s, char_id)

    async def h_unequip_badge(self, s: Session, msg) -> None:
        raw = msg.body.get(0)
        if self._index_is_instance(self.server.db, raw):
            self._unequip_index(s, msg, raw)
        else:
            self._unequip_slot(s, msg, economy.BADGE_DB_SLOT)

    async def h_equip_fashion(self, s: Session, msg) -> None:
        # equip_fashion_item(221).request is {indexId(0)} — the ITEM INSTANCE
        # id (ObjMainPlayer.EquipFashionItem), fall back to a raw item id for
        # legacy clients/tests.
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        raw = msg.body.get(0)
        item_id, index_id = self._resolve_item_raw(db, char_id, raw)
        idef = economy.ITEMS.get(item_id)
        if idef is None or idef.get("type") != "fashion":
            s.respond(msg, {0: 2})
            return
        if db.get_item_count(char_id, item_id) < 1:
            s.respond(msg, {0: 3})
            return
        slot = economy.fashion_slot_for(item_id)
        if index_id is None:
            index_id = db.create_instance(char_id, item_id, 0, [])
        db.set_equipped(char_id, slot, item_id, index_id)
        s.respond(msg, {0: 0})
        # FASHION_EQUIPPACK (container 6) visual update + wardrobe sync
        self._push_item_update(s, index_id, item_id,
                               container=P.CONTAINER_FASHION_EQUIPPACK,
                               quality=0)
        self._sync_fashion(s, char_id)
        # show fashion automatically when a piece is equipped
        self._sync_show_type(s, char_id, 1)

    async def h_unequip_fashion(self, s: Session, msg) -> None:
        # unequip_fashion_item(222).request is {indexId(0)}
        self._unequip_fashion_index(s, msg, msg.body.get(0))

    def _unequip_fashion_index(self, s: Session, msg, index_id: int) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        slot = db.find_slot_by_index(char_id, index_id)
        if slot is None or not (economy.FASHION_DB_SLOT_BASE <= slot
                                <= economy.FASHION_DB_SLOT_BASE + 3):
            s.respond(msg, {0: 0})   # idempotent: clear the UI either way
            return
        db.set_equipped(char_id, slot, None)
        s.respond(msg, {0: 0})
        # reset the FASHION_EQUIPPACK slot (container 6; a gameitem-less
        # update_item resets the slot -> the visual piece is removed)
        self._push_item_update(s, index_id, None,
                               container=P.CONTAINER_FASHION_EQUIPPACK)
        self._sync_fashion(s, char_id)

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
        # chest contents can include gear whose instances change the
        # attribute set? (instances roll at equip time) — recalc keeps
        # power in sync after reward pickups regardless.
        self._recalc_and_sync(s, char_id)

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
        # Server-authoritative power: the persisted attribute set's attack
        # (base + gear + skill contributions, recalculated on change events)
        # — the same value the client's attribute_all.atk prints.
        attrs = self.server.db.load_attributes(char_id)
        if attrs.get(1001):
            return int(attrs[1001])
        # migration: no saved set yet — compute it once now
        attrs = economy.recalc_character(self.server.db, char_id)
        return int(attrs.get(1001, economy.PLAYER_BASE_ATTACK))

    def _sync_skills(self, s: Session, char_id: int) -> None:
        # The client parses tag 0 as map<string, skill_info>: an object array
        # of skill_info blobs whose string skillId becomes the dict key.
        # Elements must be skill_info objects (string skillId!) or the client
        # throws "invalid pos" inside read_string and drops the push.
        rows = self.server.db.list_skills(char_id)
        blobs = [P.encode_skill_info(r["skill_id"], r["level"],
                                     index_pos=r["index_pos"],
                                     index_pos2=r["index_pos"])
                 for r in rows]
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
        """attack_local_npc(317) — client-side combat flavor: {damge(0) i,
        effinfoId(1) s}. The client kills NPCs locally; this only shows the
        damage board and lets the NPC fight back. The kill itself arrives
        via local_npc_die(307)."""
        wp = s.world_player
        if wp is None:
            return
        damage = msg.body.get(0, 0)
        effinfo_id = msg.body.get(1, "")
        if isinstance(effinfo_id, bytes):
            effinfo_id = effinfo_id.decode("utf-8", "replace")
        if damage:
            self.server.world.broadcast(
                wp.map_id, P.SHOW_DAMAGE_BOARD,
                {0: P.encode_damage_board([P.encode_acceptdamge(
                    wp.char_id, damage, str(effinfo_id))])})
        s.respond(msg, {0: 0})

    async def h_local_npc_die(self, s: Session, msg) -> None:
        """local_npc_die(307) — the client kills NPCs locally and reports the
        death: {npcid(0) STRING, x(1) i, z(2) i, type(3) i}. This is the REAL
        kill path: grant exp/gold/loot, count mission kills, and lazily
        respawn the NPC for the next fight.
        """
        db = self.server.db
        wp = s.world_player
        row = self._require_char(s)
        if wp is None or row is None:
            s.respond(msg, {0: 1})
            return
        npcid = msg.body.get(0, "")
        if isinstance(npcid, bytes):
            npcid = npcid.decode("utf-8", "replace")
        die_type = msg.body.get(3, 0)
        # Find the world NPC by NpcData row id (what npc_create carried) or
        # by its int server id as a fallback.
        npc = None
        for cand in self.server.world.npcs_in(wp.map_id):
            if economy.NPC_KINDS[cand.kind]["npcdataid"] == npcid \
                    or str(cand.npc_id) == npcid:
                npc = cand
                break
        # Legacy/unknown ids (tutorial scene kills, ragdoll impacts) still get
        # a base reward — otherwise the kill silently does nothing.
        if npc is not None:
            exp, gold, drops = self.server.world.kill_npc(
                npc, wp.char_id, wp.name)
            # the death is now registered (dead flag + hp 0); the lazy
            # respawn moves BELOW so kill-driven mission progress sees the
            # dead NPC first.
        else:
            base = economy.NPC_KINDS[1]
            exp, gold, drops = base["exp"], base["gold"], {}
        for item_id, cnt in drops.items():
            db.add_item(wp.char_id, item_id, cnt)
            # encode_drop_item_info returns the PUSH BODY fields (the push
            # body IS the drop_item_info.request object) — passing it as a
            # nested value under tag 0 breaks sproto encoding.
            self.server.world.broadcast(
                wp.map_id, P.DROP_ITEM_INFO,
                P.encode_drop_item_info(
                    npc.npc_id if npc else 0, item_id, cnt,
                    msg.body.get(1, 0) / 100.0, msg.body.get(2, 0) / 100.0))
        if gold:
            db.add_currency(wp.char_id, economy.CURRENCY_GOLD, gold)
        level, exp_left = db.add_exp(wp.char_id, exp)
        gold_total = db.get_currency(wp.char_id, economy.CURRENCY_GOLD)
        hp, max_hp = db.get_hp(wp.char_id)
        # aoi_update_attribute is the client's real exp/level/hp/money sync
        # (ExpLineRootLogic.UpdateExp). A kill grants exp — a change event —
        # so the attribute set (and max_hp) is recalculated and rides along.
        attrs = economy.recalc_character(db, wp.char_id)
        s.push(P.AOI_UPDATE_ATTRIBUTE, {0: P.encode_aoi_update_attribute(
            wp.char_id, hp, exp_left, level, max_hp, gold_total,
            attrs=attrs, comb_value=attrs.get("power", 0))})
        self._sync_backpack(s, wp.char_id)
        # Count the kill towards active kill-type missions (main-chain
        # KILL_TARGET_NPC/KILLMONSTER and side missions) while the NPC is
        # still registered dead; the respawn runs right after.
        self._progress_kill_missions(s, wp.char_id, npcid)
        if npc is not None:
            self.server.world.respawn_npc(npc)
        # Echo the death to the rest of the map so other clients see the kill.
        self.server.world.broadcast(
            wp.map_id, P.LOCAL_NPC_DIE,
            {0: npcid, 1: msg.body.get(1, 0), 2: msg.body.get(2, 0),
             3: die_type}, exclude=wp.char_id)
        s.respond(msg, {0: 0})
        log.info("char %d npc die npcid=%s type=%s (exp +%d gold +%d)",
                 wp.char_id, npcid, die_type, exp, gold)

    def _progress_kill_missions(self, s: Session, char_id: int,
                                npcid: str) -> None:
        """Advance active kill-type missions whose target is this NPC.

        Main-chain missions use MISSION_LOGICTYPE KILLMONSTER(1)/
        LOCAL_KILL_MONSTER(14)/KILL_TARGET_NPC(23) and match
        missionData.Target against the dying NPC's id. The recovered main
        chain stores its own target ids (mission 1001 targets "9901", the
        tutorial kill) that do NOT equal the NpcData row id the client
        reports ("21131"...), so a kill counts when the reported id matches
        ANY spelling of the NPC: raw npcid, its NpcData id, its kind server
        id, or its kind index.
        """
        # every id this kill could legitimately be matched by
        npc_ids = {str(npcid)}
        for kind, kdef in economy.NPC_KINDS.items():
            if kdef["npcdataid"] == npcid:
                npc_ids.update({str(kind), str(kdef["npcdataid"])})

        changed = False
        for mrow in self.server.db.list_missions(char_id):
            if mrow["state"] != 0:
                continue
            mid = str(mrow["mission_id"])
            mdef = M.MAIN_MISSIONS.get(mid)
            if mdef is not None:
                logic_type = mdef.get("logic_type")
                if logic_type not in (1, 14, 23):
                    continue
                target = mdef.get("target")
            else:
                sdef = economy.MISSIONS.get(mid)
                if not sdef or sdef.get("type") != "kill":
                    continue
                target = sdef.get("npc_id")
            if target is not None and str(target) not in npc_ids:
                continue
            mrow2 = self.server.db.get_mission(char_id, mrow["mission_id"])
            if mrow2 is None or mrow2["state"] != 0:
                continue
            progress = mrow2["progress"] + 1
            self.server.db.set_mission_progress(
                char_id, mrow["mission_id"], progress, 1)
            changed = True
        if changed:
            self._sync_missions(s, char_id)

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
        self._recalc_and_sync(s, char_id)

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
