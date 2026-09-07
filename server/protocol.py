"""Protocol tag registry + message schema definitions.

Ported from the decompiled `SprotoType.*` classes of Assembly-CSharp.dll.

Every message is a dict {sproto_tag: value}. Composite fields (nested objects
and arrays) are pre-encoded with the helpers in `sproto.py` and passed as
`bytes`.
"""

from . import sproto as _enc

# --- protocol tags (from Protocol.*.cs) ------------------------------------
VISITOR = 2
VERFIY = 3
LOGIN = 4
FACEBOOK_LINK = 5
FACEBOOK_UNLINK = 6
UPDATE_GAME_SERVER = 7

MAP_READY = 100
MOVE = 101
SKILL_USE = 102
CHARACTER_LIST = 103
CHARACTER_CREATE = 104
CHARACTER_PICK = 105

CHAT = 120
RELIFE_PLAYER = 132

UPDATE_CLIENT_STATE = 280
REFRESH_ONLINE_STATE = 281
GAME_CHECK = 308

ENTER_MAP = 503
MAIN_PLAYER_CREATE = 504
AOI_ADD = 505
AOI_REMOVE = 506
AOI_UPDATE_MOVE = 507
RET_SKILL_USE = 508
AOI_UPDATE_ATTRIBUTE = 510
AOI_RELIFE_PLAYER = 512
AOI_STOP_MOVE = 513
RET_CHAT = 528

HEART_BEAT = 218
LEAVE_GAME = 234

# --- missions (tags from Protocol registry; schemas provisional)  ----------
ACCEPT_MISSION = 112
COMPLETE_MISSION = 113
ABANDON_MISSION = 114
USE_ITEM = 115
SELL_ITEM = 129
SYNC_MISSION = 519
RET_ACCEPT_MISSION = 520
RET_COMPLETE_MISSION = 521
RET_ABANDON_MISSION = 522
SET_MISSION_STATE = 523
SET_MISSION_PARAM = 524
UPDATE_ITEM = 525
RET_USE_ITEM = 526
SYNC_BACKPACK_ITEM = 592
SHOW_REWARD_ITEMS_TIPS = 638

# --- shop -----------------------------------------------------------------
ASK_SHOP_LIST = 143
BUY_SHOP_ITEM = 144
RET_ASK_SHOP_LIST = 554
RET_BUY_SHOP_ITEM = 652

# --- inventory / equipment -------------------------------------------------
EQUIP_ITEM = 116
UNEQUIP_ITEM = 117
EQUIP_BADGE = 197
UNEQUIP_BADGE = 198
EQUIP_FASHION_ITEM = 221
UNEQUIP_FASHION_ITEM = 222
OPEN_ITEM_PACKAGE = 224
RET_OPEN_ITEM_PACKAGE = 617
REQUEST_UPDATE_STORAGEPACK = 139
PUT_ITEM_STORAGEPACK = 140
TAKE_ITEM_STORAGEPACK = 141
RET_REQUEST_UPDATE_STORAGEPACK = 550
REQUEST_RANDOM_NAME = 118
CHANGE_ITEM_STATE = 240
SYNC_BADGEPACK_ITEM = 604
SYNC_FASHION_BACKPACK_ITEM = 616
SYNC_ITEM_PACK = 611

# --- combat / npcs ---------------------------------------------------------
SKILL_USE = 102
ACCEPT_DAMGE = 111
LOCAL_NPC_DIE = 307
ATTACK_LOCAL_NPC = 317
RELIFE_PLAYER = 132
NPC_CREATE = 509
SHOW_DAMAGE_BOARD = 511
AOI_RELIFE_PLAYER = 512
DROP_ITEM_INFO = 527
NOTICE_RELIFE_PLAYER = 618
SYNC_SKILL_INFO = 540
SKILL_LEVEL_UP = 130
SYNC_COMMON_DATA = 614

# --- guilds ----------------------------------------------------------------
GUILD_CREATE = 146
GUILD_JOIN = 147
GUILD_LEAVE = 148
GUILD_KICK = 149
GUILD_JOB_CHANGE = 150
GUILD_REQ_LIST = 152
GUILD_REQ_INFO = 153
GUILD_APPROVE_RESVERVE = 154
REQ_GUILD_NOTICE = 169
REQ_OPEN_GUILD_SHOP = 171
REQ_BUY_GUILD_GOODS = 172
GUILD_LOG = 174
GUILD_DONATE = 175
SEARCH_GUILD = 176
RET_GUILD_CREATE = 567
RET_GUILD_JOIN = 566
RET_GUILD_LEAVE = 565
RET_GUILD_KICK = 590
RET_GUILD_REQ_LIST = 562
RET_GUILD_REQ_INFO = 563
RET_GUILD_JOB_CHANGE = 589
RET_GUILD_MEMBER_INFO = 581
RET_OPEN_GUILD_SHOP = 582
RET_BUY_GUILD_GOODS = 583
RET_GUILD_LOG = 584
RET_GUILD_DONATE = 585
RET_SEARCH_GUILD = 586
SYNC_GUILD_NEW_MEMBER = 580

# --- friends / social ------------------------------------------------------
ADD_FRIEND = 124
DEL_FRIEND = 125
ASK_CHARACTER_INFO = 142
RET_ADD_FRIEND = 533
RET_DEL_FRIEND = 535
NOTICE_ADD_FRIEND = 536
BE_DELETED_FRIEND = 537
SYN_FRIEND_INFO = 538

# --- mail ------------------------------------------------------------------
SEND_MAIL = 122
MAIL_OPERATION = 123
SEND_MAIL_BOX = 284
MAIL_UPDATE = 531
MAIL_DELETE = 532

# --- daily / sign-in -------------------------------------------------------
REQUEST_DAILY_MISSION = 121
SEND_DAILY_MISSION = 530
GRANT_DAILY_MISSION_REWARD = 612
SIGN_WEEK = 255
RET_SIGN_WEEK = 643
SIGN_30_DAY = 254
RET_SIGN_30_DAY = 642

# --- mounts / cars ---------------------------------------------------------
REQUEST_MOUNT_INFO = 235
MOUNT_EQUIP = 236
MOUNT_UNEQUIP = 237
USE_MOUNT = 238
UNUSE_MOUNT = 239
RET_MOUNT_INFO = 630
BUY_CAR_SHOP = 323
RET_BUY_CAR_SHOP = 691

# --- copy scenes / dungeons (real tag flow from the decompiled client) -----
ENTER_NEW_MAP = 106
ENTER_COPY_SCENE = 107
LEAVE_COPY_SCENE = 108
SINGLE_COPY_SCENE_NPC_DIE = 127
ASK_COPYSCENES_INFO = 145
STOP_LEAVE_COPY = 250
NEXT_WAVE = 515
COPY_SCENE_RESULT = 552
SYNC_COPYSCENES_INFO = 555
UPDATE_COPYSCENE_INFO = 561
NOTICE_COPY_SCENE_INFO = 683
NOTIFY_COPY_START_INFO = 629
COUNT_DOWN = 553
HIT_ACTION = 514
CHANGE_SCENE_LINE = 155
REQUEST_LINE_STATE = 219
UPDATE_LINE_STATE = 568
ENTER_TELEPORT_POINT = 251
GATHER_OTHER_PLAYER = 321
UPDATE_PLAYER_MAP_INFO = 324

# --- rank pvp (tianTi ladder) ----------------------------------------------
REQUEST_RANDOM_RANK_PVP_OPPONENT = 133
RET_REQUEST_RANDOM_RANK_PVP_OPPONENT = 542
REQUEST_TOP_RANK_PVP_LIST = 134
RET_REQUEST_TOP_RANK_PVP_LIST = 543
RANK_PVP_PLAYER_ATTACK = 136
RANK_PVP_OTHER_PLAYER_DIE = 137
SYN_RANK_PVP_DATA = 541
RANK_PVP_HISTORY = 546
RANK_PVP_START = 547
RANK_PVP_REWARD = 545
RANK_PVP_CREATE_ZOMBIE_USER = 544
REQUEST_RANK_PVP_DATA = 210
REQUEST_RANK_PVP_HISTORY = 211
TIANTI_REQ_WIN_COUNT_REWARDS = 157
TIANTTI_RESULT = 551
REAL_PVP_REGISTER = 138
REAL_PVP_STATE = 548

