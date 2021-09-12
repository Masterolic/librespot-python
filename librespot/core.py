from __future__ import annotations
from Cryptodome import Random
from Cryptodome.Hash import HMAC, SHA1
from Cryptodome.PublicKey import RSA
from Cryptodome.Signature import PKCS1_v1_5
from librespot import util
from librespot.audio import AudioKeyManager, CdnManager, PlayableContentFeeder
from librespot.audio.storage import ChannelManager
from librespot.cache import CacheManager
from librespot.crypto import CipherPair, DiffieHellman, Packet
from librespot.mercury import MercuryClient, MercuryRequests, RawMercuryRequest
from librespot.metadata import AlbumId, ArtistId, EpisodeId, ShowId, TrackId
from librespot.proto import Authentication_pb2 as Authentication, Connect_pb2 as Connect, Keyexchange_pb2 as Keyexchange, Metadata_pb2 as Metadata
from librespot.structure import Closeable, SubListener
from librespot.version import Version
import base64
import concurrent.futures
import defusedxml.ElementTree
import enum
import io
import json
import logging
import os
import random
import requests
import sched
import signal
import socket
import struct
import threading
import time
import typing


class ApiClient(Closeable):
    logger = logging.getLogger("Librespot:ApiClient")
    __base_url: str
    __session: Session

    def __init__(self, session: Session):
        self.__session = session
        self.__base_url = "https://{}".format(ApResolver.get_random_spclient())

    def build_request(self, method: str, suffix: str, headers: typing.Union[None, typing.Dict[str, str]],
                      body: typing.Union[None, bytes]) -> requests.PreparedRequest:
        request = requests.PreparedRequest()
        request.method = method
        request.data = body
        request.headers = {}
        if headers is not None:
            request.headers = headers
        request.headers["Authorization"] = "Bearer {}".format(self.__session.tokens().get("playlist-read"))
        request.url = self.__base_url + suffix
        return request

    def send(self, method: str, suffix: str, headers: typing.Union[None, typing.Dict[str, str]],
        body: typing.Union[None, bytes]) -> requests.Response:
        response = self.__session.client().send(self.build_request(method, suffix, headers, body))
        return response

    def put_connect_state(self, connection_id: str, proto: Connect.PutStateRequest) -> None:
        response = self.send(
            "PUT", "/connect-state/v1/devices/{}".format(self.__session.device_id()),
            {"Content-Type": "application/protobuf", "X-Spotify-Connection-Id": connection_id},
            proto.SerializeToString(),
        )
        if response.status_code == 413:
            self.logger.warning("PUT state payload is too large: {} bytes uncompressed.".format(len(proto.SerializeToString())))
        elif response.status_code != 200:
            self.logger.warning("PUT state returned {}. headers: {}".format(response.status_code, response.headers))

    def get_metadata_4_track(self, track: TrackId) -> Metadata.Track:
        response = self.send("GET", "/metadata/4/track/{}".format(track.hex_id()), None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise RuntimeError()
        proto = Metadata.Track()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_episode(self, episode: EpisodeId) -> Metadata.Episode:
        response = self.send("GET", "/metadata/4/episode/{}".format(episode.hex_id()), None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Episode()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_album(self, album: AlbumId) -> Metadata.Album:
        response = self.send("GET", "/metadata/4/album/{}".format(album.hex_id()), None, None)
        ApiClient.StatusCodeException.check_status(response)

        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Album()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_artist(self, artist: ArtistId) -> Metadata.Artist:
        response = self.send("GET", "/metadata/4/artist/{}".format(artist.hex_id()), None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Artist()
        proto.ParseFromString(body)
        return proto

    def get_metadata_4_show(self, show: ShowId) -> Metadata.Show:
        response = self.send("GET", "/metadata/4/show/{}".format(show.hex_id()), None, None)
        ApiClient.StatusCodeException.check_status(response)
        body = response.content
        if body is None:
            raise IOError()
        proto = Metadata.Show()
        proto.ParseFromString(body)
        return proto

    class StatusCodeException(IOError):
        code: int

        def __init__(self, response: requests.Response):
            super().__init__(response.status_code)
            self.code = response.status_code

        @staticmethod
        def check_status(response: requests.Response) -> None:
            if response.status_code != 200:
                raise ApiClient.StatusCodeException(response)


class ApResolver:
    base_url = "https://apresolve.spotify.com/"

    @staticmethod
    def request(service_type: str) -> typing.Any:
        """
        Gets the specified ApResolve
        Args:
            service_type: Unique ID for service name
        Returns:
            The resulting object will be returned
        """
        response = requests.get("{}?type={}".format(ApResolver.base_url, service_type))
        return response.json()

    @staticmethod
    def get_random_of(service_type: str) -> str:
        """
        Gets the specified random ApResolve url
        Args:
            service_type: Unique ID for service name
        Returns:
            A random ApResolve url will be returned
        """
        pool = ApResolver.request(service_type)
        urls = pool.get(service_type)
        if urls is None or len(urls) == 0:
            raise RuntimeError("No ApResolve url available")
        return random.choice(urls)

    @staticmethod
    def get_random_dealer() -> str:
        """
        Get dealer endpoint url
        Returns:
            dealer endpoint url
        """
        return ApResolver.get_random_of("dealer")

    @staticmethod
    def get_random_spclient() -> str:
        """
        Get spclient endpoint url
        Returns:
            spclient endpoint url
        """
        return ApResolver.get_random_of("spclient")

    @staticmethod
    def get_random_accesspoint() -> str:
        """
        Get accesspoint endpoint url
        Returns:
            accesspoint endpoint url
        """
        return ApResolver.get_random_of("accesspoint")


class EventService(Closeable):
    logger = logging.getLogger("Librespot:EventService")
    __session: Session
    __worker = concurrent.futures.ThreadPoolExecutor()

    def __init__(self, session: Session):
        self.__session = session

    def __worker_callback(self, event_builder: EventBuilder):
        try:
            body = event_builder.to_array()
            resp = self.__session.mercury().send_sync(
                RawMercuryRequest.Builder().set_uri("hm://event-service/v1/events")
                    .set_method("POST").add_user_field("Accept-Language", "en")
                    .add_user_field("X-ClientTimeStamp", int(time.time() * 1000)).add_payload_part(body).build())
            self.logger.debug("Event sent. body: {}, result: {}".format(body, resp.status_code))
        except IOError as ex:
            self.logger.error("Failed sending event: {} {}".format(event_builder, ex))

    def send_event(self, event_or_builder: typing.Union[GenericEvent, EventBuilder]):
        if type(event_or_builder) is EventService.GenericEvent:
            builder = event_or_builder.build()
        elif type(event_or_builder) is EventService.EventBuilder:
            builder = event_or_builder
        else:
            raise TypeError()
        self.__worker.submit(lambda: self.__worker_callback(builder))

    def language(self, lang: str):
        event = EventService.EventBuilder(EventService.Type.LANGUAGE)
        event.append(s=lang)

    def close(self):
        self.__worker.shutdown()

    class Type(enum.Enum):
        LANGUAGE = ("812", 1)
        FETCHED_FILE_ID = ("274", 3)
        NEW_SESSION_ID = ("557", 3)
        NEW_PLAYBACK_ID = ("558", 1)
        TRACK_PLAYED = ("372", 1)
        TRACK_TRANSITION = ("12", 37)
        CDN_REQUEST = ("10", 20)

        eventId: str
        unknown: str

        def __init__(self, event_id: str, unknown: str):
            self.eventId = event_id
            self.unknown = unknown

    class GenericEvent:
        def build(self) -> EventService.EventBuilder:
            raise NotImplementedError

    class EventBuilder:
        body = io.BytesIO()

        def __init__(self, event_type: EventService.Type):
            self.append_no_delimiter(event_type.value[0])
            self.append(event_type.value[1])

        def append_no_delimiter(self, s: str = None) -> None:
            if s is None:
                s = ""
            self.body.write(s.encode())

        def append(self, c: int = None, s: str = None) -> EventService.EventBuilder:
            if c is None and s is None or c is not None and s is not None:
                raise TypeError()
            if c is not None:
                self.body.write(b"\x09")
                self.body.write(bytes([c]))
                return self
            if s is not None:
                self.body.write(b"\x09")
                self.append_no_delimiter(s)
                return self

        def to_array(self) -> bytes:
            pos = self.body.tell()
            self.body.seek(0)
            data = self.body.read()
            self.body.seek(pos)
            return data


class Session(Closeable, SubListener):
    cipher_pair: typing.Union[CipherPair, None]
    connection: typing.Union[ConnectionHolder, None]
    country_code: str
    logger = logging.getLogger("Librespot:Session")
    scheduled_reconnect: typing.Union[sched.Event, None] = None
    scheduler = sched.scheduler(time.time)
    __api: ApiClient
    __ap_welcome: Authentication.APWelcome
    __audio_key_manager: typing.Union[AudioKeyManager, None]
    __auth_lock = threading.Condition()
    __auth_lock_bool = False
    __cache_manager: typing.Union[CacheManager, None]
    __cdn_manager: typing.Union[CdnManager, None]
    __channel_manager: typing.Union[ChannelManager, None]
    __client: typing.Union[requests.Session, None]
    __closed = False
    __closing = False
    __content_feeder: typing.Union[PlayableContentFeeder, None]
    __event_service: typing.Union[EventService, None]
    __keys: DiffieHellman
    __mercury_client: MercuryClient
    __receiver: typing.Union[Receiver, None]
    __server_key = b"\xac\xe0F\x0b\xff\xc20\xaf\xf4k\xfe\xc3\xbf\xbf\x86=" \
                   b"\xa1\x91\xc6\xcc3l\x93\xa1O\xb3\xb0\x16\x12\xac\xacj" \
                   b"\xf1\x80\xe7\xf6\x14\xd9B\x9d\xbe.4fC\xe3b\xd22z\x1a" \
                   b"\r\x92;\xae\xdd\x14\x02\xb1\x81U\x05a\x04\xd5,\x96\xa4" \
                   b"L\x1e\xcc\x02J\xd4\xb2\x0c\x00\x1f\x17\xed\xc2/\xc45" \
                   b"!\xc8\xf0\xcb\xae\xd2\xad\xd7+\x0f\x9d\xb3\xc52\x1a*" \
                   b"\xfeY\xf3Z\r\xach\xf1\xfab\x1e\xfb,\x8d\x0c\xb79-\x92" \
                   b"G\xe3\xd75\x1am\xbd$\xc2\xae%[\x88\xff\xabs)\x8a\x0b" \
                   b"\xcc\xcd\x0cXg1\x89\xe8\xbd4\x80xJ_\xc9k\x89\x9d\x95k" \
                   b"\xfc\x86\xd7O3\xa6x\x17\x96\xc9\xc3-\r2\xa5\xab\xcd\x05'" \
                   b"\xe2\xf7\x10\xa3\x96\x13\xc4/\x99\xc0'\xbf\xed\x04\x9c" \
                   b"<'X\x04\xb6\xb2\x19\xf9\xc1/\x02\xe9Hc\xec\xa1\xb6B\xa0" \
                   b"\x9dH%\xf8\xb3\x9d\xd0\xe8j\xf9HM\xa1\xc2\xba\x860B\xea" \
                   b"\x9d\xb3\x08l\x19\x0eH\xb3\x9df\xeb\x00\x06\xa2Z\xee\xa1" \
                   b"\x1b\x13\x87<\xd7\x19\xe6U\xbd"
    __token_provider: typing.Union[TokenProvider, None]
    __user_attributes = {}

    def __init__(self, inner: Inner, address: str) -> None:
        signal.signal(signal.SIGINT, lambda _1, _2: self.close())
        signal.signal(signal.SIGTERM, lambda _1, _2: self.close())
        self.__client = Session.create_client(inner.conf)
        self.connection = Session.ConnectionHolder.create(address, None)
        self.__inner = inner
        self.__keys = DiffieHellman()
        self.logger.info("Created new session! device_id: {}, ap: {}".format(inner.device_id, address))

    def api(self) -> ApiClient:
        self.__wait_auth_lock()
        if self.__api is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__api

    def ap_welcome(self):
        self.__wait_auth_lock()
        if self.__ap_welcome is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__ap_welcome

    def audio_key(self) -> AudioKeyManager:
        self.__wait_auth_lock()
        if self.__audio_key_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__audio_key_manager

    def authenticate(self, credential: Authentication.LoginCredentials) -> None:
        """
        Log in to Spotify
        Args:
            credential: Spotify account login information
        """
        self.__authenticate_partial(credential, False)
        with self.__auth_lock:
            self.__mercury_client = MercuryClient(self)
            self.__token_provider = TokenProvider(self)
            self.__audio_key_manager = AudioKeyManager(self)
            self.__channel_manager = ChannelManager(self)
            self.__api = ApiClient(self)
            self.__cdn_manager = CdnManager(self)
            self.__content_feeder = PlayableContentFeeder(self)
            self.__cache_manager = CacheManager(self)
            self.__event_service = EventService(self)
            self.__auth_lock_bool = False
            self.__auth_lock.notify_all()
        self.logger.info("Authenticated as {}!".format(self.__ap_welcome.canonical_username))
        self.mercury().interested_in("spotify:user:attributes:update", self)

    def cache(self) -> CacheManager:
        self.__wait_auth_lock()
        if self.__cache_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__cache_manager

    def cdn(self) -> CdnManager:
        self.__wait_auth_lock()
        if self.__cdn_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__cdn_manager

    def channel(self) -> ChannelManager:
        self.__wait_auth_lock()
        if self.__channel_manager is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__channel_manager

    def client(self) -> requests.Session:
        return self.__client

    def close(self) -> None:
        """
        Close instance
        """
        self.logger.info("Closing session. device_id: {}".format(self.__inner.device_id))
        self.__closing = True
        if self.__audio_key_manager is not None:
            self.__audio_key_manager = None
        if self.__channel_manager is not None:
            self.__channel_manager.close()
            self.__channel_manager = None
        if self.__event_service is not None:
            self.__event_service.close()
            self.__event_service = None
        if self.__receiver is not None:
            self.__receiver.stop()
            self.__receiver = None
        if self.__client is not None:
            self.__client.close()
            self.__client = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        with self.__auth_lock:
            self.__ap_welcome = None
            self.cipher_pair = None
            self.__closed = True
        self.logger.info("Closed session. device_id: {}".format(self.__inner.device_id))

    def connect(self) -> None:
        """
        Connect to the Spotify Server
        """
        acc = Session.Accumulator()
        # Send ClientHello
        nonce = Random.get_random_bytes(0x10)
        client_hello_proto = Keyexchange.ClientHello(
            build_info=Version.standard_build_info(),
            client_nonce=nonce,
            cryptosuites_supported=[
                Keyexchange.Cryptosuite.CRYPTO_SUITE_SHANNON
            ],
            login_crypto_hello=Keyexchange.LoginCryptoHelloUnion(
                diffie_hellman=Keyexchange.LoginCryptoDiffieHellmanHello(
                    gc=self.__keys.public_key_bytes(),
                    server_keys_known=1
                ),
            ),
            padding=b"\x1e",
        )
        client_hello_bytes = client_hello_proto.SerializeToString()
        self.connection.write(b"\x00\x04")
        self.connection.write_int(2 + 4 + len(client_hello_bytes))
        self.connection.write(client_hello_bytes)
        self.connection.flush()
        acc.write(b"\x00\x04")
        acc.write_int(2 + 4 + len(client_hello_bytes))
        acc.write(client_hello_bytes)
        # Read APResponseMessage
        ap_response_message_length = self.connection.read_int()
        acc.write_int(ap_response_message_length)
        ap_response_message_bytes = self.connection.read(ap_response_message_length - 4)
        acc.write(ap_response_message_bytes)
        ap_response_message_proto = Keyexchange.APResponseMessage()
        ap_response_message_proto.ParseFromString(ap_response_message_bytes)
        shared_key = util.int_to_bytes(
            self.__keys.compute_shared_key(
                ap_response_message_proto.challenge.login_crypto_challenge.diffie_hellman.gs
            )
        )
        # Check gs_signature
        rsa = RSA.construct((int.from_bytes(self.__server_key, "big"), 65537))
        pkcs1_v1_5 = PKCS1_v1_5.new(rsa)
        sha1 = SHA1.new()
        sha1.update(ap_response_message_proto.challenge.login_crypto_challenge.diffie_hellman.gs)
        if not pkcs1_v1_5.verify(
                sha1, ap_response_message_proto.challenge.login_crypto_challenge.diffie_hellman.gs_signature):
            raise RuntimeError("Failed signature check!")
        # Solve challenge
        buffer = io.BytesIO()
        for i in range(1, 6):
            mac = HMAC.new(shared_key, digestmod=SHA1)
            mac.update(acc.read())
            mac.update(bytes([i]))
            buffer.write(mac.digest())
        buffer.seek(0)
        mac = HMAC.new(buffer.read(20), digestmod=SHA1)
        mac.update(acc.read())
        challenge = mac.digest()
        client_response_plaintext_proto = Keyexchange.ClientResponsePlaintext(
            crypto_response=Keyexchange.CryptoResponseUnion(),
            login_crypto_response=Keyexchange.LoginCryptoResponseUnion(
                diffie_hellman=Keyexchange.LoginCryptoDiffieHellmanResponse(hmac=challenge)
            ),
            pow_response=Keyexchange.PoWResponseUnion(),
        )
        client_response_plaintext_bytes = client_response_plaintext_proto.SerializeToString()
        self.connection.write_int(4 + len(client_response_plaintext_bytes))
        self.connection.write(client_response_plaintext_bytes)
        self.connection.flush()
        try:
            self.connection.set_timeout(1)
            scrap = self.connection.read(4)
            if len(scrap) == 4:
                payload = self.connection.read(struct.unpack(">i", scrap)[0] - 4)
                failed = Keyexchange.APResponseMessage()
                failed.ParseFromString(payload)
                raise RuntimeError(failed)
        except socket.timeout:
            pass
        finally:
            self.connection.set_timeout(0)
        buffer.seek(20)
        with self.__auth_lock:
            self.cipher_pair = CipherPair(buffer.read(32), buffer.read(32))
            self.__auth_lock_bool = True
        self.logger.info("Connection successfully!")

    def content_feeder(self) -> PlayableContentFeeder:
        self.__wait_auth_lock()
        if self.__content_feeder is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__content_feeder

    @staticmethod
    def create_client(conf: Configuration) -> requests.Session:
        client = requests.Session()
        return client

    def device_id(self) -> str:
        return self.__inner.device_id

    def get_user_attribute(self, key: str, fallback: str = None) -> str:
        return self.__user_attributes.get(key) if self.__user_attributes.get(key) is not None else fallback

    def is_valid(self) -> bool:
        if self.__closed:
            return False
        self.__wait_auth_lock()
        return self.__ap_welcome is not None and self.connection is not None

    def mercury(self) -> MercuryClient:
        self.__wait_auth_lock()
        if self.__mercury_client is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__mercury_client

    def parse_product_info(self, data) -> None:
        """
        Parse product information
        Args:
            data: Raw product information
        """
        products = defusedxml.ElementTree.fromstring(data)
        if products is None:
            return
        product = products[0]
        if product is None:
            return
        for i in range(len(product)):
            self.__user_attributes[product[i].tag] = product[i].text
        self.logger.debug("Parsed product info: {}".format(self.__user_attributes))

    def reconnect(self) -> None:
        """
        Reconnect to the Spotify Server
        """
        if self.connection is not None:
            self.connection.close()
            self.__receiver.stop()
        self.connection = Session.ConnectionHolder.create(ApResolver.get_random_accesspoint(), self.__inner.conf)
        self.connect()
        self.__authenticate_partial(
            Authentication.LoginCredentials(
                typ=self.__ap_welcome.reusable_auth_credentials_type,
                username=self.__ap_welcome.canonical_username,
                auth_data=self.__ap_welcome.reusable_auth_credentials,
            ),
            True,
        )
        self.logger.info("Re-authenticated as {}!".format(self.__ap_welcome.canonical_username))

    def reconnecting(self) -> bool:
        return not self.__closing and not self.__closed and self.connection is None

    def send(self, cmd: bytes, payload: bytes):
        """
        Send data to socket using send_unchecked
        Args:
            cmd: Command
            payload: Payload
        """
        if self.__closing and self.connection is None:
            self.logger.debug("Connection was broken while closing.")
            return
        if self.__closed:
            raise RuntimeError("Session is closed!")
        with self.__auth_lock:
            if self.cipher_pair is None or self.__auth_lock_bool:
                self.__auth_lock.wait()
            self.__send_unchecked(cmd, payload)

    def tokens(self) -> TokenProvider:
        self.__wait_auth_lock()
        if self.__token_provider is None:
            raise RuntimeError("Session isn't authenticated!")
        return self.__token_provider

    def __authenticate_partial(self, credential: Authentication.LoginCredentials, remove_lock: bool) -> None:
        """
        Login to Spotify
        Args:
            credential: Spotify account login information
        """
        if self.cipher_pair is None:
            raise RuntimeError("Connection not established!")
        client_response_encrypted_proto = Authentication.ClientResponseEncrypted(
            login_credentials=credential,
            system_info=Authentication.SystemInfo(
                os=Authentication.Os.OS_UNKNOWN,
                cpu_family=Authentication.CpuFamily.CPU_UNKNOWN,
                system_information_string=Version.system_info_string(),
                device_id=self.__inner.device_id,
            ),
            version_string=Version.version_string(),
        )
        self.__send_unchecked(Packet.Type.login, client_response_encrypted_proto.SerializeToString())
        packet = self.cipher_pair.receive_encoded(self.connection)
        if packet.is_cmd(Packet.Type.ap_welcome):
            self.__ap_welcome = Authentication.APWelcome()
            self.__ap_welcome.ParseFromString(packet.payload)
            self.__receiver = Session.Receiver(self)
            bytes0x0f = Random.get_random_bytes(0x14)
            self.__send_unchecked(Packet.Type.unknown_0x0f, bytes0x0f)
            preferred_locale = io.BytesIO()
            preferred_locale.write(b"\x00\x00\x10\x00\x02preferred-locale" + self.__inner.preferred_locale.encode())
            preferred_locale.seek(0)
            self.__send_unchecked(Packet.Type.preferred_locale, preferred_locale.read())
            if remove_lock:
                with self.__auth_lock:
                    self.__auth_lock_bool = False
                    self.__auth_lock.notify_all()
            if self.__inner.conf.store_credentials:
                reusable = self.__ap_welcome.reusable_auth_credentials
                reusable_type = Authentication.AuthenticationType.Name(
                    self.__ap_welcome.reusable_auth_credentials_type)
                if self.__inner.conf.stored_credentials_file is None:
                    raise TypeError("The file path to be saved is not specified")
                with open(self.__inner.conf.stored_credentials_file, "w") as f:
                    json.dump({
                        "username": self.__ap_welcome.canonical_username,
                        "credentials": base64.b64encode(reusable).decode(),
                        "type": reusable_type,
                    }, f)

        elif packet.is_cmd(Packet.Type.auth_failure):
            ap_login_failed = Keyexchange.APLoginFailed()
            ap_login_failed.ParseFromString(packet.payload)
            raise Session.SpotifyAuthenticationException(ap_login_failed)
        else:
            raise RuntimeError("Unknown CMD 0x" + packet.cmd.hex())

    def __send_unchecked(self, cmd: bytes, payload: bytes) -> None:
        self.cipher_pair.send_encoded(self.connection, cmd, payload)

    def __wait_auth_lock(self) -> None:
        if self.__closing and self.connection is None:
            self.logger.debug("Connection was broken while closing.")
            return
        if self.__closed:
            raise RuntimeError("Session is closed!")
        with self.__auth_lock:
            if self.cipher_pair is None or self.__auth_lock_bool:
                self.__auth_lock.wait()

    class AbsBuilder:
        conf = None
        device_id = None
        device_name = "libretto-python"
        device_type = Connect.DeviceType.COMPUTER
        preferred_locale = "en"

        def __init__(self, conf: Session.Configuration = None):
            if conf is None:
                self.conf = Session.Configuration.Builder().build()
            else:
                self.conf = conf

        def set_preferred_locale(self, locale: str) -> Session.AbsBuilder:
            if len(locale) != 2:
                raise TypeError("Invalid locale: {}".format(locale))
            self.preferred_locale = locale
            return self

        def set_device_name(self, device_name: str) -> Session.AbsBuilder:
            self.device_name = device_name
            return self

        def set_device_id(self, device_id: str) -> Session.AbsBuilder:
            if self.device_id is not None and len(device_id) != 40:
                raise TypeError("Device ID must be 40 chars long.")
            self.device_id = device_id
            return self

        def set_device_type(
                self, device_type: Connect.DeviceType) -> Session.AbsBuilder:
            self.device_type = device_type
            return self

    class Accumulator:
        __buffer = io.BytesIO()

        def read(self) -> bytes:
            """
            Read all buffer
            Returns:
                All buffer
            """
            pos = self.__buffer.tell()
            self.__buffer.seek(0)
            data = self.__buffer.read()
            self.__buffer.seek(pos)
            return data

        def write(self, data: bytes) -> None:
            """
            Write data to buffer
            Args:
                data: Bytes to be written
            """
            self.__buffer.write(data)

        def write_int(self, data: int) -> None:
            """
            Write data to buffer
            Args:
                data: Integer to be written
            """
            self.write(struct.pack(">i", data))

        def write_short(self, data: int) -> None:
            """
            Write data to buffer
            Args:
                data: Short integer to be written
            """
            self.write(struct.pack(">h", data))

    class Builder(AbsBuilder):
        login_credentials: Authentication.LoginCredentials = None

        def stored(self):
            """
            TODO: implement function
            """
            pass

        def stored_file(self, stored_credentials: str = None) -> Session.Builder:
            """
            Create credential from stored file
            Args:
                stored_credentials: credential file path
            Returns:
                Builder
            """
            if stored_credentials is None:
                stored_credentials = self.conf.stored_credentials_file
            if os.path.isfile(stored_credentials):
                try:
                    with open(stored_credentials) as f:
                        obj = json.load(f)
                except json.JSONDecodeError:
                    pass
                else:
                    try:
                        self.login_credentials = Authentication.LoginCredentials(
                            typ=Authentication.AuthenticationType.Value(obj["type"]),
                            username=obj["username"],
                            auth_data=base64.b64decode(obj["credentials"]),
                        )
                    except KeyError:
                        pass
            return self

        def user_pass(self, username: str, password: str) -> Session.Builder:
            """
            Create credential from username and password
            Args:
                username: Spotify's account username
                password: Spotify's account password
            Returns:
                Builder
            """
            self.login_credentials = Authentication.LoginCredentials(
                username=username,
                typ=Authentication.AuthenticationType.AUTHENTICATION_USER_PASS,
                auth_data=password.encode(),
            )
            return self

        def create(self) -> Session:
            """
            Create the Session instance
            Returns:
                Session instance
            """
            if self.login_credentials is None:
                raise RuntimeError("You must select an authentication method.")
            session = Session(
                Session.Inner(
                    self.device_type,
                    self.device_name,
                    self.preferred_locale,
                    self.conf,
                    self.device_id,
                ),
                ApResolver.get_random_accesspoint(),
            )
            session.connect()
            session.authenticate(self.login_credentials)
            return session

    class Configuration:
        # Proxy
        # proxyEnabled: bool
        # proxyType: Proxy.Type
        # proxyAddress: str
        # proxyPort: int
        # proxyAuth: bool
        # proxyUsername: str
        # proxyPassword: str

        # Cache
        cache_enabled: bool
        cache_dir: str
        do_cache_clean_up: bool

        # Stored credentials
        store_credentials: bool
        stored_credentials_file: str

        # Fetching
        retry_on_chunk_error: bool

        def __init__(
                self,
                # proxy_enabled: bool,
                # proxy_type: Proxy.Type,
                # proxy_address: str,
                # proxy_port: int,
                # proxy_auth: bool,
                # proxy_username: str,
                # proxy_password: str,
                cache_enabled: bool,
                cache_dir: str,
                do_cache_clean_up: bool,
                store_credentials: bool,
                stored_credentials_file: str,
                retry_on_chunk_error: bool,
        ):
            # self.proxyEnabled = proxy_enabled
            # self.proxyType = proxy_type
            # self.proxyAddress = proxy_address
            # self.proxyPort = proxy_port
            # self.proxyAuth = proxy_auth
            # self.proxyUsername = proxy_username
            # self.proxyPassword = proxy_password
            self.cache_enabled = cache_enabled
            self.cache_dir = cache_dir
            self.do_cache_clean_up = do_cache_clean_up
            self.store_credentials = store_credentials
            self.stored_credentials_file = stored_credentials_file
            self.retry_on_chunk_error = retry_on_chunk_error

        class Builder:
            # Proxy
            # proxyEnabled: bool = False
            # proxyType: Proxy.Type = Proxy.Type.DIRECT
            # proxyAddress: str = None
            # proxyPort: int = None
            # proxyAuth: bool = None
            # proxyUsername: str = None
            # proxyPassword: str = None

            # Cache
            cache_enabled: bool = True
            cache_dir: str = os.path.join(os.getcwd(), "cache")
            do_cache_clean_up: bool = True

            # Stored credentials
            store_credentials: bool = True
            stored_credentials_file: str = os.path.join(os.getcwd(), "credentials.json")

            # Fetching
            retry_on_chunk_error: bool = True

            # def set_proxy_enabled(
            #         self,
            #         proxy_enabled: bool) -> Session.Configuration.Builder:
            #     self.proxyEnabled = proxy_enabled
            #     return self

            # def set_proxy_type(
            #         self,
            #         proxy_type: Proxy.Type) -> Session.Configuration.Builder:
            #     self.proxyType = proxy_type
            #     return self

            # def set_proxy_address(
            #         self, proxy_address: str) -> Session.Configuration.Builder:
            #     self.proxyAddress = proxy_address
            #     return self

            # def set_proxy_auth(
            #         self, proxy_auth: bool) -> Session.Configuration.Builder:
            #     self.proxyAuth = proxy_auth
            #     return self

            # def set_proxy_username(
            #         self,
            #         proxy_username: str) -> Session.Configuration.Builder:
            #     self.proxyUsername = proxy_username
            #     return self

            # def set_proxy_password(
            #         self,
            #         proxy_password: str) -> Session.Configuration.Builder:
            #     self.proxyPassword = proxy_password
            #     return self

            def set_cache_enabled(self, cache_enabled: bool) -> Session.Configuration.Builder:
                """
                Set cache_enabled
                Args:
                    cache_enabled: Cache enabled
                Returns:
                    Builder
                """
                self.cache_enabled = cache_enabled
                return self

            def set_cache_dir(self, cache_dir: str) -> Session.Configuration.Builder:
                """
                Set cache_dir
                Args:
                    cache_dir: Cache directory
                Returns:
                    Builder
                """
                self.cache_dir = cache_dir
                return self

            def set_do_cache_clean_up(self, do_cache_clean_up: bool) -> Session.Configuration.Builder:
                """
                Set do_cache_clean_up
                Args:
                    do_cache_clean_up: Do cache clean up
                Returns:
                    Builder
                """
                self.do_cache_clean_up = do_cache_clean_up
                return self

            def set_store_credentials(self, store_credentials: bool) -> Session.Configuration.Builder:
                """
                Set store_credentials
                Args:
                    store_credentials: Store credentials
                Returns:
                    Builder
                """
                self.store_credentials = store_credentials
                return self

            def set_stored_credential_file(self, stored_credential_file: str) -> Session.Configuration.Builder:
                """
                Set stored_credential_file
                Args:
                    stored_credential_file: Stored credential file
                Returns:
                    Builder
                """
                self.stored_credentials_file = stored_credential_file
                return self

            def set_retry_on_chunk_error(self, retry_on_chunk_error: bool) -> Session.Configuration.Builder:
                """
                Set retry_on_chunk_error
                Args:
                    retry_on_chunk_error: Retry on chunk error
                Returns:
                    Builder
                """
                self.retry_on_chunk_error = retry_on_chunk_error
                return self

            def build(self) -> Session.Configuration:
                """
                Build Configuration instance
                Returns:
                    Session.Configuration
                """
                return Session.Configuration(
                    # self.proxyEnabled,
                    # self.proxyType,
                    # self.proxyAddress,
                    # self.proxyPort,
                    # self.proxyAuth,
                    # self.proxyUsername,
                    # self.proxyPassword,
                    self.cache_enabled,
                    self.cache_dir,
                    self.do_cache_clean_up,
                    self.store_credentials,
                    self.stored_credentials_file,
                    self.retry_on_chunk_error,
                )

    class ConnectionHolder:
        __buffer = io.BytesIO()
        __socket: socket.socket

        def __init__(self, sock: socket.socket):
            self.__socket = sock

        @staticmethod
        def create(address: str, conf) \
                -> Session.ConnectionHolder:
            """
            Create the ConnectionHolder instance
            Args:
                address: Address to connect
                conf: Configuration
            Returns:
                ConnectionHolder instance
            """
            ap_address = address.split(":")[0]
            ap_port = int(address.split(":")[1])
            sock = socket.socket()
            sock.connect((ap_address, ap_port))
            return Session.ConnectionHolder(sock)

        def close(self) -> None:
            """
            Close the connection
            """
            self.__socket.close()

        def flush(self) -> None:
            """
            Flush data to socket
            """
            self.__buffer.seek(0)
            self.__socket.send(self.__buffer.read())
            self.__buffer = io.BytesIO()

        def read(self, length: int) -> bytes:
            """
            Read data from socket
            Args:
                length: Reading length
            Returns:
                Bytes data from socket
            """
            return self.__socket.recv(length)

        def read_int(self) -> int:
            """
            Read integer from socket
            Returns:
                integer from socket
            """
            return struct.unpack(">i", self.read(4))[0]

        def read_short(self) -> int:
            """
            Read short integer from socket
            Returns:
                short integer from socket
            """
            return struct.unpack(">h", self.read(2))[0]

        def set_timeout(self, seconds: float) -> None:
            """
            Set socket's timeout
            Args:
                seconds: Number of seconds until timeout
            """
            self.__socket.settimeout(None if seconds == 0 else seconds)

        def write(self, data: bytes) -> None:
            """
            Write data to buffer
            Args:
                data: Bytes to be written
            """
            self.__buffer.write(data)

        def write_int(self, data: int) -> None:
            """
            Write data to buffer
            Args:
                data: Integer to be written
            """
            self.write(struct.pack(">i", data))

        def write_short(self, data: int) -> None:
            """
            Write data to buffer
            Args:
                data: Short integer to be written
            """
            self.write(struct.pack(">h", data))

    class Inner:
        device_type: Connect.DeviceType = None
        device_name: str
        device_id: str
        conf = None
        preferred_locale: str

        def __init__(
                self,
                device_type: Connect.DeviceType,
                device_name: str,
                preferred_locale: str,
                conf: Session.Configuration,
                device_id: str = None,
        ):
            self.preferred_locale = preferred_locale
            self.conf = conf
            self.device_type = device_type
            self.device_name = device_name
            self.device_id = (device_id if device_id is not None else util.random_hex_string(40))

    class Receiver:
        __session: Session
        __thread: threading.Thread
        __running: bool = True

        def __init__(self, session):
            self.__session = session
            self.__thread = threading.Thread(target=self.run)
            self.__thread.setDaemon(True)
            self.__thread.setName("session-packet-receiver")
            self.__thread.start()

        def stop(self) -> None:
            self.__running = False

        def run(self) -> None:
            """
            Receive Packet thread function
            """
            self.__session.logger.info("Session.Receiver started")
            while self.__running:
                packet: Packet
                cmd: bytes
                try:
                    packet = self.__session.cipher_pair.receive_encoded(self.__session.connection)
                    cmd = Packet.Type.parse(packet.cmd)
                    if cmd is None:
                        self.__session.logger.info(
                            "Skipping unknown command cmd: 0x{}, payload: {}".
                                format(util.bytes_to_hex(packet.cmd), packet.payload))
                        continue
                except RuntimeError as ex:
                    if self.__running:
                        self.__session.logger.fatal("Failed reading packet! {}".format(ex))
                        self.__session.reconnect()
                    break
                if not self.__running:
                    break
                if cmd == Packet.Type.ping:
                    if self.__session.scheduled_reconnect is not None:
                        self.__session.scheduler.cancel(self.__session.scheduled_reconnect)

                    def anonymous():
                        self.__session.logger.warning("Socket timed out. Reconnecting...")
                        self.__session.reconnect()

                    self.__session.scheduled_reconnect = self.__session.scheduler.enter(2 * 60 + 5, 1, anonymous)
                    self.__session.send(Packet.Type.pong, packet.payload)
                elif cmd == Packet.Type.pong_ack:
                    continue
                elif cmd == Packet.Type.country_code:
                    self.__session.country_code = packet.payload.decode()
                    self.__session.logger.info("Received country_code: {}".format(self.__session.country_code))
                elif cmd == Packet.Type.license_version:
                    license_version = io.BytesIO(packet.payload)
                    license_id = struct.unpack(">h", license_version.read(2))[0]
                    if license_id != 0:
                        buffer = license_version.read()
                        self.__session.logger.info(
                            "Received license_version: {}, {}".format(license_id, buffer.decode()))
                    else:
                        self.__session.logger.info("Received license_version: {}".format(license_id))
                elif cmd == Packet.Type.unknown_0x10:
                    self.__session.logger.debug("Received 0x10: {}".format(util.bytes_to_hex(packet.payload)))
                elif cmd in [
                    Packet.Type.mercury_sub, Packet.Type.mercury_unsub,
                    Packet.Type.mercury_event, Packet.Type.mercury_req
                ]:
                    self.__session.mercury().dispatch(packet)
                elif cmd in [Packet.Type.aes_key, Packet.Type.aes_key_error]:
                    self.__session.audio_key().dispatch(packet)
                elif cmd in [
                    Packet.Type.channel_error, Packet.Type.stream_chunk_res
                ]:
                    self.__session.channel().dispatch(packet)
                elif cmd == Packet.Type.product_info:
                    self.__session.parse_product_info(packet.payload)
                else:
                    self.__session.logger.info("Skipping {}".format(util.bytes_to_hex(cmd)))

    class SpotifyAuthenticationException(Exception):
        def __init__(self, login_failed: Keyexchange.APLoginFailed):
            super().__init__(Keyexchange.ErrorCode.Name(login_failed.error_code))


class TokenProvider:
    logger = logging.getLogger("Librespot:TokenProvider")
    token_expire_threshold = 10
    __session: Session
    __tokens: typing.List[StoredToken] = []

    def __init__(self, session: Session):
        self._session = session

    def find_token_with_all_scopes(self, scopes: typing.List[str]) -> typing.Union[StoredToken, None]:
        for token in self.__tokens:
            if token.has_scopes(scopes):
                return token
        return None

    def get(self, scope: str) -> str:
        return self.get_token(scope).access_token

    def get_token(self, *scopes) -> StoredToken:
        scopes = list(scopes)
        if len(scopes) == 0:
            raise RuntimeError("The token doesn't have any scope")
        token = self.find_token_with_all_scopes(scopes)
        if token is not None:
            if token.expired():
                self.__tokens.remove(token)
            else:
                return token
        self.logger.debug(
            "Token expired or not suitable, requesting again. scopes: {}, old_token: {}".format(scopes, token))
        response = self._session.mercury().send_sync_json(
            MercuryRequests.request_token(self._session.device_id(), ",".join(scopes)))
        token = TokenProvider.StoredToken(response)
        self.logger.debug("Updated token successfully! scopes: {}, new_token: {}".format(scopes, token))
        self.__tokens.append(token)
        return token

    class StoredToken:
        expires_in: int
        access_token: str
        scopes: typing.List[str]
        timestamp: int

        def __init__(self, obj):
            self.timestamp = int(time.time_ns() / 1000)
            self.expires_in = obj["expiresIn"]
            self.access_token = obj["accessToken"]
            self.scopes = obj["scope"]

        def expired(self) -> bool:
            return (self.timestamp +
                    (self.expires_in - TokenProvider.token_expire_threshold) * 1000 < int(time.time_ns() / 1000))

        def has_scope(self, scope: str) -> bool:
            for s in self.scopes:
                if s == scope:
                    return True
            return False

        def has_scopes(self, sc: typing.List[str]) -> bool:
            for s in sc:
                if not self.has_scope(s):
                    return False
            return True