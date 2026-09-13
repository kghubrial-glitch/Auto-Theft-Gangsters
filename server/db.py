"""SQLite persistence for accounts, characters, inventory, and missions.

Accounts store the visitor id/key pair the client saves on first launch; the
key acts as the account password for `verfiy`. Characters keep a JSON blob of
the create-request fields plus live world state (position, level).

Economy tables:
  * currency columns on `characters` (gold / diamond)
  * `items`      — backpack: one row per (character, item) stack
  * `missions`   — one row per accepted mission per character
"""

import json
import os
import secrets
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_key TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    last_login  INTEGER
);

CREATE TABLE IF NOT EXISTS characters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    name        TEXT NOT NULL,
    level       INTEGER NOT NULL DEFAULT 1,
    sex         INTEGER NOT NULL DEFAULT 0,
    profession  INTEGER NOT NULL DEFAULT 0,   -- 0 Batfighter, 1 Boxer, 2 Gunner
    exp         INTEGER NOT NULL DEFAULT 0,
    hp          INTEGER NOT NULL DEFAULT 100,
    max_hp      INTEGER NOT NULL DEFAULT 100,
    gold        INTEGER NOT NULL DEFAULT 5000,
    car_id      INTEGER,
    using_car   INTEGER NOT NULL DEFAULT 0,
    diamond     INTEGER NOT NULL DEFAULT 20,
    cash        INTEGER NOT NULL DEFAULT 0,
    -- map 1 is the client's LoadingScene placeholder; the real main city is 11
    map_id      TEXT NOT NULL DEFAULT '11',
    pos_x       INTEGER NOT NULL DEFAULT 0,
    pos_y       INTEGER NOT NULL DEFAULT 0,
    pos_z       INTEGER NOT NULL DEFAULT 0,
    pos_o       INTEGER NOT NULL DEFAULT 0,
    data        TEXT NOT NULL DEFAULT '{}',
    created_at  INTEGER NOT NULL,
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    item_id     INTEGER NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    seen        INTEGER NOT NULL DEFAULT 1,   -- 0 = "new" (Parm[5]==0)
    UNIQUE(char_id, item_id)
);

CREATE TABLE IF NOT EXISTS missions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    mission_id  TEXT NOT NULL,
    progress    INTEGER NOT NULL DEFAULT 0,
    state       INTEGER NOT NULL DEFAULT 0,   -- 0 active, 1 done (claimable), 2 finished
    accepted_at INTEGER NOT NULL,
    UNIQUE(char_id, mission_id)
);

CREATE TABLE IF NOT EXISTS equip_slots (
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    slot        INTEGER NOT NULL,             -- client EQUIP_BACKPACK_TYPE
                                              -- 0 weapon .. 5 necklace;
                                              -- 8 badge, 9 fashion
    item_id     INTEGER NOT NULL,
    index_id    INTEGER,                      -- item_instances.index_id
    UNIQUE(char_id, slot)
);

CREATE TABLE IF NOT EXISTS item_instances (
    index_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    item_id     INTEGER NOT NULL,
    quality     INTEGER NOT NULL DEFAULT 0,   -- EQUIP_QUALITY 0=WHITE..3=PURPLE
    level       INTEGER NOT NULL DEFAULT 0,   -- upgrade level
    attrs       TEXT NOT NULL DEFAULT '[]',   -- JSON [(attr_id,val,quality,skillId)]
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS storagepack (
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    item_id     INTEGER NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    UNIQUE(char_id, item_id)
);

CREATE TABLE IF NOT EXISTS guilds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    leader      TEXT NOT NULL,
    notice      TEXT NOT NULL DEFAULT '',
    gold        INTEGER NOT NULL DEFAULT 0,
    level       INTEGER NOT NULL DEFAULT 1,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_members (
    guild_id    INTEGER NOT NULL REFERENCES guilds(id),
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    name        TEXT NOT NULL,
    job         INTEGER NOT NULL DEFAULT 2,   -- 0 leader, 1 officer, 2 member
    joined_at   INTEGER NOT NULL,
    UNIQUE(guild_id, char_id)
);

CREATE TABLE IF NOT EXISTS guild_requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL REFERENCES guilds(id),
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    name        TEXT NOT NULL,
    created_at  INTEGER NOT NULL,
    UNIQUE(guild_id, char_id)
);

CREATE TABLE IF NOT EXISTS guild_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL REFERENCES guilds(id),
    entry       TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS friends (
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    friend_id   INTEGER NOT NULL REFERENCES characters(id),
    UNIQUE(char_id, friend_id)
);

CREATE TABLE IF NOT EXISTS mails (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    sender      TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    gold        INTEGER NOT NULL DEFAULT 0,
    diamond     INTEGER NOT NULL DEFAULT 0,
    collected   INTEGER NOT NULL DEFAULT 0,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    key         TEXT NOT NULL,
    value       INTEGER NOT NULL DEFAULT 0,
    UNIQUE(char_id, key)
);

CREATE TABLE IF NOT EXISTS skills (
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    skill_id    INTEGER NOT NULL,
    level       INTEGER NOT NULL DEFAULT 1,
    index_pos   INTEGER NOT NULL DEFAULT 0,
    UNIQUE(char_id, skill_id)
);