# --- tower (climb floors of npcs) -------------------------------------------
REQUEST_TOWER_COPY_INFO = 202
RET_REQUEST_TOWER_COPY_INFO = 606
ENTER_TOWER_COPY_INFO = 204
CONTINUE_TOWER_COPY = 205
GRANT_TOWER_REWARD = 203
RET_GRANT_TOWER_REWARD = 625
TOWER_RESET = 230
RET_TOWER_RESET = 626
TOWER_WIPE_OUT = 208
RET_TOWER_WIPE_OUT = 607

# --- slot machine (casino mini-game) ----------------------------------------
REQUEST_SLOT_INFO = 242
RET_SLOT_INFO = 633
SPIN_SLOT = 243
RET_SPIN_SLOT = 634
REQUEST_SLOT_SUM_REWARD = 244
RET_SLOT_SUM_REWARD = 635
REQUEST_SLOT_REWARD = 249

# --- wild boss (open-world raid boss) ----------------------------------------
REQUEST_WILD_BOSS_INFO = 200
RET_REQUEST_WILD_BOSS_INFO = 605
ENTER_WILD_BOSS = 201

# --- survive (survival assault mode) -----------------------------------------
REQUEST_SURVIVE_TOP = 245
RET_REQUEST_SURVIVE_TOP = 636
ENTER_SURVIVE_BATTLE = 246
SURVIVE_BATTLE_FINISH = 637

# --- guild battle (weekly guild-vs-guild war; GuildBattleData row 1501) ------
REQ_GUILD_BATTLE_INFO = 285
RET_GUILD_BATTLE_INFO = 662
ENTER_GUILD_BATTLE = 286
RET_ENTER_GUILD_BATTLE = 677
REQ_GUILD_BATTLE_RANK = 287
RET_GUILD_BATTLE_RANK = 663
REQ_GUILD_BATTLE_MEMBER = 288
RET_GUILD_BATTLE_MEMBER = 665
SET_GUILD_BATTLE_MEMBER = 289
RET_SET_GUILD_BATTLE_MEMBER = 666
GUILD_BATTLE_GUESS = 290
RET_GUILD_BATTLE_GUESS = 669
REQ_GUILD_BATTLE_GUESS = 292
REQ_GUILD_SCORE_INFO = 291
RET_GUILD_SCORE_INFO = 667
GUILD_BATTLE_FINISH_INFO = 668
GUILD_BATTLE_START = 670
REQ_GUILD_BATTLE_STATE = 295
RET_GUILD_BATTLE_STATE = 673
NOTICE_GUILD_BATTLE_RANK = 676

# --- misc client progress -----------------------------------------------------
TUTORIAL_FINISH = 306
UNLOCK_FUNCTION_COMPLETE = 268
START_DOWNLOAD = 269
DOWNLOAD_FINISH = 270
RE_NAME = 301
CHANGE_SHOW_TYPE = 223
IMPACT_NPC = 298

LOGIN_MAX_COUNT = 578
RETRIEVE_ACCOUNT = 660

# --- login-time info burst (client fires these right after login; each has
# a dedicated ret tag — an unanswered request leaves a UI panel waiting) -----
REQUEST_ACTIVITY_INFO = 225
RET_REQUEST_ACTIVITY_INFO = 619
REQUEST_DANCE_INFO = 227
RET_REQUEST_DANCE_INFO = 623
REQUEST_GUILD_BOSS = 195
RET_REQUEST_GUILD_BOSS = 599
REQUEST_SIGN_30_DAY_INFO = 252
RET_REQUEST_30_DAY_INFO = 640
REQUEST_SIGN_WEEK_INFO = 253
RET_REQUEST_SIGN_WEEK_INFO = 641
REQUEST_INVEST_PACK = 257
RET_REQUEST_INVEST_PACK = 645
REQUEST_DAILY_BUY = 258
RET_REQUEST_DAILY_BUY = 646
REQUEST_DAILY_ACTIVE = 261
RET_REQUEST_DAILY_ACTIVE = 649
REQUEST_RETRIEVE_INFO = 278
RET_REQUEST_RETRIEVE_INFO = 658
REQ_LEVEL_REWARD = 296
RET_LEVEL_REWARD = 674
REQUIRE_VIP_INFO = 299
RET_REQUIRE_VIP_INFO = 678
REQUEST_DOMIN_INFO = 310
RET_DOMIN_INFO = 684
REQUEST_DANCE_STATE_INFO = 313
SYNC_DANCE_STATE_INFO = 686
REQUEST_GUILD_MAP_INFO = 319
RET_REQUEST_GUILD_MAP_INFO = 689

