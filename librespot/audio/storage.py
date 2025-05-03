from __future__ import annotations
from librespot import util
from librespot.crypto import Packet
from librespot.proto.Metadata_pb2 import AudioFile
from librespot.structure import Closeable, PacketsReceiver
import concurrent.futures
import io
import logging
import queue
import struct
import threading
import time
import typing

if typing.TYPE_CHECKING:
    from librespot.core import Session


class ChannelManager(Closeable, PacketsReceiver):
    channels: typing.Dict[int, Channel] = {}
    chunk_size = 1024 * 1024  # 🔥 Increased chunk size to 512 KB
    executor_service = concurrent.futures.ThreadPoolExecutor()
    logger = logging.getLogger("Librespot:ChannelManager")
    seq_holder = 0
    seq_holder_lock = threading.Condition()
    __session: Session = None

    def __init__(self, session: Session):
        self.__session = session

    def request_chunk(self, file_id: bytes, index: int, file: AudioFile):
        """Request a larger chunk of audio data from Spotify servers."""
        start = int(index * self.chunk_size / 4)
        end = int((index + 8) * self.chunk_size / 4)  # 🔥 Fetch 3 chunks at once

        channel = ChannelManager.Channel(self, file, index)
        self.channels[channel.chunk_id] = channel

        out = io.BytesIO()
        out.write(struct.pack(">H", channel.chunk_id))
        out.write(struct.pack(">i", 0x00000000))
        out.write(struct.pack(">i", 0x00000000))
        out.write(struct.pack(">i", 0x00004E20))
        out.write(struct.pack(">i", 0x00030D40))
        out.write(file_id)
        out.write(struct.pack(">i", start))
        out.write(struct.pack(">i", end))
        out.seek(0)

        self.__session.send(Packet.Type.stream_chunk, out.read())

        time.sleep(0.1)  # 🔥 Increase delay slightly for large chunks (100ms)

    def dispatch(self, packet: Packet) -> None:
        """Handle incoming packets from the Spotify network."""
        payload = io.BytesIO(packet.payload)

        if packet.is_cmd(Packet.Type.stream_chunk_res):
            chunk_id = struct.unpack(">H", payload.read(2))[0]
            channel = self.channels.get(chunk_id)
            if channel is None:
                self.logger.warning(
                    "Couldn't find channel, id: {}, received: {}".format(
                        chunk_id, len(packet.payload)))
                return
            channel.add_to_queue(payload)

        elif packet.is_cmd(Packet.Type.channel_error):
            chunk_id = struct.unpack(">H", payload.read(2))[0]
            channel = self.channels.get(chunk_id)
            if channel is None:
                self.logger.warning(
                    "Dropping channel error, id: {}, code: {}".format(
                        chunk_id,
                        struct.unpack(">H", payload.read(2))[0]))
                return
            channel.stream_error(struct.unpack(">H", payload.read(2))[0])

        else:
            self.logger.warning(
                "Couldn't handle packet, cmd: {}, payload: {}".format(
                    packet.cmd, util.bytes_to_hex(packet.payload)))

    def close(self) -> None:
        """Shutdown the executor service when closing."""
        self.executor_service.shutdown()

    class Channel:
        channel_manager: ChannelManager
        chunk_id: int
        q = queue.Queue()
        __buffer: io.BytesIO
        __chunk_index: int
        __file: AudioFile
        __header: bool = True

        def __init__(self, channel_manager: ChannelManager, file: AudioFile,
                     chunk_index: int):
            self.__buffer = io.BytesIO()
            self.channel_manager = channel_manager
            self.__file = file
            self.__chunk_index = chunk_index
            with self.channel_manager.seq_holder_lock:
                self.chunk_id = self.channel_manager.seq_holder
                self.channel_manager.seq_holder += 1
            self.channel_manager.executor_service.submit(
                lambda: ChannelManager.Channel.Handler(self))

        def _handle(self, payload: bytes) -> bool:
            """Process received chunk data and write it to the buffer."""
            if len(payload) == 0:
                if not self.__header:
                    self.__file.write_chunk(payload, self.__chunk_index, False)
                    return True
                self.channel_manager.logger.debug(
                    "Received empty chunk, skipping.")
                return False

            if self.__header:
                while len(payload.getbuffer()) > 0:  # ✅ Corrected `.buffer` usage
                    length = struct.unpack(">H", payload.read(2))[0]  # ✅ Corrected short read
                    if length <= 0:
                        break
                    header_id = payload.read(1)[0]  # ✅ Read a single byte
                    header_data = payload.read(length - 1)
                    self.__file.write_header(header_id, bytearray(header_data), False)
                self.__header = False
            else:
                self.__buffer.write(payload.read(len(payload.getbuffer())))  # ✅ Corrected buffer handling
            return False

        def add_to_queue(self, payload):
            """Add chunk data to queue for processing."""
            self.q.put(payload)

        def stream_error(self, code: int) -> None:
            """Handle chunk stream errors."""
            self.__file.stream_error(self.__chunk_index, code)

        class Handler:
            """Handles chunk data processing asynchronously."""
            __channel: ChannelManager.Channel = None

            def __init__(self, channel: ChannelManager.Channel):
                self.__channel = channel

            def run(self) -> None:
                """Process data from queue and clean up when finished."""
                self.__channel.channel_manager.logger.debug(
                    "ChannelManager.Handler is starting")
                with self.__channel.q.all_tasks_done:
                    self.__channel.channel_manager.channels.pop(
                        self.__channel.chunk_id)
                self.__channel.channel_manager.logger.debug(
                    "ChannelManager.Handler is shutting down")
