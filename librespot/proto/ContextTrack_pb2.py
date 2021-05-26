# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: context_track.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
    name="context_track.proto",
    package="spotify.player.proto",
    syntax="proto2",
    serialized_options=b"\n\023com.spotify.contextH\002",
    create_key=_descriptor._internal_create_key,
    serialized_pb=
    b'\n\x13\x63ontext_track.proto\x12\x14spotify.player.proto"\xaa\x01\n\x0c\x43ontextTrack\x12\x0b\n\x03uri\x18\x01 \x01(\t\x12\x0b\n\x03uid\x18\x02 \x01(\t\x12\x0b\n\x03gid\x18\x03 \x01(\x0c\x12\x42\n\x08metadata\x18\x04 \x03(\x0b\x32\x30.spotify.player.proto.ContextTrack.MetadataEntry\x1a/\n\rMetadataEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t:\x02\x38\x01\x42\x17\n\x13\x63om.spotify.contextH\x02',
)

_CONTEXTTRACK_METADATAENTRY = _descriptor.Descriptor(
    name="MetadataEntry",
    full_name="spotify.player.proto.ContextTrack.MetadataEntry",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name="key",
            full_name="spotify.player.proto.ContextTrack.MetadataEntry.key",
            index=0,
            number=1,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"".decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="value",
            full_name="spotify.player.proto.ContextTrack.MetadataEntry.value",
            index=1,
            number=2,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"".decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[],
    serialized_options=b"8\001",
    is_extendable=False,
    syntax="proto2",
    extension_ranges=[],
    oneofs=[],
    serialized_start=169,
    serialized_end=216,
)

_CONTEXTTRACK = _descriptor.Descriptor(
    name="ContextTrack",
    full_name="spotify.player.proto.ContextTrack",
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name="uri",
            full_name="spotify.player.proto.ContextTrack.uri",
            index=0,
            number=1,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"".decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="uid",
            full_name="spotify.player.proto.ContextTrack.uid",
            index=1,
            number=2,
            type=9,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"".decode("utf-8"),
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="gid",
            full_name="spotify.player.proto.ContextTrack.gid",
            index=2,
            number=3,
            type=12,
            cpp_type=9,
            label=1,
            has_default_value=False,
            default_value=b"",
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
        _descriptor.FieldDescriptor(
            name="metadata",
            full_name="spotify.player.proto.ContextTrack.metadata",
            index=3,
            number=4,
            type=11,
            cpp_type=10,
            label=3,
            has_default_value=False,
            default_value=[],
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key,
        ),
    ],
    extensions=[],
    nested_types=[
        _CONTEXTTRACK_METADATAENTRY,
    ],
    enum_types=[],
    serialized_options=None,
    is_extendable=False,
    syntax="proto2",
    extension_ranges=[],
    oneofs=[],
    serialized_start=46,
    serialized_end=216,
)

_CONTEXTTRACK_METADATAENTRY.containing_type = _CONTEXTTRACK
_CONTEXTTRACK.fields_by_name[
    "metadata"].message_type = _CONTEXTTRACK_METADATAENTRY
DESCRIPTOR.message_types_by_name["ContextTrack"] = _CONTEXTTRACK
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ContextTrack = _reflection.GeneratedProtocolMessageType(
    "ContextTrack",
    (_message.Message, ),
    {
        "MetadataEntry":
        _reflection.GeneratedProtocolMessageType(
            "MetadataEntry",
            (_message.Message, ),
            {
                "DESCRIPTOR": _CONTEXTTRACK_METADATAENTRY,
                "__module__": "context_track_pb2"
                # @@protoc_insertion_point(class_scope:spotify.player.proto.ContextTrack.MetadataEntry)
            },
        ),
        "DESCRIPTOR":
        _CONTEXTTRACK,
        "__module__":
        "context_track_pb2"
        # @@protoc_insertion_point(class_scope:spotify.player.proto.ContextTrack)
    },
)
_sym_db.RegisterMessage(ContextTrack)
_sym_db.RegisterMessage(ContextTrack.MetadataEntry)

DESCRIPTOR._options = None
_CONTEXTTRACK_METADATAENTRY._options = None
# @@protoc_insertion_point(module_scope)