CREATE TABLE IF NOT EXISTS pvp_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    blob        BLOB NOT NULL,
    created_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS guild_battle (
    guild_id    INTEGER NOT NULL REFERENCES guilds(id),
    week        INTEGER NOT NULL,
    score       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, week)
);

CREATE TABLE IF NOT EXISTS guild_battle_members (
    guild_id    INTEGER NOT NULL REFERENCES guilds(id),
    week        INTEGER NOT NULL,
    name        TEXT NOT NULL,
    job         INTEGER NOT NULL DEFAULT 2,
    PRIMARY KEY (guild_id, week, name)
);

CREATE TABLE IF NOT EXISTS guild_battle_guess (
    char_id     INTEGER NOT NULL REFERENCES characters(id),
    week        INTEGER NOT NULL,
    guild       TEXT NOT NULL,
    amount      INTEGER NOT NULL,
    settled     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (char_id, week)
);
"""


class Database:
    def __init__(self, path: str = "atg_server.db") -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        # migrate pre-economy databases: add the currency columns if missing
        cols = {r["name"] for r in self._conn.execute(
            "PRAGMA table_info(characters)")}
        if "gold" not in cols:
            self._conn.execute(
                "ALTER TABLE characters ADD COLUMN gold INTEGER NOT NULL DEFAULT 5000")
        if "diamond" not in cols:
            self._conn.execute(
                "ALTER TABLE characters ADD COLUMN diamond INTEGER NOT NULL DEFAULT 20")
        if "cash" not in cols:
            self._conn.execute(
                "ALTER TABLE characters ADD COLUMN cash INTEGER NOT NULL DEFAULT 0")
        # migrate pre-seen databases: every existing stack is "seen" (the
        # new-flag only ever applies to items granted AFTER this migration)
        icols = {r["name"] for r in self._conn.execute(
            "PRAGMA table_info(items)")}
        if "seen" not in icols:
            self._conn.execute(
                "ALTER TABLE items ADD COLUMN seen INTEGER NOT NULL DEFAULT 1")
        if "profession" not in cols:
            self._conn.execute(
                "ALTER TABLE characters ADD COLUMN profession INTEGER"
                " NOT NULL DEFAULT 0")
        # migrate legacy rows saved with map_id '1' — that id is the client's
        # LoadingScene placeholder and hangs the world-entry loader
        self._conn.execute(
            "UPDATE characters SET map_id = '11' WHERE map_id = '1'")
        # migrate pre-instance databases: equip_slots.index_id + legacy armor
        # slot renumbering (old slots 3..7 = helmet..necklace -> 1..5) and
        # badge slot 2 -> 8 / fashion slot 3 -> 9 so they match the client's
        # EQUIP_BACKPACK_TYPE numbering going forward. Renumbering runs ONLY
        # on databases that predate index_id — re-running it on migrated
        # databases would corrupt the (now legitimate) slots 2/3 armor rows.
        ecols = {r["name"] for r in self._conn.execute(
            "PRAGMA table_info(equip_slots)")}
        legacy_equips = "index_id" not in ecols
        if legacy_equips:
            self._conn.execute(
                "ALTER TABLE equip_slots ADD COLUMN index_id INTEGER")
            self._conn.execute(
                "UPDATE equip_slots SET slot = slot - 2"
                " WHERE slot >= 3 AND slot <= 7")
            self._conn.execute(
                "UPDATE equip_slots SET slot = 8 WHERE slot = 2")
            self._conn.execute(
                "UPDATE equip_slots SET slot = 9 WHERE slot = 3")
        # skills table: index_pos added in this revision
        scols = {r["name"] for r in self._conn.execute(
            "PRAGMA table_info(skills)")}
        if "index_pos" not in scols:
            self._conn.execute(
                "ALTER TABLE skills ADD COLUMN index_pos INTEGER"
                " NOT NULL DEFAULT 0")
        self._conn.commit()
        # one-time instance migration: legacy rows referenced bare item ids
        # with no index_id — roll a persisted instance for each so equipment
        # already on existing accounts keeps stable attrs/colors.
        if self.get_flag_row("_instance_migration_done") is None:
            self._migrate_equips_to_instances()
            self.set_flag(0, "_instance_migration_done", 1)

    # -- accounts -----------------------------------------------------
    def create_account(self):
        """Create a visitor account, returning (id, key)."""
        key = secrets.token_hex(16)
        now = int(time.time())
        cur = self._conn.execute(
            "INSERT INTO accounts (account_key, created_at) VALUES (?, ?)",
            (key, now),
        )
        self._conn.commit()
        return cur.lastrowid, key

    def verify_account(self, account_id: int, key: str):
        """Return the account row if id/key match, else None."""
        row = self._conn.execute(
            "SELECT * FROM accounts WHERE id = ? AND account_key = ?",
            (account_id, key),
        ).fetchone()
        if row is None:
            return None
        self._conn.execute(
            "UPDATE accounts SET last_login = ? WHERE id = ?",
            (int(time.time()), account_id),
        )
        self._conn.commit()
        return row

    # -- characters -----------------------------------------------------
    def list_characters(self, account_id: int):
        return self._conn.execute(
            "SELECT * FROM characters WHERE account_id = ? ORDER BY id",
            (account_id,),
        ).fetchall()

    def get_character(self, char_id: int):
        return self._conn.execute(
            "SELECT * FROM characters WHERE id = ?", (char_id,)
        ).fetchone()

    def create_character(self, account_id: int, name: str, sex: int = 0,
                         level: int = 1, profession: int = 0,
                         extra: dict = None):
        extra = extra or {}
        now = int(time.time())
        try:
            cur = self._conn.execute(
                "INSERT INTO characters (account_id, name, level, sex,"
                " profession, data, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (account_id, name, level, sex, profession,
                 json.dumps(extra), now),
            )
            # Testing build: maxed starting wallets (TEST_START_GOLD /
            # TEST_START_DIAMOND from economy) land in the currency columns.
            if extra.get("cash") or extra.get("gold") or extra.get("diamond"):
                self._conn.execute(
                    "UPDATE characters SET cash = COALESCE(cash, 0) + ?,"
                    " gold = COALESCE(gold, 0) + ?,"
                    " diamond = COALESCE(diamond, 0) + ? WHERE id = ?",
                    (int(extra.get("cash") or 0),
                     int(extra.get("gold") or 0),
                     int(extra.get("diamond") or 0), cur.lastrowid),
                )
            self._conn.commit()
        except sqlite3.IntegrityError:
            return None  # duplicate name
        return self.get_character(cur.lastrowid)

    def save_position(self, char_id: int, map_id: str, x: int, y: int,
                      z: int, o: int) -> None:
        self._conn.execute(
            "UPDATE characters SET map_id = ?, pos_x = ?, pos_y = ?, pos_z = ?,"
            " pos_o = ? WHERE id = ?",
            (map_id, x, y, z, o, char_id),
        )
        self._conn.commit()

    def save_level(self, char_id: int, level: int) -> None:
        self._conn.execute(
            "UPDATE characters SET level = ? WHERE id = ?", (level, char_id)
        )
        self._conn.commit()

    # -- currency -------------------------------------------------------
    # currency constants (economy.CURRENCY_*): 0 cash, 1 gold, 2 diamond —
    # the client's property money1/2/3 mapping.
    CURRENCY_COLUMNS = {0: "cash", 1: "gold", 2: "diamond"}

    def get_currency(self, char_id: int, currency: int) -> int:
        col = self.CURRENCY_COLUMNS.get(currency, "gold")
        row = self._conn.execute(
            "SELECT %s AS v FROM characters WHERE id = ?" % col, (char_id,)
        ).fetchone()
        return row["v"] if row else 0

    def add_currency(self, char_id: int, currency: int, amount: int) -> int:
        """Add (or spend, negative amount) currency; returns the new balance."""
        col = self.CURRENCY_COLUMNS.get(currency, "gold")
        bal = self.get_currency(char_id, currency)
        new_bal = max(0, bal + amount)
        self._conn.execute(
            "UPDATE characters SET %s = ? WHERE id = ?" % col, (new_bal, char_id)
        )
        self._conn.commit()
        return new_bal

    # -- items / backpack -----------------------------------------------
    def list_items(self, char_id: int):
        return self._conn.execute(
            "SELECT item_id, count, seen FROM items WHERE char_id = ?"
            " ORDER BY item_id",
            (char_id,),
        ).fetchall()

    def get_item_count(self, char_id: int, item_id: int) -> int:
        row = self._conn.execute(
            "SELECT count FROM items WHERE char_id = ? AND item_id = ?",
            (char_id, item_id),
        ).fetchone()
        return row["count"] if row else 0

    def add_item(self, char_id: int, item_id: int, count: int,
                 seen: int = None) -> int:
        """Add `count` of `item_id` to the backpack; returns the new count.

        A stack created FROM ZERO is marked "new" (seen=0) so the client
        shows the new-item flag and the player can acknowledge it with
        change_item_state(240). Pass `seen=1` for starting grants (they must
        not appear as freshly-acquired). Already-seen stacks keep their flag.
        """
        have = self.get_item_count(char_id, item_id)
        new = max(0, have + count)
        if new == 0:
            self._conn.execute(
                "DELETE FROM items WHERE char_id = ? AND item_id = ?",
                (char_id, item_id),
            )
        elif have == 0:
            new_seen = 0 if seen is None else (1 if seen else 0)
            self._conn.execute(
                "INSERT INTO items (char_id, item_id, count, seen)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT(char_id, item_id) DO UPDATE SET count = ?",
                (char_id, item_id, new, new_seen, new),
            )
        else:
            self._conn.execute(
                "INSERT INTO items (char_id, item_id, count)"
                " VALUES (?, ?, ?)"
                " ON CONFLICT(char_id, item_id) DO UPDATE SET count = ?",
                (char_id, item_id, new, new),
            )
        self._conn.commit()
        return new

    def get_item_seen(self, char_id: int, item_id: int) -> int:
        row = self._conn.execute(
            "SELECT seen FROM items WHERE char_id = ? AND item_id = ?",
            (char_id, item_id),
        ).fetchone()
        return row["seen"] if row else 1

    def mark_item_seen(self, char_id: int, item_id: int) -> None:
        """Record that the player acknowledged an item (new-flag cleared)."""
        self._conn.execute(
            "UPDATE items SET seen = 1 WHERE char_id = ? AND item_id = ?",
            (char_id, item_id),
        )
        self._conn.commit()

    # -- missions ---------------------------------------------------------
    def list_missions(self, char_id: int):
        return self._conn.execute(
            "SELECT * FROM missions WHERE char_id = ? ORDER BY mission_id",
            (char_id,),
        ).fetchall()

    def get_mission(self, char_id: int, mission_id: int):
        return self._conn.execute(
            "SELECT * FROM missions WHERE char_id = ? AND mission_id = ?",
            (char_id, mission_id),
        ).fetchone()

    def accept_mission(self, char_id: int, mission_id,
                       accepted_at: int = None) -> bool:
        if accepted_at is None:
            accepted_at = int(time.time())
        try:
            self._conn.execute(
                "INSERT INTO missions (char_id, mission_id, accepted_at)"
                " VALUES (?, ?, ?)",
                (char_id, str(mission_id), accepted_at),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # already accepted

    def set_mission_progress(self, char_id: int, mission_id: int,
                             progress: int, state: int) -> None:
        self._conn.execute(
            "UPDATE missions SET progress = ?, state = ?"
            " WHERE char_id = ? AND mission_id = ?",
            (progress, state, char_id, mission_id),
        )
        self._conn.commit()

    def finish_mission(self, char_id: int, mission_id: int) -> None:
        self._conn.execute(
            "DELETE FROM missions WHERE char_id = ? AND mission_id = ?",
            (char_id, mission_id),
        )
        self._conn.commit()

    # -- exp / hp --------------------------------------------------------
    def add_exp(self, char_id: int, amount: int) -> int:
        """Add exp and level up (1000 exp per level); returns (level, exp)."""
        self._conn.execute(
            "UPDATE characters SET exp = exp + ? WHERE id = ?",
            (amount, char_id),
        )
        row = self._conn.execute(
            "SELECT level, exp FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        level, exp = row["level"], row["exp"]
        while exp >= 1000 * level:
            exp -= 1000 * level
            level += 1
            # level-up is a change event: attrs (and thus max_hp) are
            # recalculated by handlers.economy.recalc_character afterwards.
            self._conn.execute(
                "UPDATE characters SET max_hp = max_hp + 10 WHERE id = ?",
                (char_id,))
        self._conn.execute(
            "UPDATE characters SET level = ?, exp = ? WHERE id = ?",
            (level, exp, char_id),
        )
        self._conn.commit()
        return level, exp

    def get_hp(self, char_id: int):
        row = self._conn.execute(
            "SELECT hp, max_hp FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        return (row["hp"], row["max_hp"]) if row else (0, 0)

    def set_hp(self, char_id: int, hp: int) -> int:
        row = self._conn.execute(
            "SELECT max_hp FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        max_hp = row["max_hp"] if row else 100
        hp = max(0, min(hp, max_hp))
        self._conn.execute(
            "UPDATE characters SET hp = ? WHERE id = ?", (hp, char_id))
        self._conn.commit()
        return hp

    def set_max_hp(self, char_id: int, max_hp: int) -> int:
        self._conn.execute(
            "UPDATE characters SET max_hp = ? WHERE id = ?",
            (max(1, int(max_hp)), char_id))
        self._conn.commit()
        return max_hp

    # -- persisted character attributes -----------------------------------
    # The attribute set is written ONLY on change events (equip/unequip/
    # upgrade/chest/level-up) and loaded verbatim at login — never rolled.
    def save_attributes(self, char_id: int, attrs: dict) -> None:
        data = self._get_data(char_id)
        data["attributes"] = attrs
        self._conn.execute(
            "UPDATE characters SET data = ? WHERE id = ?",
            (json.dumps(data), char_id))
        self._conn.commit()

    def load_attributes(self, char_id: int) -> dict:
        attrs = self._get_data(char_id).get("attributes") or {}
        # JSON keys are strings; normalize back to int attr ids so
        # attrs.get(1001)-style lookups work everywhere
        out = {}
        for k, v in attrs.items():
            try:
                out[int(k)] = v
            except (TypeError, ValueError):
                out[k] = v          # "power" and other named keys
        return out

    # -- character random status (rolled once, persisted, never re-rolled) --
    def get_random_status(self, char_id: int) -> dict:
        out = {}
        for k, v in (self._get_data(char_id).get("random_status") or {}).items():
            try:
                out[int(k)] = v
            except (TypeError, ValueError):
                out[k] = v
        return out

    def set_random_status(self, char_id: int, status: dict) -> None:
        data = self._get_data(char_id)
        data["random_status"] = status
        self._conn.execute(
            "UPDATE characters SET data = ? WHERE id = ?",
            (json.dumps(data), char_id))
        self._conn.commit()

    def _get_data(self, char_id: int) -> dict:
        row = self._conn.execute(
            "SELECT data FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        try:
            return json.loads(row["data"]) if row else {}
        except (TypeError, ValueError):
            return {}

    # -- item instances (rolled attrs/colors persist with the item) -------
    def create_instance(self, char_id: int, item_id: int, quality: int = 0,
                        attrs: list = None, level: int = 0) -> int:
        """Insert a rolled item instance; returns its stable index_id."""
        cur = self._conn.execute(
            "INSERT INTO item_instances (char_id, item_id, quality, level,"
            " attrs, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (char_id, item_id, quality, level,
             json.dumps(attrs or []), int(time.time())),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_instance(self, index_id: int):
        row = self._conn.execute(
            "SELECT * FROM item_instances WHERE index_id = ?", (index_id,)
        ).fetchone()
        if row is None:
            return None
        out = dict(row)
        out["attrs"] = json.loads(out["attrs"])
        return out

    def list_instances(self, char_id: int) -> list:
        """All rolled instances for a character (backpack + equipped)."""
        out = []
        for row in self._conn.execute(
                "SELECT * FROM item_instances WHERE char_id = ?"
                " ORDER BY index_id", (char_id,)):
            d = dict(row)
            d["attrs"] = json.loads(d["attrs"])
            out.append(d)
        return out

    def find_instances(self, char_id: int, item_id: int) -> list:
        """Instances of one item id, oldest first."""
        out = []
        for row in self._conn.execute(
                "SELECT * FROM item_instances WHERE char_id = ? AND item_id = ?"
                " ORDER BY index_id", (char_id, item_id)):
            d = dict(row)
            d["attrs"] = json.loads(d["attrs"])
            out.append(d)
        return out

    def set_instance_level(self, index_id: int, level: int) -> None:
        self._conn.execute(
            "UPDATE item_instances SET level = ? WHERE index_id = ?",
            (level, index_id))
        self._conn.commit()

    def delete_instance(self, index_id: int) -> None:
        self._conn.execute(
            "DELETE FROM item_instances WHERE index_id = ?", (index_id,))
        self._conn.commit()

    def _migrate_equips_to_instances(self) -> None:
        """Legacy rows reference a bare item id with no index_id; roll and
        persist an instance per equipped item so existing accounts keep
        stable attrs/colors across this upgrade."""
        import random
        from . import economy
        for row in self._conn.execute(
                "SELECT rowid AS rid, char_id, slot, item_id FROM equip_slots"
                " WHERE index_id IS NULL").fetchall():
            if row["slot"] in (8, 9):
                continue            # badge/fashion have no rolled attrs
            idef = economy.ITEMS.get(row["item_id"], {})
            if idef.get("slot") == 0 or "weapon_class" in idef:
                q, attrs = economy.roll_weapon_instance(row["item_id"])
            else:
                q, attrs = economy.roll_armor_instance(row["item_id"],
                                                        random)
            iid = self.create_instance(row["char_id"], row["item_id"], q,
                                       attrs)
            self._conn.execute(
                "UPDATE equip_slots SET index_id = ? WHERE rowid = ?",
                (iid, row["rid"]))
        self._conn.commit()

    def repair_stale_instances(self) -> None:
        """Re-roll instances persisted by earlier bugged rolls:

        * weapons that carried the base attack as a random_attri "skill"
          entry (attr 1001 inside random_attri) or that rolled from the
          wrong class pool (the pool lookup used `weapon_class`, which the
          ITEMS merge names `class`) — weapons must carry ONLY one rolled
          skill from their class's 6-skill pool, never the basic attack;
        * armor whose random_attri included the base status row (it showed
          up as a bogus "random status") — random_attri must hold only the
          1-2 random bonus stats.
        """
        from . import economy
        for row in self._conn.execute(
                "SELECT index_id, char_id, item_id FROM item_instances") \
                .fetchall():
            idef = economy.ITEMS.get(row["item_id"], {})
            is_weapon = idef.get("slot") == 0 or "weapon_class" in idef
            if is_weapon:
                q, attrs = economy.roll_weapon_instance(row["item_id"])
            elif idef.get("type") == "equipment":
                old = json.loads(self._conn.execute(
                    "SELECT attrs FROM item_instances WHERE index_id = ?",
                    (row["index_id"],)).fetchone()["attrs"])
                has_base = any(a[1] == 0 for a in old if len(a) > 1)
                base_ids = {a for a, _ in economy.armor_base_attrs(
                    row["item_id"])}
                has_base_status = any(a[1] in base_ids for a in old
                                      if len(a) > 1)
                if not has_base and not has_base_status:
                    continue            # already clean
                q, attrs = economy.roll_armor_instance(row["item_id"])
            else:
                continue                # fashion/badge: no rolled attrs
            self._conn.execute(
                "UPDATE item_instances SET quality = ?, attrs = ?"
                " WHERE index_id = ?",
                (q, json.dumps(attrs), row["index_id"]))
        self._conn.commit()

    def get_flag_row(self, key: str):
        return self._conn.execute(
            "SELECT value FROM progress WHERE char_id = 0 AND key = ?",
            (key,)).fetchone()

    # -- equipment / storage ---------------------------------------------
    def get_equipped(self, char_id: int, slot: int):
        row = self._conn.execute(
            "SELECT item_id FROM equip_slots WHERE char_id = ? AND slot = ?",
            (char_id, slot),
        ).fetchone()
        return row["item_id"] if row else None

    def get_equipped_index(self, char_id: int, slot: int):
        """The instance index_id equipped in `slot` (None if empty)."""
        row = self._conn.execute(
            "SELECT index_id FROM equip_slots WHERE char_id = ? AND slot = ?",
            (char_id, slot),
        ).fetchone()
        return row["index_id"] if row else None

    def find_slot_by_index(self, char_id: int, index_id: int):
        """The equip slot holding `index_id`, or None."""
        row = self._conn.execute(
            "SELECT slot FROM equip_slots WHERE char_id = ? AND index_id = ?",
            (char_id, index_id),
        ).fetchone()
        return row["slot"] if row else None

    def set_equipped(self, char_id: int, slot: int, item_id,
                     index_id: int = None) -> None:
        self._conn.execute(
            "DELETE FROM equip_slots WHERE char_id = ? AND slot = ?",
            (char_id, slot),
        )
        if item_id is not None:
            self._conn.execute(
                "INSERT INTO equip_slots (char_id, slot, item_id, index_id)"
                " VALUES (?, ?, ?, ?)",
                (char_id, slot, item_id, index_id),
            )
        self._conn.commit()

    def list_equipped(self, char_id: int):
        return self._conn.execute(
            "SELECT slot, item_id, index_id FROM equip_slots WHERE char_id = ?",
            (char_id,),
        ).fetchall()

    def list_equipped_instances(self, char_id: int) -> list:
        """Full rolled instances for every equipped slot (attribute/power
        recalculation). Items without a rolled instance (badge/fashion or
        legacy rows) are skipped."""
        out = []
        for row in self._conn.execute(
                "SELECT index_id FROM equip_slots WHERE char_id = ?"
                " AND index_id IS NOT NULL", (char_id,)):
            inst = self.get_instance(row["index_id"])
            if inst is not None:
                out.append(inst)
        return out

    def list_storage(self, char_id: int):
        return self._conn.execute(
            "SELECT item_id, count FROM storagepack WHERE char_id = ?"
            " ORDER BY item_id", (char_id,),
        ).fetchall()

    def get_storage_count(self, char_id: int, item_id: int) -> int:
        row = self._conn.execute(
            "SELECT count FROM storagepack WHERE char_id = ? AND item_id = ?",
            (char_id, item_id),
        ).fetchone()
        return row["count"] if row else 0

    def add_storage(self, char_id: int, item_id: int, count: int) -> int:
        new = max(0, self.get_storage_count(char_id, item_id) + count)
        if new == 0:
            self._conn.execute(
                "DELETE FROM storagepack WHERE char_id = ? AND item_id = ?",
                (char_id, item_id),
            )
        else:
            self._conn.execute(
                "INSERT INTO storagepack (char_id, item_id, count) VALUES (?, ?, ?)"
                " ON CONFLICT(char_id, item_id) DO UPDATE SET count = ?",
                (char_id, item_id, new, new),
            )
        self._conn.commit()
        return new

    # -- guilds ------------------------------------------------------------
    def create_guild(self, name: str, leader_name: str):
        try:
            cur = self._conn.execute(
                "INSERT INTO guilds (name, leader, created_at) VALUES (?, ?, ?)",
                (name, leader_name, int(time.time())),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            return None
        return self.get_guild(cur.lastrowid)

    def get_guild(self, guild_id: int):
        return self._conn.execute(
            "SELECT * FROM guilds WHERE id = ?", (guild_id,)
        ).fetchone()

    def get_guild_by_member(self, char_id: int):
        row = self._conn.execute(
            "SELECT g.* FROM guilds g JOIN guild_members m ON m.guild_id = g.id"
            " WHERE m.char_id = ?", (char_id,),
        ).fetchone()
        return row

    def list_guilds(self):
        return self._conn.execute(
            "SELECT * FROM guilds ORDER BY id").fetchall()

    def search_guilds(self, pattern: str):
        return self._conn.execute(
            "SELECT * FROM guilds WHERE name LIKE ? ORDER BY id",
            ("%" + pattern + "%",),
        ).fetchall()

    def guild_member_count(self, guild_id: int) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM guild_members WHERE guild_id = ?",
            (guild_id,),
        ).fetchone()
        return row["c"] if row else 0

    def list_guild_members(self, guild_id: int):
        return self._conn.execute(
            "SELECT * FROM guild_members WHERE guild_id = ? ORDER BY job, name",
            (guild_id,),
        ).fetchall()

    def get_guild_member(self, guild_id: int, char_id: int):
        return self._conn.execute(
            "SELECT * FROM guild_members WHERE guild_id = ? AND char_id = ?",
            (guild_id, char_id),
        ).fetchone()

    def add_guild_member(self, guild_id: int, char_id: int, name: str,
                         job: int = 2) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO guild_members (guild_id, char_id, name, job,"
            " joined_at) VALUES (?, ?, ?, ?, ?)",
            (guild_id, char_id, name, job, int(time.time())),
        )
        self._conn.commit()

    def remove_guild_member(self, guild_id: int, char_id: int) -> None:
        self._conn.execute(
            "DELETE FROM guild_members WHERE guild_id = ? AND char_id = ?",
            (guild_id, char_id),
        )
        self._conn.commit()

    def set_guild_job(self, guild_id: int, char_id: int, job: int) -> None:
        self._conn.execute(
            "UPDATE guild_members SET job = ? WHERE guild_id = ? AND char_id = ?",
            (job, guild_id, char_id),
        )
        self._conn.commit()

    def add_guild_gold(self, guild_id: int, amount: int) -> int:
        row = self._conn.execute(
            "SELECT gold FROM guilds WHERE id = ?", (guild_id,)
        ).fetchone()
        gold = max(0, (row["gold"] if row else 0) + amount)
        self._conn.execute(
            "UPDATE guilds SET gold = ? WHERE id = ?", (gold, guild_id))
        self._conn.commit()
        return gold

    def set_guild_notice(self, guild_id: int, notice: str) -> None:
        self._conn.execute(
            "UPDATE guilds SET notice = ? WHERE id = ?", (notice, guild_id))
        self._conn.commit()

    def add_guild_log(self, guild_id: int, entry: str) -> None:
        self._conn.execute(
            "INSERT INTO guild_log (guild_id, entry, created_at) VALUES (?, ?, ?)",
            (guild_id, entry, int(time.time())),
        )
        self._conn.commit()

    def list_guild_log(self, guild_id: int, limit: int = 20):
        return self._conn.execute(
            "SELECT entry, created_at FROM guild_log WHERE guild_id = ?"
            " ORDER BY id DESC LIMIT ?", (guild_id, limit),
        ).fetchall()

    def add_guild_request(self, guild_id: int, char_id: int, name: str) -> bool:
        try:
            self._conn.execute(
                "INSERT INTO guild_requests (guild_id, char_id, name, created_at)"
                " VALUES (?, ?, ?, ?)",
                (guild_id, char_id, name, int(time.time())),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_guild_requests(self, guild_id: int):
        return self._conn.execute(
            "SELECT * FROM guild_requests WHERE guild_id = ? ORDER BY id",
            (guild_id,),
        ).fetchall()

    def remove_guild_request(self, guild_id: int, char_id: int) -> None:
        self._conn.execute(
            "DELETE FROM guild_requests WHERE guild_id = ? AND char_id = ?",
            (guild_id, char_id),
        )
        self._conn.commit()

    # -- friends ------------------------------------------------------------
    def list_friends(self, char_id: int):
        return self._conn.execute(
            "SELECT friend_id FROM friends WHERE char_id = ? ORDER BY friend_id",
            (char_id,),
        ).fetchall()

    def add_friend(self, char_id: int, friend_id: int) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO friends (char_id, friend_id) VALUES (?, ?)",
            (char_id, friend_id),
        )
        self._conn.commit()

    def remove_friend(self, char_id: int, friend_id: int) -> None:
        self._conn.execute(
            "DELETE FROM friends WHERE char_id = ? AND friend_id = ?",
            (char_id, friend_id),
        )
        self._conn.commit()

    # -- mail ---------------------------------------------------------------
    def list_mails(self, char_id: int):
        return self._conn.execute(
            "SELECT * FROM mails WHERE char_id = ? ORDER BY id DESC", (char_id,)
        ).fetchall()

    def get_mail(self, char_id: int, mail_id: int):
        return self._conn.execute(
            "SELECT * FROM mails WHERE char_id = ? AND id = ?",
            (char_id, mail_id),
        ).fetchone()

    def send_mail(self, char_id: int, sender: str, title: str, body: str,
                  gold: int = 0, diamond: int = 0) -> int:
        cur = self._conn.execute(
            "INSERT INTO mails (char_id, sender, title, body, gold, diamond,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (char_id, sender, title, body, gold, diamond, int(time.time())),
        )
        self._conn.commit()
        return cur.lastrowid

    def set_mail_collected(self, mail_id: int) -> None:
        self._conn.execute(
            "UPDATE mails SET collected = 1 WHERE id = ?", (mail_id,))
        self._conn.commit()

    def delete_mail(self, char_id: int, mail_id: int) -> None:
        self._conn.execute(
            "DELETE FROM mails WHERE char_id = ? AND id = ?", (char_id, mail_id))
        self._conn.commit()

    # -- generic progress key/values (sign-in, daily, skills…) --------------
    def get_progress(self, char_id: int, key: str) -> int:
        row = self._conn.execute(
            "SELECT value FROM progress WHERE char_id = ? AND key = ?",
            (char_id, key),
        ).fetchone()
        return row["value"] if row else 0

    def set_progress(self, char_id: int, key: str, value: int) -> None:
        self._conn.execute(
            "INSERT INTO progress (char_id, key, value) VALUES (?, ?, ?)"
            " ON CONFLICT(char_id, key) DO UPDATE SET value = ?",
            (char_id, key, value, value),
        )
        self._conn.commit()

    # -- skills ---------------------------------------------------------------
    def list_skills(self, char_id: int):
        return self._conn.execute(
            "SELECT skill_id, level, index_pos FROM skills WHERE char_id = ?"
            " ORDER BY skill_id", (char_id,),
        ).fetchall()

    def get_skill(self, char_id: int, skill_id: int):
        return self._conn.execute(
            "SELECT level FROM skills WHERE char_id = ? AND skill_id = ?",
            (char_id, skill_id),
        ).fetchone()

    def learn_skill(self, char_id: int, skill_id: int,
                    index_pos: int = None) -> int:
        row = self.get_skill(char_id, skill_id)
        level = (row["level"] if row else 0) + 1
        self._conn.execute(
            "INSERT INTO skills (char_id, skill_id, level, index_pos)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(char_id, skill_id) DO UPDATE SET level = ?",
            (char_id, skill_id, level,
             index_pos if index_pos is not None else
             (row["index_pos"] if row else 0), level),
        )
        self._conn.commit()
        return level

    def set_skill_index_pos(self, char_id: int, skill_id: int,
                            index_pos: int) -> None:
        self._conn.execute(
            "UPDATE skills SET index_pos = ?"
            " WHERE char_id = ? AND skill_id = ?",
            (index_pos, char_id, skill_id),
        )
        self._conn.commit()

    # -- pvp ladder -------------------------------------------------------------
    def append_pvp_history(self, char_id: int, blob: bytes) -> None:
        """Record a ladder battle (blob is the pre-encoded wire object)."""
        self._conn.execute(
            "INSERT INTO pvp_history (char_id, blob, created_at)"
            " VALUES (?, ?, ?)", (char_id, blob, int(time.time())))
        self._conn.commit()

    def list_pvp_history(self, char_id: int, limit: int = 20):
        return self._conn.execute(
            "SELECT blob FROM pvp_history WHERE char_id = ?"
            " ORDER BY id DESC LIMIT ?", (char_id, limit)
        ).fetchall()

    def top_pvp_scores(self, limit: int = 10):
        """Top ladder scores joined with character names."""
        progress = self._conn.execute(
            "SELECT char_id, value FROM progress WHERE key = 'pvp_score'"
            " ORDER BY value DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in progress:
            row = self._conn.execute(
                "SELECT name FROM characters WHERE id = ?", (r["char_id"],)
            ).fetchone()
            if row is not None:
                out.append({"name": row["name"], "score": r["value"]})
        return out

    # -- guild battle (weekly guild-vs-guild war) ----------------------------
    def set_guild_battle_members(self, guild_id: int, week: int,
                                 names: list) -> None:
        self._conn.execute(
            "DELETE FROM guild_battle_members WHERE guild_id = ? AND week = ?",
            (guild_id, week))
        for i, name in enumerate(names):
            self._conn.execute(
                "INSERT OR IGNORE INTO guild_battle_members"
                " (guild_id, week, name, job) VALUES (?, ?, ?, ?)",
                (guild_id, week, name, 0 if i == 0 else 2))
        self._conn.commit()

    def list_guild_battle_members(self, guild_id: int, week: int):
        return self._conn.execute(
            "SELECT name, job FROM guild_battle_members"
            " WHERE guild_id = ? AND week = ? ORDER BY job, rowid",
            (guild_id, week)).fetchall()

    def add_guild_battle_score(self, guild_id: int, week: int,
                               amount: int) -> int:
        self._conn.execute(
            "INSERT INTO guild_battle (guild_id, week, score) VALUES (?, ?, ?)"
            " ON CONFLICT(guild_id, week)"
            " DO UPDATE SET score = score + ?",
            (guild_id, week, amount, amount))
        self._conn.commit()
        return self.get_guild_battle_score(guild_id, week)

    def get_guild_battle_score(self, guild_id: int, week: int) -> int:
        row = self._conn.execute(
            "SELECT score FROM guild_battle WHERE guild_id = ? AND week = ?",
            (guild_id, week)).fetchone()
        return row["score"] if row else 0

    def top_guild_battle_scores(self, week: int, limit: int = 10):
        rows = self._conn.execute(
            "SELECT guild_id, score FROM guild_battle WHERE week = ?"
            " ORDER BY score DESC LIMIT ?", (week, limit)).fetchall()
        out = []
        for r in rows:
            g = self._conn.execute(
                "SELECT name FROM guilds WHERE id = ?", (r["guild_id"],)
            ).fetchone()
            if g is not None:
                out.append({"guild_id": r["guild_id"], "name": g["name"],
                            "score": r["score"]})
        return out

    def set_guild_battle_guess(self, char_id: int, week: int,
                               guild: str, amount: int) -> None:
        self._conn.execute(
            "INSERT INTO guild_battle_guess (char_id, week, guild, amount)"
            " VALUES (?, ?, ?, ?)"
            " ON CONFLICT(char_id, week)"
            " DO UPDATE SET guild = ?, amount = ?, settled = 0",
            (char_id, week, guild, amount, guild, amount))
        self._conn.commit()

    def get_guild_battle_guess(self, char_id: int, week: int):
        return self._conn.execute(
            "SELECT guild, amount, settled FROM guild_battle_guess"
            " WHERE char_id = ? AND week = ?", (char_id, week)).fetchone()

    def get_flag(self, char_id: int, key: str) -> int:
        return self.get_progress(char_id, key)

    def set_flag(self, char_id: int, key: str, value: int) -> None:
        self.set_progress(char_id, key, value)

    def top_survive_scores(self, limit: int = 10):
        """Best survive waves joined with character names."""
        progress = self._conn.execute(
            "SELECT char_id, value FROM progress WHERE key = 'survive_best'"
            " ORDER BY value DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for r in progress:
            row = self._conn.execute(
                "SELECT name FROM characters WHERE id = ?", (r["char_id"],)
            ).fetchone()
            if row is not None:
                out.append({"name": row["name"], "best": r["value"]})
        return out

    # -- cars / mounts ----------------------------------------------------------
    def list_cars(self, char_id: int):
        row = self._conn.execute(
            "SELECT car_id, using_car FROM characters WHERE id = ?", (char_id,)
        ).fetchone()
        return [row] if row and row["car_id"] is not None else []

    def buy_car(self, char_id: int, car_id: int) -> None:
        self._conn.execute(
            "UPDATE characters SET car_id = ? WHERE id = ?", (car_id, char_id))
        self._conn.commit()

    def set_using_car(self, char_id: int, car_id) -> None:
        self._conn.execute(
            "UPDATE characters SET car_id = ?, using_car = ? WHERE id = ?",
            (car_id, car_id if car_id is not None else 0, char_id))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
