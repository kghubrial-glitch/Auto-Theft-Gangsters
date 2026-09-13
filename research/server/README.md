# Revival Server

A working, protocol-compatible replacement backend for **Auto Theft Gangsters
v1.19** (`com.doodlemobile.vicecity`), implemented in Python 3.10+ with no
third-party dependencies. Reverse-engineered from the client's
`Assembly-CSharp.dll` (see `docs/protocol.md` for the full protocol spec).

## Quick start

```bash
python3 -m server.main
```

By default the server now runs in **single-port mode** on `0.0.0.0:13103`:
one listener serves both the login-gate protocol and the game protocol. The
client connects its login gate to the patched host/port and then hops to
whatever `game_server.serverPort` the gate advertises — the gate advertises
the same single port, so only one port needs to be open. The original
two-port layout is still available with `ATG_SINGLE_PORT=0`:

| Endpoint   | Port | Purpose                                   |
|------------|------|-------------------------------------------|
| Single port| 13103| gate + game on one listener (default)     |
| Login gate | 9777 | `update_game_server`, `visitor`, `verfiy` |
| Game server| 9555 | `login`, characters, world/AOI, chat      |

## Pointing the APK at the server

The client hardcodes `gangsterlogin.galaxyaura.com:9777`. Options:

1. **Repack the APK** — edit the server host string in
   `assets/bin/Data/…` / smali constants (`gangsterlogin.galaxyaura.com`)
   to your server IP, re-sign, install.
2. **DNS override** — on a rooted device or via ADB, redirect
   `gangsterlogin.galaxyaura.com` to your server IP (hosts file or VPN DNS),
   keeping port 9777.
3. **Local VPN app** — e.g. an on-device redirector mapping the original
   host:port to your server.