TAG_NAMES = {
    VISITOR: "visitor",
    VERFIY: "verfiy",
    LOGIN: "login",
    FACEBOOK_LINK: "facebook_link",
    FACEBOOK_UNLINK: "facebook_unlink",
    UPDATE_GAME_SERVER: "update_game_server",
    MAP_READY: "map_ready",
    MOVE: "move",
    SKILL_USE: "skill_use",
    CHARACTER_LIST: "character_list",
    CHARACTER_CREATE: "character_create",
    CHARACTER_PICK: "character_pick",
    CHAT: "chat",
    HEART_BEAT: "heart_beat",
    LEAVE_GAME: "leave_game",
    UPDATE_CLIENT_STATE: "update_client_state",
    REFRESH_ONLINE_STATE: "refresh_online_state",
    GAME_CHECK: "game_check",
    ENTER_MAP: "enter_map",
    MAIN_PLAYER_CREATE: "main_player_create",
    AOI_ADD: "aoi_add",
    AOI_REMOVE: "aoi_remove",
    AOI_UPDATE_MOVE: "aoi_update_move",
    AOI_STOP_MOVE: "aoi_stop_move",
    ACCEPT_MISSION: "accept_mission",
    COMPLETE_MISSION: "complete_mission",
    ABANDON_MISSION: "abandon_mission",
    USE_ITEM: "use_item",
    SELL_ITEM: "sell_item",
    SYNC_MISSION: "sync_mission",
    RET_ACCEPT_MISSION: "ret_accept_mission",
    RET_COMPLETE_MISSION: "ret_complete_mission",
    RET_ABANDON_MISSION: "ret_abandon_mission",
    SET_MISSION_STATE: "set_mission_state",
    SET_MISSION_PARAM: "set_mission_param",
    UPDATE_ITEM: "update_item",
    RET_USE_ITEM: "ret_use_item",
    SYNC_BACKPACK_ITEM: "sync_backpack_item",
    SHOW_REWARD_ITEMS_TIPS: "show_reward_items_tips",
    ASK_SHOP_LIST: "ask_shop_list",
    BUY_SHOP_ITEM: "buy_shop_item",
    RET_ASK_SHOP_LIST: "ret_ask_shop_list",
    RET_BUY_SHOP_ITEM: "ret_buy_shop_item",
    EQUIP_ITEM: "equip_item",
    UNEQUIP_ITEM: "unequip_item",
    EQUIP_BADGE: "equip_badge",
    UNEQUIP_BADGE: "unequip_badge",
    EQUIP_FASHION_ITEM: "equip_fashion_item",
    UNEQUIP_FASHION_ITEM: "unequip_fashion_item",
    OPEN_ITEM_PACKAGE: "open_item_package",
    RET_OPEN_ITEM_PACKAGE: "ret_open_item_package",
    REQUEST_UPDATE_STORAGEPACK: "request_update_storagepack",
    PUT_ITEM_STORAGEPACK: "put_item_storagepack",
    TAKE_ITEM_STORAGEPACK: "take_item_storagepack",
    RET_REQUEST_UPDATE_STORAGEPACK: "ret_request_update_storagepack",
    REQUEST_RANDOM_NAME: "request_random_name",
    CHANGE_ITEM_STATE: "change_item_state",
    SYNC_BADGEPACK_ITEM: "sync_badgepack_item",
    SYNC_FASHION_BACKPACK_ITEM: "sync_fashion_backpack_item",
    SYNC_ITEM_PACK: "sync_item_pack",
    SKILL_USE: "skill_use",
    ACCEPT_DAMGE: "accept_damge",
    LOCAL_NPC_DIE: "local_npc_die",
    ATTACK_LOCAL_NPC: "attack_local_npc",
    NPC_CREATE: "npc_create",
    SHOW_DAMAGE_BOARD: "show_damage_board",
    DROP_ITEM_INFO: "drop_item_info",
    NOTICE_RELIFE_PLAYER: "notice_relife_player",
    SYNC_SKILL_INFO: "sync_skill_info",
    SKILL_LEVEL_UP: "skill_level_up",
    SYNC_COMMON_DATA: "sync_common_data",
    GUILD_CREATE: "guild_create",
    GUILD_JOIN: "guild_join",
    GUILD_LEAVE: "guild_leave",
    GUILD_KICK: "guild_kick",
    GUILD_JOB_CHANGE: "guild_job_change",
    GUILD_REQ_LIST: "guild_req_list",
    GUILD_REQ_INFO: "guild_req_info",
    GUILD_APPROVE_RESVERVE: "guild_approve_resverve",
    REQ_GUILD_NOTICE: "req_guild_notice",
    REQ_OPEN_GUILD_SHOP: "req_open_guild_shop",
    REQ_BUY_GUILD_GOODS: "req_buy_guild_goods",
    GUILD_LOG: "guild_log",
    GUILD_DONATE: "guild_donate",
    SEARCH_GUILD: "search_guild",
    RET_GUILD_CREATE: "ret_guild_create",
    RET_GUILD_JOIN: "ret_guild_join",
    RET_GUILD_LEAVE: "ret_guild_leave",
    RET_GUILD_KICK: "ret_guild_kick",
    RET_GUILD_REQ_LIST: "ret_guild_req_list",
    RET_GUILD_REQ_INFO: "ret_guild_req_info",
    RET_GUILD_JOB_CHANGE: "ret_guild_job_change",
    RET_GUILD_MEMBER_INFO: "ret_guild_member_info",
    RET_OPEN_GUILD_SHOP: "ret_open_guild_shop",
    RET_BUY_GUILD_GOODS: "ret_buy_guild_goods",
    RET_GUILD_LOG: "ret_guild_log",
    RET_GUILD_DONATE: "ret_guild_donate",
    RET_SEARCH_GUILD: "ret_search_guild",
    SYNC_GUILD_NEW_MEMBER: "sync_guild_new_member",
    ADD_FRIEND: "add_friend",
    DEL_FRIEND: "del_friend",
    ASK_CHARACTER_INFO: "ask_character_info",
    RET_ADD_FRIEND: "ret_add_friend",
    RET_DEL_FRIEND: "ret_del_friend",
    NOTICE_ADD_FRIEND: "notice_add_friend",
    BE_DELETED_FRIEND: "be_deleted_friend",
    SYN_FRIEND_INFO: "syn_friend_info",
    SEND_MAIL: "send_mail",
    MAIL_OPERATION: "mail_operation",
    SEND_MAIL_BOX: "send_mail_box",
    MAIL_UPDATE: "mail_update",
    MAIL_DELETE: "mail_delete",
    REQUEST_DAILY_MISSION: "request_daily_mission",
    SEND_DAILY_MISSION: "send_daily_mission",
    GRANT_DAILY_MISSION_REWARD: "grant_daily_mission_reward",
    SIGN_WEEK: "sign_week",
    RET_SIGN_WEEK: "ret_sign_week",
    SIGN_30_DAY: "sign_30_day",
    RET_SIGN_30_DAY: "ret_sign_30_day",
    REQUEST_MOUNT_INFO: "request_mount_info",
    MOUNT_EQUIP: "mount_equip",
    MOUNT_UNEQUIP: "mount_unequip",
    USE_MOUNT: "use_mount",
    UNUSE_MOUNT: "unuse_mount",
    RET_MOUNT_INFO: "ret_mount_info",
    BUY_CAR_SHOP: "buy_car_shop",
    RET_BUY_CAR_SHOP: "ret_buy_car_shop",
    ENTER_NEW_MAP: "enter_new_map",
    ENTER_COPY_SCENE: "enter_copy_scene",
    LEAVE_COPY_SCENE: "leave_copy_scene",
    SINGLE_COPY_SCENE_NPC_DIE: "single_copy_scene_npc_die",
    ASK_COPYSCENES_INFO: "ask_copyscenes_info",
    STOP_LEAVE_COPY: "stop_leave_copy",
    NEXT_WAVE: "next_wave",
    COPY_SCENE_RESULT: "copy_scene_result",
    SYNC_COPYSCENES_INFO: "sync_copyscenes_info",
    REQ_GUILD_BATTLE_INFO: "req_guild_battle_info",
    RET_GUILD_BATTLE_INFO: "ret_guild_battle_info",
    ENTER_GUILD_BATTLE: "enter_guild_battle",
    RET_ENTER_GUILD_BATTLE: "ret_enter_guild_battle",
    REQ_GUILD_BATTLE_RANK: "req_guild_battle_rank",
    RET_GUILD_BATTLE_RANK: "ret_guild_battle_rank",
    REQ_GUILD_BATTLE_MEMBER: "req_guild_battle_member",
    RET_GUILD_BATTLE_MEMBER: "ret_guild_battle_member",
    SET_GUILD_BATTLE_MEMBER: "set_guild_battle_member",
    RET_SET_GUILD_BATTLE_MEMBER: "ret_set_guild_battle_member",
    GUILD_BATTLE_GUESS: "guild_battle_guess",
    RET_GUILD_BATTLE_GUESS: "ret_guild_battle_guess",
    REQ_GUILD_SCORE_INFO: "req_guild_score_info",
    RET_GUILD_SCORE_INFO: "ret_guild_score_info",
    GUILD_BATTLE_START: "guild_battle_start",
    GUILD_BATTLE_FINISH_INFO: "guild_battle_finish_info",
    REQ_GUILD_BATTLE_STATE: "req_guild_battle_state",
    RET_GUILD_BATTLE_STATE: "ret_guild_battle_state",
    NOTICE_GUILD_BATTLE_RANK: "notice_guild_battle_rank",
    UPDATE_COPYSCENE_INFO: "update_copyscene_info",
    NOTICE_COPY_SCENE_INFO: "notice_copy_scene_info",
    NOTIFY_COPY_START_INFO: "notify_copy_start_info",
    COUNT_DOWN: "count_down",
    HIT_ACTION: "hit_action",
    CHANGE_SCENE_LINE: "change_scene_line",
    REQUEST_LINE_STATE: "request_line_state",
    UPDATE_LINE_STATE: "update_line_state",
    ENTER_TELEPORT_POINT: "enter_teleport_point",
    GATHER_OTHER_PLAYER: "gather_other_player",
    UPDATE_PLAYER_MAP_INFO: "update_player_map_info",
    REQUEST_RANDOM_RANK_PVP_OPPONENT: "request_random_rank_pvp_opponent",
    RET_REQUEST_RANDOM_RANK_PVP_OPPONENT: "ret_request_random_rank_pvp_opponent",
    REQUEST_TOP_RANK_PVP_LIST: "request_top_rank_pvp_list",
    RET_REQUEST_TOP_RANK_PVP_LIST: "ret_request_top_rank_pvp_list",
    RANK_PVP_PLAYER_ATTACK: "rank_pvp_player_attack",
    RANK_PVP_OTHER_PLAYER_DIE: "rank_pvp_other_player_die",
    SYN_RANK_PVP_DATA: "syn_rank_pvp_data",
    RANK_PVP_HISTORY: "rank_pvp_history",
    RANK_PVP_START: "rank_pvp_start",
    RANK_PVP_REWARD: "rank_pvp_reward",
    RANK_PVP_CREATE_ZOMBIE_USER: "rank_pvp_create_zombie_user",
    REQUEST_RANK_PVP_DATA: "request_rank_pvp_data",
    REQUEST_RANK_PVP_HISTORY: "request_rank_pvp_history",
    TIANTI_REQ_WIN_COUNT_REWARDS: "tianti_req_win_count_rewards",
    TIANTTI_RESULT: "tiantti_result",
    REAL_PVP_REGISTER: "real_pvp_register",
    REAL_PVP_STATE: "real_pvp_state",
    REQUEST_TOWER_COPY_INFO: "request_tower_copy_info",
    RET_REQUEST_TOWER_COPY_INFO: "ret_request_tower_copy_info",
    ENTER_TOWER_COPY_INFO: "enter_tower_copy_info",
    CONTINUE_TOWER_COPY: "continue_tower_copy",
    GRANT_TOWER_REWARD: "grant_tower_reward",
    RET_GRANT_TOWER_REWARD: "ret_grant_tower_reward",
    TOWER_RESET: "tower_reset",
    RET_TOWER_RESET: "ret_tower_reset",
    TOWER_WIPE_OUT: "tower_wipe_out",
    RET_TOWER_WIPE_OUT: "ret_tower_wipe_out",
    REQUEST_SLOT_INFO: "request_slot_info",
    RET_SLOT_INFO: "ret_slot_info",
    SPIN_SLOT: "spin_slot",
    RET_SPIN_SLOT: "ret_spin_slot",
    REQUEST_SLOT_SUM_REWARD: "request_slot_sum_reward",
    RET_SLOT_SUM_REWARD: "ret_slot_sum_reward",
    REQUEST_SLOT_REWARD: "request_slot_reward",
    TUTORIAL_FINISH: "tutorial_finish",
    UNLOCK_FUNCTION_COMPLETE: "unlock_function_complete",
    START_DOWNLOAD: "start_download",
    DOWNLOAD_FINISH: "download_finish",
    RE_NAME: "re_name",
    CHANGE_SHOW_TYPE: "change_show_type",
    IMPACT_NPC: "impact_npc",
    RELIFE_PLAYER: "relife_player",
    LOGIN_MAX_COUNT: "login_max_count",
    RETRIEVE_ACCOUNT: "retrieve_account",
    REQUEST_ACTIVITY_INFO: "request_activity_info",
    RET_REQUEST_ACTIVITY_INFO: "ret_request_activity_info",
    REQUEST_DANCE_INFO: "request_dance_info",
    RET_REQUEST_DANCE_INFO: "ret_request_dance_info",
    REQUEST_GUILD_BOSS: "request_guild_boss",
    RET_REQUEST_GUILD_BOSS: "ret_request_guild_boss",
    REQUEST_SIGN_30_DAY_INFO: "request_sign_30_day_info",
    RET_REQUEST_30_DAY_INFO: "ret_request_30_day_info",
    REQUEST_SIGN_WEEK_INFO: "request_sign_week_info",
    RET_REQUEST_SIGN_WEEK_INFO: "ret_request_sign_week_info",
    REQUEST_INVEST_PACK: "request_invest_pack",
    RET_REQUEST_INVEST_PACK: "ret_request_invest_pack",
    REQUEST_DAILY_BUY: "request_daily_buy",
    RET_REQUEST_DAILY_BUY: "ret_request_daily_buy",
    REQUEST_DAILY_ACTIVE: "request_daily_active",
    RET_REQUEST_DAILY_ACTIVE: "ret_request_daily_active",
    REQUEST_RETRIEVE_INFO: "request_retrieve_info",
    RET_REQUEST_RETRIEVE_INFO: "ret_request_retrieve_info",
    REQ_LEVEL_REWARD: "req_level_reward",
    RET_LEVEL_REWARD: "ret_level_reward",
    REQUIRE_VIP_INFO: "require_vip_info",
    RET_REQUIRE_VIP_INFO: "ret_require_vip_info",
    REQUEST_DOMIN_INFO: "request_domin_info",
    RET_DOMIN_INFO: "ret_domin_info",
    REQUEST_DANCE_STATE_INFO: "request_dance_state_info",
    SYNC_DANCE_STATE_INFO: "sync_dance_state_info",
    REQUEST_GUILD_MAP_INFO: "request_guild_map_info",
    RET_REQUEST_GUILD_MAP_INFO: "ret_request_guild_map_info",
}


