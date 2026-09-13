"""Extended handlers: copy scenes (dungeons), rank PvP ladder, tower climb,
slot machine, map/line/teleport helpers and misc client progress tags.

Implemented from the decompiled client's real tag flow (see
research/notes/protocol_tags.json):

* copy scenes:  enter_copy_scene(107) -> npc_create pushes + count_down(553)
                single_copy_scene_npc_die(127) -> next_wave(515) ... ->
                copy result rewards
* rank pvp:     request_random_rank_pvp_opponent(133) -> rank_pvp_start(547)
                -> rank_pvp_player_attack(136) / rank_pvp_other_player_die(137)
                -> tiantti_result(551), syn_rank_pvp_data(541),
                top list(134/543), win-count rewards(157)
* tower:        request/enter_tower_copy_info(202/204) -> continue(205) ->
                grant_tower_reward(203), tower_reset(230), wipe_out(208)
* slot machine: request_slot_info(242) -> spin_slot(243) ->
                request_slot_sum_reward(244)

Field layouts without surviving SprotoType classes are provisional, as
documented in research/server/README.md.
"""

import logging
import time

from . import economy
from . import protocol as P
from . import sproto
from . import world as W
from .session import Session

log = logging.getLogger("atg.handlers.pvp")


class PvpHandlersMixin:
    """Mixin added onto Handlers; uses self.server, self._require_char."""

    # ------------------------------------------------------------------
    # copy scenes / dungeons (wave-based PvE instances)
    # ------------------------------------------------------------------
    def _copy_state(self, s: Session):
        return getattr(s, "copy_scene", None)

    async def h_enter_copy_scene(self, s: Session, msg) -> None:
        """enter_copy_scene {copy_id(0)} -> spawn wave 1 + countdown.

        The client runs the fight; the server tracks wave progress and pays
        per-kill exp/gold on single_copy_scene_npc_die.
        """
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        copy_id = msg.body.get(0)
        cdef = economy.COPY_SCENES.get(copy_id)
        if cdef is None:
            s.respond(msg, {0: 2})   # unknown copy scene
            return
        s.copy_scene = {
            "copy_id": copy_id,
            "wave": 0,
            "waves": cdef["waves"],
            "reward": cdef["reward"],
            "npc_ids": [],
        }
        s.respond(msg, {0: 0})
        await self._push_copy_wave(s)
        s.push(P.COUNT_DOWN, {0: cdef["countdown"]})
        log.info("char %s entered copy scene %s", row["name"], copy_id)

    async def _push_copy_wave(self, s: Session) -> None:
        """Spawn the next wave's NPCs as npc_create pushes."""
        state = self._copy_state(s)
        if state is None or state["wave"] >= len(state["waves"]):
            return
        kinds = state["waves"][state["wave"]]
        state["npc_ids"] = []
        for kind in kinds:
            npc = W.WorldNpc(kind, "copy_%d" % state["copy_id"],
                             {"x": 400, "y": 0, "z": 400, "o": 0})
            state["npc_ids"].append(npc.npc_id)
            self.server.world.npcs.setdefault(npc.map_id, {})[npc.npc_id] = npc
            s.push(P.NPC_CREATE, {0: npc.blob()})
        state["wave"] += 1

    async def h_single_copy_scene_npc_die(self, s: Session, msg) -> None:
        """Client-confirmed NPC kill inside a copy scene (tag 127).

        body {npc_id(0)}; pays half the open-world kill payout per kill and
        advances to the next wave when the current one is cleared.
        """
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        npc_id = msg.body.get(0)
        state = self._copy_state(s)
        if state is None or npc_id not in state["npc_ids"]:
            s.respond(msg, {0: 2})
            return
        state["npc_ids"].remove(npc_id)
        db = self.server.db
        kind_def = economy.NPC_KINDS.get(1, {})
        db.add_currency(char_id, economy.CURRENCY_GOLD,
                        kind_def.get("gold", 80) // 2)
        exp = kind_def.get("exp", 40) // 2
        level, exp_left = db.add_exp(char_id, exp)
        hp, max_hp = db.get_hp(char_id)
        s.respond(msg, {0: 0})
        s.push(P.AOI_UPDATE_ATTRIBUTE, {0: P.encode_aoi_update_attribute(
            char_id, hp, exp_left, level, max_hp,
            db.get_currency(char_id, economy.CURRENCY_GOLD),
            db.get_currency(char_id, economy.CURRENCY_DIAMOND),
            cash=db.get_currency(char_id, economy.CURRENCY_CASH))})
        self._sync_backpack(s, char_id)
        # wave cleared -> push the next one (or finish)
        if not state["npc_ids"]:
            if state["wave"] < len(state["waves"]):
                s.push(P.NEXT_WAVE, {0: state["wave"] + 1})
                await self._push_copy_wave(s)
            else:
                best = db.get_progress(char_id,
                                       "copy_best_%d" % state["copy_id"])
                if best < len(state["waves"]):
                    db.set_progress(char_id,
                                    "copy_best_%d" % state["copy_id"],
                                    len(state["waves"]))
                await self._grant_copy_reward(s, state["reward"])
                s.copy_scene = None

    async def h_leave_copy_scene(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        s.copy_scene = None
        s.respond(msg, {0: 0})

    async def h_ask_copyscenes_info(self, s: Session, msg) -> None:
        """sync_copyscenes_info: per copy {copy_id(0), best_wave(1), done(2)}."""
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        db = self.server.db
        blobs = []
        for copy_id, cdef in economy.COPY_SCENES.items():
            best = db.get_progress(row["id"], "copy_best_%d" % copy_id)
            blobs.append(sproto.encode_object({
                0: copy_id,
                1: best,
                2: 1 if best >= len(cdef["waves"]) else 0,
            }))
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    async def _grant_copy_reward(self, s: Session, reward: dict) -> None:
        """Shared payout for a cleared dungeon."""
        row = self._require_char(s)
        if row is None:
            return
        char_id = row["id"]
        db = self.server.db
        if reward.get("gold"):
            db.add_currency(char_id, economy.CURRENCY_GOLD, reward["gold"])
        if reward.get("diamond"):
            db.add_currency(char_id, economy.CURRENCY_DIAMOND,
                            reward["diamond"])
        for item_id, cnt in reward.get("items", {}).items():
            db.add_item(char_id, item_id, cnt)
        if reward.get("exp"):
            db.add_exp(char_id, reward["exp"])
        stacks = [P.encode_item_stack(int(k), v)
                  for k, v in reward.get("items", {}).items()]
        s.push(P.SHOW_REWARD_ITEMS_TIPS, {
            0: reward.get("gold", 0),
            1: reward.get("diamond", 0),
            2: sproto.encode_object_array(stacks),
        })
        self._sync_backpack(s, char_id)

    # ------------------------------------------------------------------
    # map/line helpers (multi-line maps + teleport points)
    # ------------------------------------------------------------------
    async def h_enter_new_map(self, s: Session, msg) -> None:
        """enter_new_map {map_id(0)} — switch maps without a full relogin."""
        wp = s.world_player
        row = self._require_char(s)
        if wp is None or row is None:
            s.respond(msg, {0: 1})
            return
        map_id = str(msg.body.get(0, economy.MAIN_CITY_MAP))
        old_map = wp.map_id
        self.server.world.leave(wp)
        wp.map_id = map_id
        self.server.db.save_position(row["id"], map_id, wp.pos["x"],
                                     wp.pos["y"], wp.pos["z"], wp.pos["o"])
        self.server.world.join(wp)
        s.respond(msg, {0: 0})
        for other in self.server.world.others(map_id, wp.char_id):
            s.push(P.AOI_ADD, {0: W.encode_aoi_add(other)})
        for npc in self.server.world.npcs_in(map_id):
            s.push(P.NPC_CREATE, {0: npc.blob()})
        self.server.world.broadcast(map_id, P.AOI_ADD,
                                    {0: W.encode_aoi_add(wp)},
                                    exclude=wp.char_id)
        log.info("%s moved map %s -> %s", row["name"], old_map, map_id)

    async def h_change_scene_line(self, s: Session, msg) -> None:
        """change_scene_line {line(0)} — switch map line (channel)."""
        wp = s.world_player
        row = self._require_char(s)
        if wp is None or row is None:
            s.respond(msg, {0: 1})
            return
        new_line = msg.body.get(0, 0)
        old_line = wp.line_index
        self.server.world.leave(wp)
        wp.line_index = new_line
        self.server.world.join(wp)
        s.respond(msg, {0: 0})
        for other in self.server.world.others(wp.map_id, wp.char_id):
            s.push(P.AOI_ADD, {0: W.encode_aoi_add(other)})
        self.server.world.broadcast(wp.map_id, P.AOI_ADD,
                                    {0: W.encode_aoi_add(wp)},
                                    exclude=wp.char_id)
        log.info("%s changed line %s -> %s", row["name"], old_line, new_line)

    async def h_request_line_state(self, s: Session, msg) -> None:
        """update_line_state: player counts per line of the requested map."""
        map_id = str(msg.body.get(0, economy.MAIN_CITY_MAP))
        counts = [0, 0, 0]
        for p in self.server.world.maps.get(map_id, {}).values():
            idx = p.line_index if p.line_index < 3 else 2
            counts[idx] += 1
        s.respond(msg, {0: sproto.encode_integer_array(counts)})

    async def h_enter_teleport_point(self, s: Session, msg) -> None:
        """enter_teleport_point — send the player back to the home map."""
        wp = s.world_player
        row = self._require_char(s)
        if wp is None or row is None:
            s.respond(msg, {0: 1})
            return
        old_map = wp.map_id
        self.server.world.leave(wp)
        wp.map_id = economy.MAIN_CITY_MAP
        self.server.db.save_position(row["id"], "1", 0, 0, 0, 0)
        self.server.world.join(wp)
        s.respond(msg, {0: 0})
        for other in self.server.world.others("1", wp.char_id):
            s.push(P.AOI_ADD, {0: W.encode_aoi_add(other)})
        for npc in self.server.world.npcs_in("1"):
            s.push(P.NPC_CREATE, {0: npc.blob()})
        self.server.world.broadcast("1", P.AOI_ADD,
                                    {0: W.encode_aoi_add(wp)},
                                    exclude=wp.char_id)
        log.info("%s teleported %s -> 1", row["name"], old_map)

    async def h_update_player_map_info(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        map_id = str(msg.body.get(0, economy.MAIN_CITY_MAP))
        line = msg.body.get(1, 0)
        s.respond(msg, {0: map_id, 1: line})

    # ------------------------------------------------------------------
    # rank pvp (tianTi ladder)
    # ------------------------------------------------------------------
    def _pvp_score(self, char_id: int) -> int:
        return self.server.db.get_progress(
            char_id, "pvp_score") or economy.RANK_PVP["base_score"]

    async def h_request_random_rank_pvp_opponent(self, s: Session,
                                                 msg) -> None:
        """Match the player against a synthetic opponent near their score.

        The decompiled client flow (request_random_rank_pvp_opponent ->
        rank_pvp_start -> rank_pvp_player_attack ->
        rank_pvp_other_player_die -> tiantti_result) is preserved; the
        opponent is server-simulated.
        """
        import random as _random
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        my_score = self._pvp_score(char_id)
        opp_score = max(800, my_score + _random.randint(-100, 100))
        opp_attack = 8 + _random.randint(0, 10)
        opp_hp = 100 + _random.randint(0, 50)
        s.pvp_battle = {
            "opp_name": "Rival%d" % _random.randrange(1000, 9999),
            "opp_score": opp_score,
            "opp_attack": opp_attack,
            "opp_hp": opp_hp,
            "opp_max_hp": opp_hp,
            "my_hp": db.get_hp(char_id)[0] or economy.PLAYER_BASE_HP,
        }
        s.respond(msg, {0: s.pvp_battle["opp_name"],
                        1: opp_score,
                        2: opp_hp})
        # the real client waits for rank_pvp_start before the fight begins
        s.push(P.RANK_PVP_START, {
            0: s.pvp_battle["opp_name"],
            1: opp_attack,
            2: opp_hp,
        })
        log.info("char %s matched vs %s (score %d)", row["name"],
                 s.pvp_battle["opp_name"], opp_score)

    async def h_rank_pvp_player_attack(self, s: Session, msg) -> None:
        """rank_pvp_player_attack {damage(0)} — resolve the ladder fight."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        battle = getattr(s, "pvp_battle", None)
        if battle is None:
            s.respond(msg, {0: 2})
            return
        damage = msg.body.get(0, 0)
        battle["opp_hp"] = max(0, battle["opp_hp"] - damage)
        s.respond(msg, {0: 0, 1: battle["opp_hp"]})
        if battle["opp_hp"] > 0:
            # opponent fights back
            battle["my_hp"] = max(0, battle["my_hp"] - battle["opp_attack"])
            if battle["my_hp"] > 0:
                return
        # battle over -> resolve the ladder
        win = battle["opp_hp"] <= 0
        delta = economy.RANK_PVP["win_score"] if win \
            else economy.RANK_PVP["lose_score"]
        new_score = max(0, self._pvp_score(char_id) + delta)
        db.set_progress(char_id, "pvp_score", new_score)
        wins = db.get_progress(char_id, "pvp_wins") + (1 if win else 0)
        db.set_progress(char_id, "pvp_wins", wins)
        db.set_progress(char_id, "pvp_battles",
                        db.get_progress(char_id, "pvp_battles") + 1)
        if win:
            db.add_currency(char_id, economy.CURRENCY_GOLD,
                            economy.RANK_PVP["win_gold"])
            db.add_currency(char_id, economy.CURRENCY_DIAMOND,
                            economy.RANK_PVP["win_diamond"])
            s.push(P.RANK_PVP_REWARD, {
                0: economy.RANK_PVP["win_gold"],
                1: economy.RANK_PVP["win_diamond"],
            })
        # record history {result(0), opp_name(1), score(2)}
        db.append_pvp_history(char_id, sproto.encode_object({
            0: 1 if win else 0,
            1: battle["opp_name"],
            2: new_score,
        }))
        s.push(P.TIANTTI_RESULT, {0: 1 if win else 0,
                                  1: new_score,
                                  2: delta})
        s.pvp_battle = None
        log.info("char %s %s pvp (score %d)", row["name"],
                 "won" if win else "lost", new_score)

    async def h_rank_pvp_other_player_die(self, s: Session, msg) -> None:
        """rank_pvp_other_player_die: opponent killed -> force win resolution."""
        battle = getattr(s, "pvp_battle", None)
        if battle is not None:
            battle["opp_hp"] = 0
        await self.h_rank_pvp_player_attack(s, msg)

    async def h_request_rank_pvp_data(self, s: Session, msg) -> None:
        """syn_rank_pvp_data {score(0), wins(1), battles(2)}."""
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        s.respond(msg, {0: self._pvp_score(char_id),
                        1: self.server.db.get_progress(char_id, "pvp_wins"),
                        2: self.server.db.get_progress(char_id, "pvp_battles")})

    async def h_request_rank_pvp_history(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        rows = self.server.db.list_pvp_history(row["id"])
        blobs = [bytes(r["blob"]) for r in rows]
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    async def h_request_top_rank_pvp_list(self, s: Session, msg) -> None:
        """ret_request_top_rank_pvp_list: top {name(0), score(1)} entries."""
        rows = self.server.db.top_pvp_scores(10)
        blobs = [sproto.encode_object({0: r["name"], 1: r["score"]})
                 for r in rows]
        s.respond(msg, {0: sproto.encode_object_array(blobs)})

    async def h_request_top_rank_list(self, s: Session, msg) -> None:
        """request_top_rank_list(191) -> ret_top_rank_list(598).

        Client sends {sortType(0): i}; we answer with the top characters
        sorted by level as sort_item entries (id/score/name/profession).
        """
        db = self.server.db
        sort_type = msg.body.get(0, 0)
        rows = db._conn.execute(
            "SELECT id, name, level, profession FROM characters "
            "ORDER BY level DESC, exp DESC LIMIT 10"
        ).fetchall()
        blobs = [sproto.encode_object({
            0: r["id"],
            1: r["level"],
            2: r["name"],
            3: r["profession"],
            4: str(r["level"]),
        }) for r in rows]
        s.respond(msg, {0: sproto.encode_object_array(blobs),
                        1: sort_type})

    async def h_request_special_big_pack(self, s: Session, msg) -> None:
        """request_special_big_pack(274) -> ret_special_big_pack(656).

        No shop bundles are active on this server: answer with an empty
        special_big_pack map so the client's purchase UI can open instead
        of hanging.
        """
        s.respond(msg, {0: sproto.encode_object_array([])})

    async def h_tianti_rewards(self, s: Session, msg) -> None:
        """tianti_req_win_count_rewards — pay per 5 cumulative wins."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        wins = db.get_progress(char_id, "pvp_wins")
        claimed = db.get_progress(char_id, "pvp_reward_claimed")
        claimable = (wins // 5) - claimed
        if claimable <= 0:
            s.respond(msg, {0: 2, 1: 0})
            return
        gold = claimable * economy.RANK_PVP["win_count_reward"]
        db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        db.set_progress(char_id, "pvp_reward_claimed", wins // 5)
        s.respond(msg, {0: 0, 1: gold})
        s.push(P.SHOW_REWARD_ITEMS_TIPS,
               {0: gold, 1: 0, 2: sproto.encode_object_array([])})

    # ------------------------------------------------------------------
    # tower (endless climb)
    # ------------------------------------------------------------------
    async def h_request_tower_info(self, s: Session, msg) -> None:
        """ret_request_tower_copy_info {floor(0), max_floor(1)}."""
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        floor = self.server.db.get_progress(row["id"], "tower_floor")
        s.respond(msg, {0: floor,
                        1: economy.TOWER["max_floor"]})

    async def h_continue_tower_copy(self, s: Session, msg) -> None:
        """Enter (or continue) the tower: spawn the current floor's NPC."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        floor = db.get_progress(row["id"], "tower_floor") + 1
        if floor > economy.TOWER["max_floor"]:
            s.respond(msg, {0: 2})
            return
        db.set_progress(row["id"], "tower_floor", floor)
        kind = 1 if floor < 20 else (2 if floor < 50 else 3)
        npc = W.WorldNpc(kind, "tower", {"x": 500, "y": 0, "z": 500, "o": 0})
        npc.max_hp += floor * 10
        npc.hp = npc.max_hp
        self.server.world.npcs.setdefault("tower", {})[npc.npc_id] = npc
        s.tower_npc_id = npc.npc_id
        s.respond(msg, {0: 0, 1: floor})
        s.push(P.NPC_CREATE, {0: npc.blob()})
        log.info("char %s entered tower floor %d", row["name"], floor)

    async def h_grant_tower_reward(self, s: Session, msg) -> None:
        """grant_tower_reward — pay per-floor rewards for unclaimed floors."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        floor = db.get_progress(char_id, "tower_floor")
        paid = db.get_progress(char_id, "tower_paid_floor")
        floors = floor - paid
        if floors <= 0:
            s.respond(msg, {0: 2})
            return
        gold = floors * economy.TOWER["gold_per_floor"]
        exp = floors * economy.TOWER["exp_per_floor"]
        db.add_currency(char_id, economy.CURRENCY_GOLD, gold)
        db.add_exp(char_id, exp)
        db.set_progress(char_id, "tower_paid_floor", floor)
        s.respond(msg, {0: 0, 1: gold})
        s.push(P.SHOW_REWARD_ITEMS_TIPS,
               {0: gold, 1: 0, 2: sproto.encode_object_array([])})

    async def h_tower_reset(self, s: Session, msg) -> None:
        """tower_reset — spend diamonds to start over from floor 1."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        cost = economy.TOWER["reset_diamond_cost"]
        if db.get_currency(char_id, economy.CURRENCY_DIAMOND) < cost:
            s.respond(msg, {0: 2})
            return
        db.add_currency(char_id, economy.CURRENCY_DIAMOND, -cost)
        db.set_progress(char_id, "tower_floor", 0)
        db.set_progress(char_id, "tower_paid_floor", 0)
        s.respond(msg, {0: 0})

    async def h_tower_wipe_out(self, s: Session, msg) -> None:
        """tower_wipe_out — instantly clear the current floor (paid feature)."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        floor = db.get_progress(char_id, "tower_floor") + 1
        if floor > economy.TOWER["max_floor"]:
            s.respond(msg, {0: 2})
            return
        db.set_progress(char_id, "tower_floor", floor)
        s.respond(msg, {0: 0, 1: floor})

    # ------------------------------------------------------------------
    # slot machine
    # ------------------------------------------------------------------
    async def h_request_slot_info(self, s: Session, msg) -> None:
        """ret_slot_info {cost(0), sum_pool(1)}."""
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        s.respond(msg, {0: economy.SLOT["spin_cost"],
                        1: self.server.db.get_progress(row["id"],
                                                       "slot_pool")})

    async def h_spin_slot(self, s: Session, msg) -> None:
        """spin_slot — deduct the cost, roll 3 reels, push ret_spin_slot."""
        import random as _random
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        cost = economy.SLOT["spin_cost"]
        if db.get_currency(char_id, economy.CURRENCY_GOLD) < cost:
            s.respond(msg, {0: 2})
            return
        db.add_currency(char_id, economy.CURRENCY_GOLD, -cost)
        reels = [_random.randrange(economy.SLOT["reels"]) for _ in range(3)]
        payout = 0
        if reels[0] == reels[1] == reels[2]:
            payout = cost * economy.SLOT["triple_multiplier"]
        elif reels[0] == reels[1] or reels[1] == reels[2] \
                or reels[0] == reels[2]:
            payout = cost * economy.SLOT["pair_multiplier"]
        if payout:
            db.add_currency(char_id, economy.CURRENCY_GOLD, payout)
        # 10% of losses accrue to the sum-reward pool
        pool = db.get_progress(char_id, "slot_pool") \
            + max(0, cost - payout) // 10
        db.set_progress(char_id, "slot_pool", pool)
        s.respond(msg, {0: sproto.encode_integer_array(reels), 1: payout})

    async def h_request_slot_sum_reward(self, s: Session, msg) -> None:
        """Claim the accumulated slot pool (ret_slot_sum_reward {pool(0)})."""
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        char_id = row["id"]
        pool = db.get_progress(char_id, "slot_pool")
        if pool <= 0:
            s.respond(msg, {0: 2})
            return
        db.add_currency(char_id, economy.CURRENCY_GOLD, pool)
        db.set_progress(char_id, "slot_pool", 0)
        s.respond(msg, {0: pool})

    # ------------------------------------------------------------------
    # misc client progress
    # ------------------------------------------------------------------
    async def h_noop(self, s: Session, msg) -> None:
        s.respond(msg, {})

    async def h_tutorial_finish(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        self.server.db.set_progress(row["id"], "tutorial_done", 1)
        s.respond(msg, {0: 0})

    async def h_unlock_function_complete(self, s: Session, msg) -> None:
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        # request {ID(0) string, state(1) int} — the id is the FUNCTION_TYPE
        # value as text (see encode_function_info)
        func_id = sproto.as_str(msg.body.get(0, ""))
        state = msg.body.get(1, 1)
        self.server.db.set_progress(row["id"],
                                    "unlock_func_%s" % func_id, state)
        s.respond(msg, {0: 0})

    async def h_re_name(self, s: Session, msg) -> None:
        db = self.server.db
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        new_name = sproto.as_str(msg.body.get(0, ""))
        if not new_name:
            s.respond(msg, {0: 2})
            return
        try:
            db._conn.execute(
                "UPDATE characters SET name = ? WHERE id = ?",
                (new_name, row["id"]))
            db._conn.commit()
            s.respond(msg, {0: 0})
        except Exception:
            s.respond(msg, {0: 3})   # name taken

    async def h_change_show_type(self, s: Session, msg) -> None:
        # change_show_type(223): {showType(0)} — the wardrobe Show/Hide
        # toggle. Persist it (survives relogin) and broadcast the visual
        # change so the model updates without a relog.
        row = self._require_char(s)
        if row is None:
            s.respond(msg, {0: 1})
            return
        show_type = 1 if msg.body.get(0, 0) else 0
        self.server.db.set_progress(row["id"], "show_type", show_type)
        s.respond(msg, {0: 0})
        self._sync_show_type(s, row["id"], show_type)

    async def h_impact_npc(self, s: Session, msg) -> None:
        """Client-side NPC interaction impact (dialog trigger); mirror it."""
        wp = s.world_player
        if wp is None:
            return
        self.server.world.broadcast(wp.map_id, P.IMPACT_NPC,
                                    dict(msg.body), exclude=wp.char_id)
        s.respond(msg, {})
