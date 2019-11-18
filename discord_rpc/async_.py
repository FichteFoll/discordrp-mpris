# References:
# * https://github.com/discordapp/discord-rpc/tree/master/documentation/hard-mode.md
# * https://github.com/discordapp/discord-rpc/tree/master/src
# * https://discordapp.com/developers/docs/rich-presence/how-to#updating-presence-update-presence-payload-fields
# * https://github.com/devsnek/discord-rpc/tree/master/src/transports/IPC.js
# * https://github.com/devsnek/discord-rpc/tree/master/example/main.js

from abc import ABCMeta, abstractmethod
import asyncio
from functools import wraps
import json
import logging
import os
import sys
import struct
from typing import cast, Any, Dict, Tuple
import uuid


OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
OP_PING = 3
OP_PONG = 4

JSON = Dict[str, Any]
Reply = Tuple[int, JSON]

logger = logging.getLogger(__name__)

# commonly thrown exceptions when connection is lost
exceptions = (ConnectionResetError, BrokenPipeError)
try:
    exceptions += (asyncio.streams.IncompleteReadError,)
except AttributeError:
    pass


class DiscordRpcError(Exception):
    pass


class AsyncDiscordRpc(metaclass=ABCMeta):

    """Work with an open Discord instance via its JSON IPC for its rich presence.

    In a blocking way.
    Classmethod `for_platform`
    will resolve to UnixAsyncDiscordIpc.
    Windows hasn't been implemented.

    Supports asynchronous context handler protocol.
    """

    def __init__(self, client_id: str, *,
                 loop: asyncio.AbstractEventLoop = None) -> None:
        self.client_id = client_id
        self.loop = loop

    @property
    @abstractmethod
    def connected(self):
        pass

    async def connect(self):
        await self._connect()
        await self._do_handshake()
        # logger.debug("connected via ID %s", self.client_id)

    @classmethod
    def for_platform(cls, client_id: str, platform=sys.platform, *,
                     loop: asyncio.AbstractEventLoop = None,
                     ) -> 'AsyncDiscordRpc':
        if platform == 'win32':
            return NotImplemented  # async is a pain for windows pipes
        else:
            return UnixAsyncDiscordRpc(client_id)

    @abstractmethod
    async def _connect(self) -> None:
        pass

    async def _do_handshake(self) -> None:
        while True:
            ret_op, ret_data = await self.send_recv({'v': 1, 'client_id': self.client_id},
                                                    op=OP_HANDSHAKE)
            # {'cmd': 'DISPATCH', 'data': {'v': 1, 'config': {...}}, 'evt': 'READY', 'nonce': None}
            if ret_op == OP_FRAME and ret_data['cmd'] == 'DISPATCH' and ret_data['evt'] == 'READY':
                return
            else:
                # No idea when or why this occurs; just try again.
                if ret_data == {'message': "Cannot read property 'id' of undefined"}:
                    await asyncio.sleep(0.3)
                    continue
                if ret_op == OP_CLOSE:
                    await self.close()
                raise RuntimeError(ret_data)

    @abstractmethod
    async def _write(self, date: bytes):
        pass

    @abstractmethod
    async def _recv(self, size: int) -> bytes:
        pass

    async def _recv_header(self) -> Tuple[int, int]:
        header = await self._recv_exactly(8)
        return cast(Tuple[int, int], struct.unpack("<II", header))

    async def _recv_exactly(self, size: int) -> bytes:
        buf = b""
        size_remaining = size
        while size_remaining:
            chunk = await self._recv(size_remaining)
            chunk_size = len(chunk)
            if chunk_size == 0:
                raise EOFError()
            buf += chunk
            size_remaining -= chunk_size
        return buf

    async def close(self) -> None:
        if not self.connected:
            return
        logger.warning("closing connection")
        try:
            await self.send({}, op=OP_CLOSE)
        finally:
            await self._close()

    @abstractmethod
    async def _close(self) -> None:
        pass

    async def __aenter__(self) -> 'AsyncDiscordRpc':
        return self

    async def __aexit__(self, *_) -> None:
        if self.connected:
            await self.close()

    async def send_recv(self, data: JSON, *, op=OP_FRAME) -> Reply:
        nonce = data.get('nonce')
        await self.send(data, op=op)
        while True:
            reply = await self.recv()
            if reply[1].get('nonce') == nonce:
                return reply
            else:
                logger.warning("received unexpected reply; %s", reply)

    async def send(self, data: JSON, *, op=OP_FRAME) -> None:
        logger.debug("sending %s", data)
        data_str = json.dumps(data, separators=(',', ':'))
        data_bytes = data_str.encode('utf-8')
        header = struct.pack("<II", op, len(data_bytes))
        await self._write(header)
        await self._write(data_bytes)

    async def recv(self) -> Reply:
        """Receives a packet from discord.

        Returns op code and payload.
        """
        op, length = await self._recv_header()
        payload = await self._recv_exactly(length)
        data = json.loads(payload.decode('utf-8'))
        logger.debug("received %s", data)
        return op, data

    async def set_activity(self, act: JSON) -> Reply:
        data = {
            'cmd': 'SET_ACTIVITY',
            'args': {'pid': os.getpid(),
                     'activity': act},
            'nonce': str(uuid.uuid4())
        }
        return await self.send_recv(data)

    async def clear_activity(self) -> Reply:
        data = {
            'cmd': 'SET_ACTIVITY',
            'args': {'pid': os.getpid()},
            'nonce': str(uuid.uuid4())
        }
        return await self.send_recv(data)


class UnixAsyncDiscordRpc(AsyncDiscordRpc):

    reader = None
    writer = None

    @property
    def connected(self):
        return self.reader and not self.reader.at_eof()

    async def _connect(self) -> None:
        pipe_pattern = self._get_pipe_pattern()
        for i in range(10):
            path = pipe_pattern.format(i)
            if not os.path.exists(path):
                continue
            try:
                self.reader, self.writer = \
                    await asyncio.open_unix_connection(path, loop=self.loop)
            except OSError as e:
                logger.error("failed to open {!r}: {}".format(path, e))
            else:
                break
        else:
            raise DiscordRpcError("Failed to connect to a Discord pipe")

    @staticmethod
    def _get_pipe_pattern() -> str:
        env_keys = ('XDG_RUNTIME_DIR', 'TMPDIR', 'TMP', 'TEMP')
        for env_key in env_keys:
            dir_path = os.environ.get(env_key)
            if dir_path:
                break
        else:
            dir_path = '/tmp'
        return os.path.join(dir_path, 'discord-ipc-{}')

    def _disconnect_on_error(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except exceptions:
                self.reader.feed_eof()
                raise
        return wrapper

    @_disconnect_on_error
    async def _write(self, data: bytes) -> None:
        self.writer.write(data)
        # await self.writer.drain()  # exception will be caught in _recv_exactly

    @_disconnect_on_error
    async def _recv(self, size: int) -> bytes:
        return await self.reader.read(size)

    @_disconnect_on_error
    async def _recv_exactly(self, size: int) -> bytes:
        return await self.reader.readexactly(size)

    async def _close(self) -> None:
        self.reader.feed_eof()
        self.writer.write_eof()
        await self.writer.drain()