def tag_name(tag: int) -> str:
    return TAG_NAMES.get(tag, "tag_%d" % tag)


# --- wire frame + package header -------------------------------------------

def encode_frame(tag: int, session: int, body: dict) -> bytes:
    """Build a full wire frame for a server->client message.

    Payload layout (matching the client's ProcessPack reader):
        sproto(Package{...}) || sproto(body)

    The client dispatches on the Package header:
      * HasType   -> server push, routed through NetReceiver by tag
      * HasSession-> RPC response, routed through NetSender by session id
    So responses carry ONLY the session (no type) and pushes carry ONLY
    the type (no session) — sending both makes the real client treat a
    response as a push and drop it, hanging the login flow.
    """
    if session is not None:
        pkg = {1: session}                # RPC response
    else:
        pkg = {0: tag}                    # server push
    payload = _enc.encode_object(pkg) + _enc.encode_object(body or {})
    return _enc.frame_encode(payload)


class IncomingMessage:
    """Parsed client->server frame: Package header + request body."""

    __slots__ = ("type", "session", "body")

    def __init__(self, type_tag, session, body: dict) -> None:
        self.type = type_tag
        self.session = session
        self.body = body or {}

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return "IncomingMessage(type=%s(%r) session=%r body=%r)" % (
            tag_name(self.type) if self.type is not None else "?",
            self.type,
            self.session,
            self.body,
        )


def parse_frame(payload: bytes, response: bool = False,
                assume_type: int = None) -> "IncomingMessage":
    """Split an unpacked frame payload into the Package header and body.

    `response=True` decodes the body with server->client field types
    (used when parsing frames received *from* the server, e.g. in tests).
    Response frames carry no type in the Package header, so callers that
    know which request a session belongs to pass `assume_type`.
    """
    dec = _enc.Decoder(payload)
    ptype = None
    session = None
    while (tag := dec.next_tag()) is not None:
        if tag == 0:
            ptype = dec.read_integer()
        elif tag == 1:
            session = dec.read_integer()
        else:
            dec.skip_field()
    consumed = dec.pos
    body = {}
    if consumed < len(payload):
        msg_type = ptype if ptype is not None else assume_type
        if response:
            body = decode_response(msg_type, payload[consumed:])
        else:
            body = decode_request(msg_type, payload[consumed:])
    return IncomingMessage(ptype, session, body)


