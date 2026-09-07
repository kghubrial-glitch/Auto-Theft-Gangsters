# Auto Theft Gangsters v1.19 — Reverse-Engineered Network Protocol

_Recovered from `Assembly-CSharp.dll` (decompiled with ilspycmd) — APK sha256 `eb6b452c17ae02346aee41f55288fd755f8a6801cf879ca3464d8aac5b8436` (APKPure repack of v1.19)。_

## 1. Server endpoints (original, now dead)

| Purpose | Host | Port |
|---|---|---|
| Login gate (main) | `gangsterlogin.galaxyaura.com` | `9777` |
| Login gate (classic) | `gangsterlogin2.galaxyaura.com` | `9777` |
| Game server (default) | any `game_server.serverIP:serverPort` from server list | `9555` (default) |

All domains are currently NXDOMAIN — the original backend is gone, which is why this revival project exists。

## 2. Client build versions

```text
UnityVersion    = "Unity4.7"
GameVersion      = "1.012.017"
versionCode      = 14119          (v1.19)
minSdk 14 / targetSdk 28, cleartext HTTP enabled
```

## 3. Transport layer

- Raw **TCP** sockets blocking, one connection at a time.

- Optional DNS: `ServerInfoData.IsUseDns`.

### 3.1 Frame format

```
+--------+----------------------------------------------+
| uint16  | Sproto-pack(payload)                    |
| BE len   | (len bytes)                                |
+--------+----------------------------------------------+
```

- 2-byte **big-endian** length on the **packed** payload (length does not include the 2 header bytes)).
- Max one-pack size constant: `MAX_ONE_PACK_BYTE_SIZE = 16384`; receiving buffer doubles when exceeded。



## 4. Sproto (“SprotoPack”/compression