The game server address is returned by the gate in
`update_game_server`/`verfiy` responses, so only the login host needs
redirecting. The advertised game-server IP can be set with
`ATG_ADVERTISE_IP` (defaults to the machine's primary address).

## Configuration (environment variables)

| Variable          | Default        | Meaning                          |
|-------------------|----------------|----------------------------------|
| `ATG_SINGLE_PORT` | `1`            | `1` = one listener, `0` = gate+game |
| `ATG_PORT`        | `13103`        | Single-mode listener port        |
| `ATG_GATE_PORT`   | `9777`         | Login gate port (two-port mode)  |
| `ATG_GAME_PORT`   | `9555`         | Game server port (two-port mode) |
| `ATG_ADVERTISE_PORT`| listen port  | Port advertised in the server list |
| `ATG_BIND_HOST`   | `0.0.0.0`      | Listen address                   |
| `ATG_DB_PATH`     | `atg_server.db`| SQLite database file             |
| `ATG_SERVER_NAME` | `Revival-1`    | Server name shown in server list |
| `ATG_ADVERTISE_IP`| (local IP)     | IP advertised in server list     |

## Implemented protocol

Tags handled (see `server/protocol.py`):

- **Gate**: `update_game_server` (7), `visitor` (2), `verfiy` (3)
- **Game**: `login` (4), `character_list` (103), `character_create` (104),
  `character_pick` (105), `map_ready` (100), `enter_map` (503),
  `move` (101, broadcast as `aoi_update_move` 507 / `aoi_add` 505 /
  `aoi_remove` 506), `chat` (120, echoed as `ret_chat` 528),
  `heart_beat` (218), `leave_game` (234), plus no-op acknowledgements for
  `refresh_online_state`, `update_client_state`, `game_check` and
  `retrieve_account` (account recovery is not supported).
- **Missions**: `accept_mission` (112) / `ret_accept_mission` (520),
  `complete_mission` (113) / `ret_complete_mission` (521),
  `abandon_mission` (114) / `ret_abandon_mission` (522), with state pushed
  via `sync_mission` (519) and rewards via `show_reward_items_tips` (638).
  Daily missions via `request_daily_mission` (121) / `send_daily_mission` (530).
- **Shop**: `ask_shop_list` (143) / `ret_ask_shop_list` (554),
  `buy_shop_item` (144) / `ret_buy_shop_item` (652), plus car shop via
  `buy_car_shop` (323) / `ret_buy_car_shop` (691).
- **Items**: `use_item` (115) / `ret_use_item` (526), `sell_item` (129),
  backpack sync via `sync_backpack_item` (592) and `update_item` (525).
- **Equipment**: `equip_item` (116), `unequip_item` (117), `equip_badge` (197),
  `unequip_badge` (198), `equip_fashion_item` (221),
  `unequip_fashion_item` (222), `equip_appraise` (303), badge/fashion sync
  pushes (604 / 616), equip-slot based weapon/armor/badge/fashion with
  combat stat effects. `gameitem.appraise` (field 8) carries the item's
  identified state: 0 = new/unidentified (Appraise page, blocked from
  direct equipping), 1 = identified/usable. Newly acquired equipment rolls
  an unidentified instance; `equip_appraise` (303) charges
  `economy.APPRAISE_PRICE` gold and unlocks it. The EQUIPPACK map
  (`character.equip` tag 9 and the post-equip resync) only ever carries the
  six real armor/weapon slots — badge/fashion sync through their own
  containers so no wrong ModelId hides a body part.
- **Storage + packages**: `request_update_storagepack` (139) /
  `ret_request_update_storagepack` (550), `put_item_storagepack` (140),
  `take_item_storagepack` (141), `open_item_package` (224) /
  `ret_open_item_package` (617), `change_item_state` (240),
  `request_random_name` (118).
- **NPCs + combat**: NPCs spawn per map and are pushed with `npc_create` (509)
  on map entry. `attack_local_npc` (317) applies weapon/badge/skill damage,
  broadcasts `show_damage_board` (511), NPCs fight back via
  `accept_damge` (111), die via `local_npc_die` (307), drop loot via
  `drop_item_info` (527), and grant exp/gold (level-ups pushed via
  `sync_common_data` 614). NPCs lazily respawn at full HP.
- **Skills**: `skill_use` (102) broadcast via `ret_skill_use` (508),
  `skill_level_up` (130), `sync_skill_info` (540) push. A profession learns
  its basic attack (the x01 combo opener, indexPos 3) PLUS its class's full
  six-skill pool (indexPos 4..9, the two switch groups) — the basic attack
  is a separate combat action and never occupies one of the six weapon skill
  slots. A weapon instance carries all six class skills as random_attri
  entries so the info panel and the skill bar match. Weapon skills persist
  across relogin (rolled once at acquisition; `repair_stale_instances` only
  repairs weapons that are missing the correct class set, never re-rolls
  correct ones at restart).
- **Player life**: `relife_player` (132) respawn flow with
  `aoi_relife_player` (512) / `notice_relife_player` (618); hp/max_hp per
  character with level-based growth.
- **Guilds**: `guild_create` (146), `guild_join` (147) with join requests,
  `guild_approve_resverve` (154), `guild_kick` (149), `guild_job_change`
  (150) (leader/officer/member roles), `guild_donate` (175), guild shop
  (`req_open_guild_shop` 171 / `req_buy_guild_goods` 172, funded by
  donations), `guild_log` (174), `search_guild` (176), notices + member
  info, `sync_guild_new_member` (580) push.
- **Friends**: `add_friend` (124) / `del_friend` (125) (bidirectional),
  `ask_character_info` (142), friend list push `syn_friend_info` (538),
  online/offline status, `notice_add_friend` (536) / `be_deleted_friend`
  (537) pushes.
- **Mail**: `send_mail` (122), mailbox `send_mail_box` (284),
  `mail_operation` (123) (collect attachment / delete),
  `mail_update` (531) push for online recipients.
- **Sign-in**: `sign_week` (255) and `sign_30_day` (254) with daily
  gold/diamond rewards, `request_daily_mission` (121).
- **Cars/mounts**: `request_mount_info` (235) / `ret_mount_info` (630),
  `mount_equip` (236), `use_mount` (238) / `unuse_mount` (239) with AOI
  re-announce, car ownership persisted per character.
- **Copy scenes (dungeons)**: `enter_copy_scene` (107) spawns per-wave NPCs
  (`npc_create` 509) with a `count_down` (553) timer; kills are reported via
  `single_copy_scene_npc_die` (127), cleared waves trigger `next_wave`
  (515), and the final clear pays the dungeon reward through
  `show_reward_items_tips` (638). `ask_copyscenes_info` (145) reports best
  wave/done state; `leave_copy_scene` (108) abandons a run. Content lives in
  `economy.COPY_SCENES`.
- **Rank PvP (天梯 ladder)**: `request_random_rank_pvp_opponent` (133)
  matches a synthetic opponent near the player's score and pushes
  `rank_pvp_start` (547); the client's attacks are validated in
  `rank_pvp_player_attack` (136) / `rank_pvp_other_player_die` (137) and the
  result is pushed as `tiantti_result` (551) with `rank_pvp_reward` (545).
  `syn_rank_pvp_data` (541) reports score/wins/battles, ladder history is
  persisted, the top list is served via `request_top_rank_pvp_list`
  (134/543), and cumulative win-count rewards via
  `tianti_req_win_count_rewards` (157).
- **Tower**: `request/enter_tower_copy_info` (202/204) report current floor,
  `continue_tower_copy` (205) spawns a scaled floor NPC, per-floor rewards
  via `grant_tower_reward` (203), `tower_reset` (230, diamond cost),
  `tower_wipe_out` (208, instant clear). Content in `economy.TOWER`.
- **Slot machine**: `request_slot_info` (242/633), `spin_slot` (243/634,
  3 reels, pair/triple payouts), accumulating sum-reward pool claimable via
  `request_slot_sum_reward` (244/635). Content in `economy.SLOT`.
- **Maps/lines/teleports**: `enter_new_map` (106), `change_scene_line`
  (155), `request_line_state` (219, answered with `update_line_state` 568
  player counts per line), `enter_teleport_point` (251),
  `update_player_map_info` (324).
- **Wild boss (raid boss)**: `request_wild_boss_info` (200/605, boss name,
  level, hp/max, alive flag), `enter_wild_boss` (201 → npc_create +
  count_down). The boss is a shared per-map NPC (kind 3 stats) fought with
  the standard combat tags; it respawns on demand at full strength.
  Config in `economy.WILD_BOSS`.
- **Survive mode**: `request_survive_top` (245/636, best-wave leaderboard),
  `enter_survive_batttle` (246 → escalating npc waves + countdown; kills
  reported via `single_copy_scene_npc_die`), `survive_battle_finish`
  (637 → wave-scaled gold/exp reward, best wave recorded, reward tips
  pushed). Config in `economy.SURVIVE`.
- **Client progress**: `tutorial_finish` (306), `unlock_function_complete`
  (268), `re_name` (301), `change_show_type` (223), `impact_npc` (298),
  `start_download` (269) / `download_finish` (270) no-ops.

### Economy content and provisional schemas

The mission/shop *tags* were recovered from the client, but the decompiled
repo preserved no `SprotoType` classes for them, so their field layouts are
**provisional** (documented in `server/protocol.py` `REQUEST_SPECS` /
`RESPONSE_SPECS`):

- `accept_mission.request {mission_id(0)}` → `{errno(0)}`
  (0 ok, 1 no character, 2 unknown mission, 3 already active)
- `complete_mission.request {mission_id(0)}` → `{errno(0)}`
  (0 ok, 1 no character, 2 not accepted, 3 objectives not met)
- `abandon_mission.request {mission_id(0)}` → `{errno(0)}`
- `use_item.request {item_id(0), count(1)}` → `{errno(0)}` (2 = not owned)
- `sell_item.request {item_id(0), count(1)}` → `{errno(0)}`
- `ask_shop_list.request {shop_id(0)}` → `{errno(0), goods(1)}` where each
  good is `{goods_id(0), item_id(1), count(2), currency(3), price(4)}`
- `buy_shop_item.request {goods_id(0), count(1)}` → `{errno(0)}`
  (3 = insufficient currency)
- `sync_mission` push: `{missions(0)}` = array of
  `{mission_id(0), progress(1), state(2)}` (0 active, 1 claimable)
- `sync_backpack_item` push: `{items(0)}` = array of `{item_id(0), count(1)}`
- `show_reward_items_tips` push: `{gold(0), diamond(1), items(2)}`

Game content (shops, missions, item catalog, NPC kinds/spawns, skills,
cars, guild shop) lives in `server/economy.py` —
small default tables until `Bundle/Data/Data.bundle` is fully parsed; the
handlers and NPC simulation are fully data-driven, so new content only
requires extending those tables. Mission types: `buy` (progresses on shop
purchases of the target item) and `visit` (progresses on entering the target
map); missions can chain via the `next` field and pay gold/diamond/item
rewards.

## Architecture

```
server/
├── main.py      asyncio entry point: gate + game listeners, dispatcher
├── session.py   per-connection state + frame pump
├── handlers.py  protocol logic (login, world, combat, economy, guilds,
│                friends, mail, sign-in, mounts)
├── world.py     per-map player + NPC registry, AOI broadcast, NPC combat sim
├── economy.py   content tables: items, shops, missions, NPCs, skills, cars
├── db.py        SQLite persistence (accounts, characters, inventory,
│                equipment, guilds, friends, mail, skills, progress)
├── protocol.py  tag constants, typed request/response schemas
├── sproto.py    SprotoPack compression + sproto binary codec + framing
└── config.py    environment-based configuration
```

## Tests

```bash
python3 -m pip install pytest pytest-asyncio
python3 -m pytest tests/ -q
```

- `tests/test_sproto.py` — codec unit tests (pack/unpack round-trips,
  object encode/decode, frame framing).
- `tests/test_e2e.py` — drives the real server over TCP through the full
  client login flow: server list → visitor → verify → login → character
  create/pick → enter map → heartbeat → movement broadcast between two
  players.
- `tests/test_economy.py` — end-to-end mission/shop flow: shop list +
  purchase (currency debit, backpack credit), mission accept → auto-complete
  on purchase → claim reward → chained mission → abandon, visit missions via
  map movement, and item consumption.
- `tests/test_game_systems.py` — end-to-end coverage of the full game
  systems: NPC spawn pushes, combat (attack → damage → kill → exp/gold/loot),
  equip/unequip (weapon/armor/badge/fashion), storage pack, item packages,
  guilds (create/join/approve/donate/guild-shop/kick/search), friends
  (add/info/delete), mail (send/mailbox/collect/delete), sign-in rewards,
  skill level-up, and car purchase/use.
- `tests/test_pvp_dungeons.py` — end-to-end coverage of the newer systems:
  a full dungeon run (enter → countdown → wave npcs → next_wave → clear →
  rewards → done state), unknown-copy rejection, the rank PvP ladder
  (matchmaking → attacks → tiantti_result → rewards → data/history), the
  tower (info → climb → rewards → wipe-out → reset), the slot machine
  (info → spins → pool claim), map/line helpers (line state, line change,
  map switch, teleport), and the misc progress tags (tutorial, unlock,
  rename, show type, download no-ops).
- `tests/test_wild_survive.py` — end-to-end coverage of the wild boss
  (info → enter → boss npc sync → countdown) and survive mode (leaderboard
  → enter → escalating waves → finish → scaled rewards → best/leaderboard
  update).
- `tests/test_guild_battle.py` — end-to-end coverage of the weekly guild
  battle (signup → fighter list → info → betting → ranks/scores → entry
  gating), the three professions (starting weapon + real skill group,
  weapon-class locking), and the real car shop (CarData vehicles).

## Real content (Data.bundle recovery)

`server/game_data.py` holds content extracted from the APK's
`Bundle/Data/Data.bundle` (LZMA-compressed Unity asset, decompressed and
table-parsed):

- **Professions** — exactly three playable classes (string table 100128–130):
  Batfighter (械斗), Boxer (拳击), Gunner (枪手). The profession sent in
  `character_create.general` picks the weapon class and the starting skills.
- **Weapons** — `EquipData` Position=0 rows: 8 tiers per class with the real
  attack values (180/300/486/732/1044/1416/1848/2340) and the real skill
  groups (101–104 / 201–204 / 301–304 = three attacks + a dodge).
- **Cars** — `CarData`: North Star, Thunder, Conqueror, Bison, Night Walker,
  Golden King, Christmas Sleigh + the North Star GT variant, with the real
  hp/atk/speed/accel stats. The shop sells the original car vouchers
  (ItemData 9301–9307).
- **Items** — real consumables (定值-血药 potions, 复活药 revive, 药剂
  stamina potions), tickets (经验/金币/装备/赛车), rename card, world-chat
  mic, with ItemData prices.
- **Guild battle** — `GuildBattleData` row 1501: 10 fighters per guild,
  1800 s battles, gold-bar betting (item 1002, stake 200 → 500), weekly
  rounds on weekdays 5 (19:30) / 6 (20:30) / 7 (20:30), top-3 reward drops
  37001–37003.

## What works with a real client

- Account creation (visitor) and verification — matches the client's saved
  `id`/`key` flow.
- Server list and login — the client proceeds to character select.
- Character create/pick and entering the map — the client loads into the
  world and other players see each other (`aoi_add`/movement/`aoi_remove`).
- World chat and heartbeat.

Character persistence (position, level, exp, hp, name, car), currency
(gold/diamond), backpack, storage, equipment slots, skills, missions, guild
membership, friends, mail, ladder score/history and tower/slot progress are
stored in SQLite and restored on re-entry.

The remaining tags (dances, bar fight, escort, teams, VIP, videos/ads,
retrieve-account and similar) are not yet implemented; unknown tags are
logged, not crashed on.

## Wire protocol summary (recovered from Assembly-CSharp.dll)

- Transport: raw TCP.
- Frame: `[u16be len][sproto-pack(payload)]`.
- payload = `sproto(Package{type?,session?})` + `sproto(body)`.
- **Dispatch rule (NetLogic.ProcessPack, recovered from the DLL):** a frame
  whose Package has `type` is a server push (routed via NetReceiver by tag);
  a frame whose Package has `session` is an RPC response (routed via
  NetSender by session id). Server responses therefore carry ONLY the
  session — no type field. Sending a type on responses makes the real
  client drop them and hang on the loading widget.
- Sproto is the standard compact binary serialization (Skynet-style).

Full tag table: `research/notes/protocol_tags.json` (409 entries).
Full protocol notes: `docs/protocol.md`.