# --- typed schema snippets --------------------------------------------------
# Per-message field type specs for decoding client requests.
# kinds: i=int, b=bool, s=string, o=nested object, ia=int array,
#        sa=string array, oa=object array
REQUEST_SPECS = {
    VISITOR: {},
    VERFIY: {0: "s", 1: "s", 2: "s"},
    SET_GUILD_BATTLE_MEMBER: {0: "sa"},
    LOGIN: {0: "i", 1: "s", 2: "i", 3: "s", 4: "s", 5: "i", 6: "i"},
    CHARACTER_CREATE: {0: "o"},
    CHARACTER_PICK: {0: "i"},
    ENTER_MAP: {0: "s", 1: "i", 2: "i"},
    MOVE: {0: "o", 1: "b", 2: "i", 3: "i"},
    CHAT: {0: "i", 1: "s", 2: "s", 3: "i", 4: "i", 5: "ia", 6: "sa"},
    HEART_BEAT: {0: "i", 1: "i"},
    # provisional (no decompiled SprotoType survived for these):
    ACCEPT_MISSION: {0: "i"},
    COMPLETE_MISSION: {0: "i"},
    ABANDON_MISSION: {0: "i"},
    USE_ITEM: {0: "i", 1: "i", 2: "i"},
    SELL_ITEM: {0: "i", 1: "i"},
    ASK_SHOP_LIST: {0: "i"},
    BUY_SHOP_ITEM: {0: "i", 1: "i"},
    # inventory / equipment (provisional)
    EQUIP_ITEM: {0: "i"},          # item instance id
    UNEQUIP_ITEM: {0: "i"},        # equip slot
    EQUIP_BADGE: {0: "i"},
    UNEQUIP_BADGE: {0: "i"},
    EQUIP_FASHION_ITEM: {0: "i"},
    UNEQUIP_FASHION_ITEM: {0: "i"},
    OPEN_ITEM_PACKAGE: {0: "i"},   # item id of the package
    PUT_ITEM_STORAGEPACK: {0: "i", 1: "i"},   # item id, count
    TAKE_ITEM_STORAGEPACK: {0: "i", 1: "i"},  # item id, count
    REQUEST_RANDOM_NAME: {0: "i"},  # sex
    CHANGE_ITEM_STATE: {0: "i", 1: "i"},
    SKILL_USE: {0: "i", 1: "i"},   # skill id, target id
    ACCEPT_DAMGE: {0: "oa"},   # damges: object array of acceptdamge
    LOCAL_NPC_DIE: {0: "i"},       # npc id
    ATTACK_LOCAL_NPC: {0: "i", 1: "i"},      # npc id, skill id
    RELIFE_PLAYER: {},
    # guilds (provisional)
    GUILD_CREATE: {0: "s"},                        # name
    GUILD_JOIN: {0: "i"},                          # guild id
    GUILD_LEAVE: {},
    GUILD_KICK: {0: "s"},                          # member name
    GUILD_JOB_CHANGE: {0: "s", 1: "i"},           # member name, job
    GUILD_APPROVE_RESVERVE: {0: "s", 1: "i"},     # name, approve(1)/deny(0)
    REQ_GUILD_NOTICE: {},
    GUILD_DONATE: {0: "i"},                        # gold amount
    SEARCH_GUILD: {0: "s"},                        # name substring
    # friends (provisional)
    ADD_FRIEND: {0: "s"},          # character name
    DEL_FRIEND: {0: "s"},
    ASK_CHARACTER_INFO: {0: "s"},
    # mail (provisional)
    SEND_MAIL: {0: "s", 1: "s", 2: "s"},   # to, title, body
    MAIL_OPERATION: {0: "i", 1: "i"},       # mail id, op (0 read, 1 collect, 2 delete)
    # daily / sign-in
    REQUEST_DAILY_MISSION: {},
    SIGN_WEEK: {},
    SIGN_30_DAY: {},
    # mounts
    REQUEST_MOUNT_INFO: {},
    MOUNT_EQUIP: {0: "i"},
    MOUNT_UNEQUIP: {},
    USE_MOUNT: {0: "i"},
    UNUSE_MOUNT: {},
    BUY_CAR_SHOP: {0: "i"},        # car goods id
    # copy scenes / dungeons (provisional)
    ENTER_COPY_SCENE: {0: "i"},                 # copy scene id
    LEAVE_COPY_SCENE: {},
    SINGLE_COPY_SCENE_NPC_DIE: {0: "i"},        # npc id
    ASK_COPYSCENES_INFO: {},
    ENTER_NEW_MAP: {0: "s"},                    # map id
    CHANGE_SCENE_LINE: {0: "i"},
    REQUEST_LINE_STATE: {0: "s"},
    ENTER_TELEPORT_POINT: {0: "i"},
    GATHER_OTHER_PLAYER: {0: "s"},
    UPDATE_PLAYER_MAP_INFO: {0: "s", 1: "i"},
    # rank pvp (provisional)
    REQUEST_RANDOM_RANK_PVP_OPPONENT: {},
    RANK_PVP_PLAYER_ATTACK: {0: "i", 1: "i"},   # damage, opponent hp
    RANK_PVP_OTHER_PLAYER_DIE: {},
    REQUEST_RANK_PVP_DATA: {},
    REQUEST_RANK_PVP_HISTORY: {},
    TIANTI_REQ_WIN_COUNT_REWARDS: {},
    # tower (provisional)
    REQUEST_TOWER_COPY_INFO: {},
    ENTER_TOWER_COPY_INFO: {},
    CONTINUE_TOWER_COPY: {},
    GRANT_TOWER_REWARD: {},
    TOWER_RESET: {},
    TOWER_WIPE_OUT: {},
    # slot machine
    REQUEST_SLOT_INFO: {},
    SPIN_SLOT: {},
    REQUEST_SLOT_SUM_REWARD: {},
    REQUEST_SLOT_REWARD: {0: "i"},
    # misc
    TUTORIAL_FINISH: {},
    UNLOCK_FUNCTION_COMPLETE: {0: "i"},
    RE_NAME: {0: "s"},
    CHANGE_SHOW_TYPE: {0: "i"},
    IMPACT_NPC: {0: "i"},
    START_DOWNLOAD: {},
    DOWNLOAD_FINISH: {},
}