The client uses the **Sproto** serialization + packing scheme (typical of Skynet/China MMO servers。 Port of the client-side `SprotoPack.pack` / `unpack` is in `research/server/sproto_codec.py`。



**Pack (compression** operates on the raw Sproto stream before framing:]
- Processes data in 8-byte groups。

- A group with all-zero bytes → `0x00`。
- A group with 1–6 nonzero bytes → a bitmask byte (LSB-first bits for each nonzero byte) followed by the nonzero bytes in order。
- 7–8 nonzero bytes → literal escape: `0xFF,0xNN` marks a literal (NN+1)*8-byte block, followed by that many bytes (with zero padding to 8-byte boundary)。Groups of all-zero are skipped by the zero bitmask byte。





## 5. Sproto schema encoding (field stream**

Each sproto object (type derived from `SprotoTypeBase`) encodes:

```
+----------------+--------------------------------------------------+
| uint16 fn       | uint16 header records (2 bytes each)          |
| (header word) | ... up to fn records ...                          |
+----------------+--------------------------------------------------+
| body: fields in tag order, each prefixed by a uint32 length      |
+----------------+--------------------------------------------------+
```

- Header first word = number of header words following。
- Each header word: tag skip info + value:
  - if `(word & 1) == 0` → value present: `value = word/2 - 1` (small integer value)。
  - else `tag += word/2` skips that many tags。
- Field types (body encodings, all little-endian):
  - **integer** small: stored directly in header value as `(value+1)*2` (2 bytes); fits `< 32767`。
  - **integer** 32/64-bit: header value `=0`; body: `uint32 len` then 4- or 8-byte integer无量纲。
  - **string**: header value `=0`; body: `uint32 byteLen` + UTF-8 bytes。

  - **boolean**: same as small integer (0/1)。
  - **struct/object**: header value `=0`; body: `uint32 byteLen` + nested sproto object。


  - **arrays** (integer/string/bool/object lists): header value `=0`; body: `uint32 totalByteLen` then elements back-to-back (each object element prefixed by its own `uint32 len`)。Integer arrays carry a 1-byte size type (4 or 8) after the length张。

。



## 6. Frame header (Package object**

The wire frame payload (after unpacking) begins with a standard sproto object, `SprotoType.Package`:

```text
tag 0: type    (integer)
tag 1: session  (integer)
```

- Server→client requests/pushes carry `type` (protocol tag)； optionally can carry session。
- Client→server responses carry `session` (echo of the request session)； optionally type (e.g. `heart_beat` echoes type 218)。
- `NetLogic` logic:
  - if frame has `type` → dispatch to `NetReceiver` handler (RPC-like request)；
  - else if frame has `session` → dispatch to `NetSender` pending-response handler by session id。



## 7. Protocol tags (full registry: `research/notes/protocol_tags.json`, 409 entries)

Key tags used in the revival server:

:

| Tag | Name | Direction | Purpose |
|---|---|---|---|
|   2 | `visitor` | C→S / S→C | create visitor account: req(empty), resp `{id,key,state}` |
|   3 | `verfiy` | C→S / S→C | verify account: req `{id,key,versionCode}`, resp `{state,session,game_server[],...}` |
|   4 | `login` | C→S / S→C | game login: req `{session,id,logintype,version,unityVersion,serverId,time}`, resp `{type,versionCode,dataVersionCode,serverLevel}` |
|   7 | `update_game_server` | C→S / S→C | refresh game-server list: resp `{game_server[]}` |
| 100 | `map_ready` | C→S | client finished loading map (sent only AFTER its main player spawned) |
| 101 | `move` | C→S | player movement `{pos:{x,y,z,o}, moving, index, parm}` |
| 102 | `skill_use` | C→S | use skill |
| 103 | `character_list` | C→S / S→C | list characters: resp `{character[]}` |
| 104 | `character_create` | C→S / S→C | create character `{...}` resp `{character}` |
| 105 | `character_pick` | C→S / S→C | select character: req `{id}`, resp `{errno}` |
| 120 | `chat` | C→S | world chat `{tellId,tellName,chatInfo,chattype,linktype,intdata,stringdata}` |
| 218 | `heart_beat` | C→S / S→C | heartbeat every 15s: req `{time,time2}`, resp `{time,serverTime}` |
| 234 | `leave_game` | C→S | logout |
| 280 | `update_client_state` | C→S / S→C | client/server state sync |
| 281 | `refresh_online_state` | C→S | re-entered online state `{id,type,mapId}` |
| 308 | `game_check` | C→S | game guard check |
| 503 | `enter_map` | S→C push | server tells the client to load map `{mapInfoId,line_index,line_count}` (a legacy C→S form also exists) |
| 504 | `main_player_create` | S→C push | spawn the main player `{character, movement}` — must be pushed immediately after `enter_map` |
| 578 | `login_max_count` | S→C | server full (kick) |
| 660 | `retrieve_account` | C→S | account recovery |

AOI push tags (server→client）:`aoi_add`(505)`aoi_update_move`(507)`aoi_remove`(506)`aoi_update_attribute`(510)`aoi_stop_move`(513)`aoi_relife_player`(512)`aoi_social_dance`(657)a.o.



## 8. Login flow (reconstructed from client logic)

```text
player taps Login
    │
    ├─ ChooseRecommendServer()  ── selects best game_server from cached list
    │
    ├─ ConnectToServer(CurLoginServerData.LoginIP, LoginPort)   ── gate (default gangsterlogin.galaxyaura.com:9777)
    │       └─ after connect: Send<Protocol.update_game_server>  (tag 7)   ── fetch server list
    │                                     └─ resp: update_game_server.response{game_server[]} → MenuSceneController.UpdateServerList()
    │
    ├─ ConnectToServer(CurGameServerData.serverIP, serverPort)  ── game gate (default :9555)
    │       ├─ no saved account →   visitor.request {} → resp {id,key} → SavePlayerAccountId/Key
    │       └─ saved account    →   verfiy.request {id,key,versionCode} → resp {state,session,...}
    │                                                           (state 0: old account; 2: new device; handled accordingly)
    │
    ├─ LoginRequest(logintype)
    │       └─ login.request {session,id,logintype,version,unityVersion,serverId,time}
    │                                                                             └─ resp {type,versionCode,dataVersionCode,serverLevel}
    │
    ├─ CharacterListRequest()  → character_list.response {character[]}
    ├─ Select/create character
    ├─ character_pick.request{id} → resp{} (empty body on success)
    ├─ (push) enter_map{mapInfoId,line_index,line_count}  → client loads the
    │       map scene and STOPS processing frames (NetLogic.CanProcessPack=false)
    ├─ (push) main_player_create{character,movement}  → buffered during the
    │       scene load, processed when SceneController.Awake re-enables the
    │       packet pump → ObjManager.CreateMainPlayer → IsSceneReady=true →
    │       loading bar passes 90% → OnLoadingOver
    ├─ map_ready (100) sent by the client  (server answers with the AOI/NPC burst)
    └─ in-world: move/chat/heart_beat(15s)/aoi sync...
```

## 9. Game server list (`SprotoType.game_server` — fields

```text
tag 0  serverId        (long)
tag 1  serverName      (string)
tag 2  serverIP        (string)
tag 3  serverPort      (long)
tag 4  serverState     (long:  0 ok/1 busy/2 full/3 maintenance
tag 5  serverPlayerState(long)
tag 6  serverArea      (long)
tag  ️7  serverRank       (long)
tag  ️8  serverTimeZone   (long)
tag  ️9  serverWeight     (long)
tag10  newServer        (long)
```

## 10. Player character (`SprotoType.character` — selected fields

```text
tag 0  id
tag 1  general
tag 2  attribute_other
tag 3  property
tag 4  visual
tag 5  movement
tag  ️6  skills
tag  ️7  equip
tag  ️8  badge_equip
tag  ️9  fashion_equip
tag  ️10  potionIndex
tag  ️11  runtime
tag  ️12  equip_enhance
tag  ️13  download
tag  ️14  skill_index
```

## 11. Credits

- Original game: Doodle Mobile (`com.doodlemobile.vicecity`)
- APK source: APKPure CDN v1.19 (27,192,460-byte repack — original uptodown SHA256 `f78e5f5...c08c78193`)
- Decompiler: ilspycmd + androguard + monodis