"""Entry point: asyncio TCP server hosting the login gate (9777) and the
game server (9555).

Run with:  python -m server.main
"""

import asyncio
import logging

from . import config
from . import protocol as P
from .db import Database
from .handlers import Handlers
from .session import Session
from .world import World

log = logging.getLogger("atg.main")


class GameServer:
    def __init__(self, advertise_ip: str = None) -> None:
        self.db = Database(config.DB_PATH)
        # fix instances rolled by earlier bugged weapon/armor logic (main
        # attack stored as a "skill", base status stored as a random stat)
        self.db.repair_stale_instances()
        self.world = World()
        self.handlers = Handlers(self)
        env_ip = config.ADVERTISE_IP or advertise_ip
        # default: whatever IP the client used to reach the login gate. The
        # client resolves the game hop itself when the gate advertises the
        # same host it is already talking to.
        self.advertise_ip = env_ip or ""
        self._session_counter = 0

    def next_session(self) -> int:
        self._session_counter += 1
        return self._session_counter

    def next_rng_seed(self) -> int:
        """Seed for the client's PlayerCommonData.InitRandom (sync_common_data
        field 12): any non-zero 32-bit value; feeds the combat hit/miss rolls."""
        import random
        return random.getrandbits(31)

    async def dispatch(self, session: Session, msg) -> None:
        if msg.type is None:
            log.warning("frame without type from %s", session.writer.get_extra_info("peername"))
            return
        handler = self.handlers.map.get(msg.type)
        if handler is None:
            log.info("unhandled protocol tag %s (%s) session=%s",
                     msg.type, P.tag_name(msg.type), msg.session)
            return
        try:
            await handler(session, msg)
        except Exception:
            log.exception("handler error for tag %s", msg.type)

    async def on_disconnect(self, session: Session) -> None:
        wp = session.world_player
        if wp is not None:
            row = self.db.get_character(wp.char_id)
            if row is not None:
                self.db.save_position(
                    wp.char_id, wp.map_id,
                    wp.pos["x"], wp.pos["y"], wp.pos["z"], wp.pos["o"])
            self.world.leave(wp)
            session.world_player = None

    async def _handle_conn(self, reader: asyncio.StreamReader,
                           writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        log.info("connection from %s", peer)
        session = Session(reader, writer, self)
        await session.run()
        log.info("connection closed %s", peer)

    async def start(self) -> None:
        if config.SINGLE_PORT:
            listener = await asyncio.start_server(
                self._handle_conn, config.BIND_HOST, config.SINGLE_PORT_NUM)
            log.info("single-port mode: listening on %s:%d "
                     "(gate + game on one port)",
                     config.BIND_HOST, config.SINGLE_PORT_NUM)
            async with listener:
                await listener.serve_forever()
            return
        gate = await asyncio.start_server(
            self._handle_conn, config.BIND_HOST, config.GATE_PORT)
        game = await asyncio.start_server(
            self._handle_conn, config.BIND_HOST, config.GAME_PORT)
        log.info("gate listening on %s:%d", config.BIND_HOST, config.GATE_PORT)
        log.info("game listening on %s:%d", config.BIND_HOST, config.GAME_PORT)
        async with gate, game:
            await asyncio.gather(gate.serve_forever(), game.serve_forever())


async def amain() -> None:
    server = GameServer()
    await server.start()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        log.info("shutting down")


if __name__ == "__main__":
    main()