# Server->client response field specs (used by tests / client-side parsing).
RESPONSE_SPECS = {
    VISITOR: {0: "s", 1: "s", 2: "i"},
    VERFIY: {0: "i", 1: "i", 2: "oa", 3: "s", 4: "i", 5: "s", 6: "s", 7: "i"},
    LOGIN: {0: "i", 1: "s", 2: "s", 3: "i"},
    UPDATE_GAME_SERVER: {2: "oa"},
    CHARACTER_LIST: {0: "oa"},
    CHARACTER_CREATE: {0: "o", 1: "i"},
    CHARACTER_PICK: {0: "i"},
    MAP_READY: {},
    # enter_map response (legacy request path): {character(0)}; the PUSH
    # variant (no session) is {mapInfoId(0), line_index(1), line_count(2)}
    # and is decoded by the push path in tests.
    ENTER_MAP: {0: "o"},
    HEART_BEAT: {0: "i", 1: "i"},
    # provisional (see server/economy.py for the field layout notes)
    ACCEPT_MISSION: {0: "i"},
    COMPLETE_MISSION: {0: "i"},
    ABANDON_MISSION: {0: "i"},
    RET_ACCEPT_MISSION: {0: "i", 1: "i"},
    RET_COMPLETE_MISSION: {0: "i", 1: "i"},
    RET_ABANDON_MISSION: {0: "i", 1: "i"},
    SYNC_MISSION: {0: "oa"},
    RET_USE_ITEM: {0: "i", 1: "i"},
    UPDATE_ITEM: {0: "i", 1: "i", 2: "i"},
    SYNC_BACKPACK_ITEM: {0: "oa"},
    RET_ASK_SHOP_LIST: {0: "i", 1: "oa"},
    RET_BUY_SHOP_ITEM: {0: "i", 1: "i"},
    EQUIP_ITEM: {0: "i"},
    UNEQUIP_ITEM: {0: "i"},
    EQUIP_BADGE: {0: "i"},
    UNEQUIP_BADGE: {0: "i"},
    EQUIP_FASHION_ITEM: {0: "i"},
    UNEQUIP_FASHION_ITEM: {0: "i"},
    RET_OPEN_ITEM_PACKAGE: {0: "i", 1: "oa"},
    RET_REQUEST_UPDATE_STORAGEPACK: {0: "oa"},
    REQUEST_RANDOM_NAME: {0: "s"},
    SYNC_BADGEPACK_ITEM: {0: "oa"},
    SYNC_FASHION_BACKPACK_ITEM: {0: "oa"},
    SYNC_ITEM_PACK: {0: "oa"},
    RET_SKILL_USE: {0: "i", 1: "i"},
    # sync_skill_info: the client reads tag 0 as map<string, skill_info> —
    # an OBJECT ARRAY of skill_info blobs (key taken from v.skillId)
    SYNC_SKILL_INFO: {0: "oa"},
    SHOW_DAMAGE_BOARD: {0: "oa"},  # damges: object array of acceptdamge
    DROP_ITEM_INFO: {0: "i", 1: "i", 2: "i", 3: "i", 4: "o", 7: "i"},
    AOI_UPDATE_ATTRIBUTE: {0: "o"},  # character_aoi_attribute blob
    SYNC_COMMON_DATA: {0: "i", 1: "i", 2: "i", 3: "i"},
    RET_GUILD_CREATE: {0: "i", 1: "i"},
    RET_GUILD_JOIN: {0: "i", 1: "i"},
    RET_GUILD_LEAVE: {0: "i"},
    RET_GUILD_KICK: {0: "i"},
    RET_GUILD_REQ_LIST: {0: "oa"},
    RET_GUILD_REQ_INFO: {0: "o"},
    RET_GUILD_JOB_CHANGE: {0: "i"},
    RET_GUILD_MEMBER_INFO: {0: "o"},
    RET_OPEN_GUILD_SHOP: {0: "i", 1: "oa"},
    RET_BUY_GUILD_GOODS: {0: "i"},
    RET_GUILD_LOG: {0: "oa"},
    RET_GUILD_DONATE: {0: "i", 1: "i"},
    RET_SEARCH_GUILD: {0: "oa"},
    SYNC_GUILD_NEW_MEMBER: {0: "s"},
    # ret_add_friend / notice_add_friend: ONE friend_info object at tag 0
    RET_ADD_FRIEND: {0: "o"},
    NOTICE_ADD_FRIEND: {0: "o"},
    # be_deleted_friend / ret_del_friend: characterId integer at tag 0
    RET_DEL_FRIEND: {0: "i"},
    BE_DELETED_FRIEND: {0: "i"},
    # syn_friend_info: ONE friend_info object at tag 0, not an array
    SYN_FRIEND_INFO: {0: "o"},
    MAIL_UPDATE: {0: "o"},
    SEND_MAIL_BOX: {0: "oa"},
    MAIL_DELETE: {0: "i"},
    SEND_DAILY_MISSION: {0: "oa"},
    RET_SIGN_WEEK: {0: "i", 1: "i"},
    RET_SIGN_30_DAY: {0: "i", 1: "i"},
    RET_MOUNT_INFO: {0: "oa"},
    RET_BUY_CAR_SHOP: {0: "i"},
    ENTER_COPY_SCENE: {0: "i"},
    COPY_SCENE_RESULT: {0: "i", 1: "i", 2: "i"},
    SYNC_COPYSCENES_INFO: {0: "oa"},
    UPDATE_COPYSCENE_INFO: {0: "i", 1: "i"},
    NEXT_WAVE: {0: "i"},
    COUNT_DOWN: {0: "i"},
    RET_REQUEST_RANDOM_RANK_PVP_OPPONENT: {0: "s", 1: "i", 2: "i"},
    RET_REQUEST_TOP_RANK_PVP_LIST: {0: "oa"},
    SYN_RANK_PVP_DATA: {0: "i", 1: "i", 2: "i"},
    RANK_PVP_START: {0: "s", 1: "i", 2: "i"},
    RANK_PVP_REWARD: {0: "i", 1: "i"},
    TIANTTI_RESULT: {0: "i", 1: "i", 2: "i"},
    RET_REQUEST_TOWER_COPY_INFO: {0: "i", 1: "i"},
    RET_GRANT_TOWER_REWARD: {0: "i", 1: "i"},
    RET_TOWER_RESET: {0: "i"},
    RET_TOWER_WIPE_OUT: {0: "i"},
    RET_SLOT_INFO: {0: "i", 1: "i"},
    RET_SPIN_SLOT: {0: "ia", 1: "i"},
    RET_SLOT_SUM_REWARD: {0: "i"},
    UPDATE_LINE_STATE: {0: "ia"},
    SYNC_COPYSCENES_INFO: {0: "oa"},
    ENTER_NEW_MAP: {0: "i"},
    CHANGE_SCENE_LINE: {0: "i"},
    ENTER_TELEPORT_POINT: {0: "i"},
    UPDATE_PLAYER_MAP_INFO: {0: "s", 1: "i"},
    RET_REQUEST_WILD_BOSS_INFO: {0: "s", 1: "i", 2: "i", 3: "i", 4: "i"},
    RET_REQUEST_SURVIVE_TOP: {0: "oa"},
    SURVIVE_BATTLE_FINISH: {0: "i", 1: "i", 2: "i"},
    RET_GUILD_BATTLE_INFO: {0: "i", 1: "i", 2: "i", 3: "i", 4: "oa"},
    RET_ENTER_GUILD_BATTLE: {0: "i"},
    RET_GUILD_BATTLE_RANK: {0: "oa"},
    RET_GUILD_BATTLE_MEMBER: {0: "oa"},
    RET_SET_GUILD_BATTLE_MEMBER: {0: "i"},
    RET_GUILD_BATTLE_GUESS: {0: "s", 1: "i"},
    RET_GUILD_SCORE_INFO: {0: "i", 1: "i"},
    GUILD_BATTLE_START: {0: "i"},
    RET_GUILD_BATTLE_STATE: {0: "i"},
    # login-time info burst — list/object payloads matching the client's
    # SprotoType decode switch order (see handlers.h_info_burst)
    RET_REQUEST_ACTIVITY_INFO: {0: "oa"},
    RET_REQUEST_DANCE_INFO: {0: "oa"},
    RET_REQUEST_GUILD_BOSS: {0: "i", 1: "i"},
    RET_REQUEST_30_DAY_INFO: {0: "i"},
    RET_REQUEST_SIGN_WEEK_INFO: {0: "i"},
    RET_REQUEST_INVEST_PACK: {0: "oa"},
    RET_REQUEST_DAILY_BUY: {0: "oa"},
    RET_REQUEST_DAILY_ACTIVE: {0: "oa"},
    RET_REQUEST_RETRIEVE_INFO: {0: "oa"},
    RET_LEVEL_REWARD: {0: "oa"},
    RET_REQUIRE_VIP_INFO: {0: "i", 1: "i"},
    RET_DOMIN_INFO: {0: "i"},
    SYNC_DANCE_STATE_INFO: {0: "oa"},
    RET_REQUEST_GUILD_MAP_INFO: {0: "oa"},
}


