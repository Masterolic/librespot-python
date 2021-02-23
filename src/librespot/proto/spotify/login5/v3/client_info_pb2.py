# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: spotify/login5/v3/client_info.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
    name='spotify/login5/v3/client_info.proto',
    package='spotify.login5.v3',
    syntax='proto3',
    serialized_options=b'\n\024com.spotify.login5v3',
    create_key=_descriptor._internal_create_key,
    serialized_pb=
    b'\n#spotify/login5/v3/client_info.proto\x12\x11spotify.login5.v3\"2\n\nClientInfo\x12\x11\n\tclient_id\x18\x01 \x01(\t\x12\x11\n\tdevice_id\x18\x02 \x01(\tB\x16\n\x14\x63om.spotify.login5v3b\x06proto3'
)

_CLIENTINFO = _descriptor.Descriptor(
    name='ClientInfo',
    full_name='spotify.login5.v3.ClientInfo',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name='client_id',
            full_name='spotify.login5.v3.ClientInfo.client_id',
            index=0,
            number=1,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"".decode('utf-8'),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key),
        _descriptor.FieldDescriptor(
            name='device_id',
            full_name='spotify.login5.v3.ClientInfo.device_id',
            index=1,
            number=2,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"".decode('utf-8'),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax='proto3',
    extension_ranges=[],
    oneofs=[],
    serialized_start=58,
    serialized_end=108,
)

DESCRIPTOR.message_types_by_name['ClientInfo'] = _CLIENTINFO
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ClientInfo = _reflection.GeneratedProtocolMessageType(
    'ClientInfo',
    (_message.Message, ),
    {
        'DESCRIPTOR': _CLIENTINFO,
        '__module__': 'spotify.login5.v3.client_info_pb2'
        # @@protoc_insertion_point(class_scope:spotify.login5.v3.ClientInfo)
    })
_sym_db.RegisterMessage(ClientInfo)

DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