# Requests whose typed response body is registered under the ret_* tag.
RESPONSE_ALIASES = {
    UPDATE_GAME_SERVER: UPDATE_GAME_SERVER,
    ACCEPT_MISSION: RET_ACCEPT_MISSION,
    COMPLETE_MISSION: RET_COMPLETE_MISSION,
    ABANDON_MISSION: RET_ABANDON_MISSION,
    USE_ITEM: RET_USE_ITEM,
    ASK_SHOP_LIST: RET_ASK_SHOP_LIST,
    BUY_SHOP_ITEM: RET_BUY_SHOP_ITEM,
    OPEN_ITEM_PACKAGE: RET_OPEN_ITEM_PACKAGE,
    REQUEST_UPDATE_STORAGEPACK: RET_REQUEST_UPDATE_STORAGEPACK,
    GUILD_CREATE: RET_GUILD_CREATE,
    GUILD_JOIN: RET_GUILD_JOIN,
    GUILD_LEAVE: RET_GUILD_LEAVE,
    GUILD_KICK: RET_GUILD_KICK,
    GUILD_JOB_CHANGE: RET_GUILD_JOB_CHANGE,
    GUILD_DONATE: RET_GUILD_DONATE,
    SEARCH_GUILD: RET_SEARCH_GUILD,
    ADD_FRIEND: RET_ADD_FRIEND,
    DEL_FRIEND: RET_DEL_FRIEND,
    SIGN_WEEK: RET_SIGN_WEEK,
    SIGN_30_DAY: RET_SIGN_30_DAY,
    REQUEST_MOUNT_INFO: RET_MOUNT_INFO,
    BUY_CAR_SHOP: RET_BUY_CAR_SHOP,
    REQUEST_RANK_PVP_DATA: SYN_RANK_PVP_DATA,
    REQUEST_RANDOM_RANK_PVP_OPPONENT: RET_REQUEST_RANDOM_RANK_PVP_OPPONENT,
    REQUEST_TOP_RANK_PVP_LIST: RET_REQUEST_TOP_RANK_PVP_LIST,
    TIANTI_REQ_WIN_COUNT_REWARDS: TIANTTI_RESULT,
    REQUEST_TOWER_COPY_INFO: RET_REQUEST_TOWER_COPY_INFO,
    ENTER_TOWER_COPY_INFO: RET_REQUEST_TOWER_COPY_INFO,
    GRANT_TOWER_REWARD: RET_GRANT_TOWER_REWARD,
    TOWER_RESET: RET_TOWER_RESET,
    TOWER_WIPE_OUT: RET_TOWER_WIPE_OUT,
    REQUEST_SLOT_INFO: RET_SLOT_INFO,
    SPIN_SLOT: RET_SPIN_SLOT,
    REQUEST_SLOT_SUM_REWARD: RET_SLOT_SUM_REWARD,
    REQUEST_LINE_STATE: UPDATE_LINE_STATE,
    ASK_COPYSCENES_INFO: SYNC_COPYSCENES_INFO,
    REQUEST_WILD_BOSS_INFO: RET_REQUEST_WILD_BOSS_INFO,
    REQUEST_SURVIVE_TOP: RET_REQUEST_SURVIVE_TOP,
    ENTER_NEW_MAP: ENTER_NEW_MAP,
    LEAVE_COPY_SCENE: LEAVE_COPY_SCENE,
    CHANGE_SCENE_LINE: CHANGE_SCENE_LINE,
    ENTER_TELEPORT_POINT: ENTER_TELEPORT_POINT,
    REQ_GUILD_BATTLE_INFO: RET_GUILD_BATTLE_INFO,
    REQ_GUILD_BATTLE_MEMBER: RET_GUILD_BATTLE_MEMBER,
    SET_GUILD_BATTLE_MEMBER: RET_SET_GUILD_BATTLE_MEMBER,
    GUILD_BATTLE_GUESS: RET_GUILD_BATTLE_GUESS,
    REQ_GUILD_BATTLE_GUESS: RET_GUILD_BATTLE_GUESS,
    REQ_GUILD_BATTLE_RANK: RET_GUILD_BATTLE_RANK,
    REQ_GUILD_SCORE_INFO: RET_GUILD_SCORE_INFO,
    REQ_GUILD_BATTLE_STATE: RET_GUILD_BATTLE_STATE,
    ENTER_GUILD_BATTLE: RET_ENTER_GUILD_BATTLE,
    REQUEST_ACTIVITY_INFO: RET_REQUEST_ACTIVITY_INFO,
    REQUEST_DANCE_INFO: RET_REQUEST_DANCE_INFO,
    REQUEST_GUILD_BOSS: RET_REQUEST_GUILD_BOSS,
    REQUEST_SIGN_30_DAY_INFO: RET_REQUEST_30_DAY_INFO,
    REQUEST_SIGN_WEEK_INFO: RET_REQUEST_SIGN_WEEK_INFO,
    REQUEST_INVEST_PACK: RET_REQUEST_INVEST_PACK,
    REQUEST_DAILY_BUY: RET_REQUEST_DAILY_BUY,
    REQUEST_DAILY_ACTIVE: RET_REQUEST_DAILY_ACTIVE,
    REQUEST_RETRIEVE_INFO: RET_REQUEST_RETRIEVE_INFO,
    REQ_LEVEL_REWARD: RET_LEVEL_REWARD,
    REQUIRE_VIP_INFO: RET_REQUIRE_VIP_INFO,
    REQUEST_DOMIN_INFO: RET_DOMIN_INFO,
    REQUEST_DANCE_STATE_INFO: SYNC_DANCE_STATE_INFO,
    REQUEST_GUILD_MAP_INFO: RET_REQUEST_GUILD_MAP_INFO,
}


def decode_request(msg_type: int, data: bytes) -> dict:
    spec = REQUEST_SPECS.get(msg_type, {})
    return _enc.decode_typed(data, spec)


def decode_response(msg_type: int, data: bytes) -> dict:
    spec = RESPONSE_SPECS.get(RESPONSE_ALIASES.get(msg_type, msg_type), {})
    return _enc.decode_typed(data, spec)


# position {x,y,z,o} — all integers
def encode_position(x: int, y: int, z: int, o: int) -> bytes:
    return _enc.encode_object({0: x, 1: y, 2: z, 3: o})


def decode_position(data: bytes) -> dict:
    d = _enc.decode_typed(data, {0: "i", 1: "i", 2: "i", 3: "i"})
    return {
        "x": d.get(0, 0),
        "y": d.get(1, 0),
        "z": d.get(2, 0),
        "o": d.get(3, 0),
    }


# movement {pos, pos2} — position objects
def encode_movement(pos: dict, pos2: dict = None) -> bytes:
    fields = {0: encode_position(**pos)}
    if pos2:
        fields[1] = encode_position(**pos2)
    return _enc.encode_object(fields)


# character_overview: {id(0), name(1), level(2), sex(3), online(4), ...}
def encode_character_overview(char_id: int, name: str, level: int = 1,
                              sex: int = 0) -> bytes:
    return _enc.encode_object({
        0: char_id,
        1: name,
        2: level,
        3: sex,
    })


# game_server object (tags per SprotoType.game_server)
def encode_game_server(server_id, name, ip, port, state=0,
                       player_state=0, area=0, rank=1, tz=8,
                       weight=0, new_server=0) -> bytes:
    return _enc.encode_object({
        0: server_id,
        1: name,
        2: ip,
        3: port,
        4: state,
        5: player_state,
        6: area,
        7: rank,
        8: tz,
        9: weight,
        10: new_server,
    })


# --- mission / shop / item wire objects (provisional schemas) --------------

def encode_mission_state(mission_id: int, progress: int, state: int) -> bytes:
    """sync_mission element: {mission_id(0), progress(1), state(2)}.

    state: 0 = active, 1 = complete (reward claimable), 2 = finished/claimed.
    """
    return _enc.encode_object({0: mission_id, 1: progress, 2: state})


def encode_item_stack(item_id: int, count: int) -> bytes:
    """Backpack element: {item_id(0), count(1)}."""
    return _enc.encode_object({0: item_id, 1: count})


def encode_acceptdamge(obj_id: int, damage: int, skill_id: str = "1",
                       cri: bool = False) -> bytes:
    """SprotoType.acceptdamge element (show_damage_board / accept_damge):
    {id(0) int, damage(1) int, skillId(2) STRING, effinfoId(3) STRING,
    cri(4) bool, parm..(5-8)}. The client's handlers read request.damges as
    an OBJECT ARRAY at tag 0 — sending bare ints there decodes them as
    garbage objects and crashes the damage-board loop.
    """
    return _enc.encode_object({
        0: obj_id, 1: damage, 2: str(skill_id), 4: 1 if cri else 0,
    })


def encode_damage_board(entries: list) -> bytes:
    """Object-array element blob for show_damage_board / accept_damge.
    The push body is SprotoType.show_damage_board.request whose tag 0
    (damges) is an OBJECT ARRAY of acceptdamge elements — i.e. the body
    dict must be {0: <array blob>} and the array blob is just the
    concatenated (u32 len + object stream) elements, exactly like
    sproto.encode_object_array. The client's show_damage_board_handler
    reads request.damges (tag 0) and iterates the acceptdamge objects.
    """
    return _enc.encode_object_array(entries)


def encode_drop_item_info(server_id: int, item_id: int, count: int,
                          pos_x: int, pos_z: int) -> dict:
    """SprotoType.drop_item_info push BODY (flat, not wrapped in {0: blob}):
    {serverId(0) int, pos_x(1) int, pos_z(2) int, type(3) int,
    item(4): SprotoType.item object, ownServerId(7) int}. The client's
    drop_item_info.request class decodes these tags directly off the push
    body — wrapping the object at tag 0 makes the client read a
    length-prefixed field as serverId ("read invalid integer size"), which
    kills the packet pump. SprotoType.item: {itemId(0) STRING,
    itemCount(1), quality(3), id(4) STRING, count2(5)} — itemId must be the
    REAL ItemData row id as a string, or GetItemDataByID returns null and
    the client crashes (drop_item_info_handler dereferences
    itemDataByID.Type).
    """
    item = _enc.encode_object({
        0: str(item_id), 1: count,
    })
    return {
        0: server_id,
        1: int(pos_x * 100),
        2: int(pos_z * 100),
        3: 0,                 # type
        4: item,
        7: server_id,         # ownServerId
    }


def encode_shop_good(goods_id: int, item_id: int, count: int,
                     currency: int, price: int) -> bytes:
    """ret_ask_shop_list element: {goods_id(0), item_id(1), count(2),
    currency(3), price(4)}."""
    return _enc.encode_object({
        0: goods_id, 1: item_id, 2: count, 3: currency, 4: price,
    })


def encode_reward_tips(items: dict, gold: int = 0, diamond: int = 0) -> bytes:
    """show_reward_items_tips body: {gold(0), diamond(1), items(2, object array
    of encode_item_stack)} — the client shows a reward popup for this."""
    stacks = [_enc.encode_object({0: iid, 1: cnt}) for iid, cnt in items.items()]
    return _enc.encode_object({
        0: gold,
        1: diamond,
        2: _enc.encode_object_array(stacks),
    })


# character_aoi_move {id(0), movement(1), walk(2)}
def encode_character_aoi_move(char_id: int, movement: bytes,
                              walk: bool = True) -> bytes:
    return _enc.encode_object({0: char_id, 1: movement, 2: walk})


# --- npc / combat wire objects ----------------------------------------------

def encode_npc(npc_id: int, kind: int, level: int, hp: int, max_hp: int,
               pos: dict) -> bytes:
    """SprotoType.npc_attribute — the REAL client schema (decode() switch).

    npc_create_handler -> ObjInitNpcData.InitData(npc_attribute):
        id(0) int          -> mServerID
        npcdataid(1) STRING-> DataManager.GetNpcDataByID(...) — MUST be a
                             real NpcData row id from the APK's Data.bundle
                             (e.g. "21131" RepairMan Lv.1), otherwise the
                             lookup returns null and the client crashes,
                             freezing the loading window at 90%.
        hp(2) max_hp(3) atk(4) def(5) hit(6) eva(7) cri(8) exd(9) exr(10)
        res(11) crd(12) crr(13) defa(14) — plain integers
        x(15) z(16) o(17)  — position as SEPARATE integers (x*100, z*100,
                             o*100 in client units), NOT a nested object.
        level(18) anti_stun(19) anti_knock_down(20) player_name(21 STRING)
        guildId(22) teamid(23) dgea(24) resa(25) hita(26) cria(27)

    NOTE: the client does NOT send a max_hp in npc_attribute — it takes
    MaxHP from the NpcData row; we still send it at tag 3 (max_hp) since
    InitData reads npc_attribute.max_hp directly.
    """
    from . import economy
    kind_def = economy.NPC_KINDS.get(kind, {})
    npcdataid = kind_def.get("npcdataid", "21131")
    atk = kind_def.get("atk", 20)
    return _enc.encode_object({
        0: npc_id,
        1: npcdataid,          # STRING — read_string on the client
        2: hp,
        3: max_hp,
        4: atk,
        5: kind_def.get("def", 100),
        6: 10,                 # hit
        7: 5,                  # eva
        8: 0,                  # cri
        9: 0, 10: 0,           # exd / exr
        11: 0, 12: 0, 13: 0,   # res / crd / crr
        14: 0,                 # defa
        15: int(pos.get("x", 0) * 100),
        16: int(pos.get("z", 0) * 100),
        17: int(pos.get("o", 0) * 100),
        18: level,
        19: 0, 20: 0,          # anti_stun / anti_knock_down
        21: kind_def.get("name", "NPC"),  # player_name STRING
    })


def encode_aoi_update_attribute(char_id: int, hp: int, exp: int,
                                level: int, max_hp: int, gold: int = 0,
                                diamond: int = 0) -> bytes:
    """SprotoType.aoi_update_attribute.request {character(0)} where character
    is a character_aoi_attribute blob: id(0) attribute_other(1) attribute(2)
    attribute_all(3) visual(4) property(5). aoi_update_attribute_handler on
    the client applies MaxHP/HP/level/exp (UpdateExp) and money for the main
    player — this is the real post-kill attribute sync (NOT sync_common_data,
    whose tag 0 is serverTime on the client!).
    """
    attribute = _enc.encode_object({
        0: max_hp,            # max_hp
        1: exp,               # exp
        2: 20,                # atk
        3: 100,               # def
    })
    attribute_other = _enc.encode_object({
        0: hp, 1: exp, 2: level,
    })
    character = _enc.encode_object({
        0: char_id,
        1: attribute_other,
        2: attribute,
        5: _enc.encode_object({13: gold, 14: diamond}),  # property money1/2
    })
    return _enc.encode_object({0: character})


def encode_npc_create(npc) -> bytes:
    """npc_create push body: {npc(0)}."""
    return _enc.encode_object({0: npc})


def encode_skill_info(skill_id: int, level: int) -> bytes:
    """sync_skill_info / character.skills element (SprotoType.skill_info).

    The client decodes skillId as a STRING (read_string) and uses it as the
    dictionary key; it must be a string like "101", not an integer — an int
    here makes read_string hit the end of the stream and the push dies with
    "Exception: invalid pos" on the client.
    """
    return _enc.encode_object({0: str(skill_id), 1: level})


def encode_friend_entry(char_id: int, name: str, level: int = 1,
                        online: bool = False) -> bytes:
    """friend_info object (SprotoType.friend_info).

    Fields: characterId(0), friendId(1), name(2), level(3), profession(4),
    combValue(5), state(6), timeInfo(7), friendType(8). The client's friend
    handlers (syn_friend_info / ret_add_friend / notice_add_friend) add ONE
    friend_info per push — send a single object, never an array.
    """
    return _enc.encode_object({
        0: char_id, 1: char_id, 2: name, 3: level, 4: 0,
        6: 1 if online else 0,
    })


def encode_mail(mail_id: int, sender: str, title: str, body: str,
                gold: int = 0, diamond: int = 0, collected: int = 0) -> bytes:
    """mail element: {mail_id(0), sender(1), title(2), body(3), gold(4),
    diamond(5), collected(6)}."""
    return _enc.encode_object({
        0: mail_id, 1: sender, 2: title, 3: body,
        4: gold, 5: diamond, 6: collected,
    })


def encode_guild_info(guild_id: int, name: str, leader: str,
                      members: int = 1, notice: str = "", gold: int = 0,
                      level: int = 1) -> bytes:
    """Guild object: {guild_id(0), name(1), leader(2), members(3), notice(4),
    gold(5), level(6)}."""
    return _enc.encode_object({
        0: guild_id, 1: name, 2: leader, 3: members, 4: notice,
        5: gold, 6: level,
    })


def encode_guild_member(name: str, job: int, level: int = 1,
                        online: bool = False) -> bytes:
    """Guild member: {name(0), job(1), level(2), online(3)}
    job: 0 leader, 1 officer, 2 member."""
    return _enc.encode_object({
        0: name, 1: job, 2: level, 3: 1 if online else 0,
    })


def encode_mount_info(car_id: int, equipped: bool = False,
                      in_use: bool = False) -> bytes:
    """ret_mount_info element: {car_id(0), equipped(1), in_use(2)}."""
    return _enc.encode_object({
        0: car_id, 1: 1 if equipped else 0, 2: 1 if in_use else 0,
    })
