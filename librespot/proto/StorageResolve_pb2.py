# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: storage-resolve.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor.FileDescriptor(
    name='storage-resolve.proto',
    package='spotify.download.proto',
    syntax='proto3',
    serialized_options=b'\n\023com.spotify.storageH\002',
    create_key=_descriptor._internal_create_key,
    serialized_pb=b'\n\x15storage-resolve.proto\x12\x16spotify.download.proto\"\xaf\x01\n\x16StorageResolveResponse\x12\x45\n\x06result\x18\x01 \x01(\x0e\x32\x35.spotify.download.proto.StorageResolveResponse.Result\x12\x0e\n\x06\x63\x64nurl\x18\x02 \x03(\t\x12\x0e\n\x06\x66ileid\x18\x04 \x01(\x0c\".\n\x06Result\x12\x07\n\x03\x43\x44N\x10\x00\x12\x0b\n\x07STORAGE\x10\x01\x12\x0e\n\nRESTRICTED\x10\x03\x42\x17\n\x13\x63om.spotify.storageH\x02\x62\x06proto3'
)

_STORAGERESOLVERESPONSE_RESULT = _descriptor.EnumDescriptor(
    name='Result',
    full_name='spotify.download.proto.StorageResolveResponse.Result',
    filename=None,
    file=DESCRIPTOR,
    create_key=_descriptor._internal_create_key,
    values=[
        _descriptor.EnumValueDescriptor(
            name='CDN',
            index=0,
            number=0,
            serialized_options=None,
            type=None,
            create_key=_descriptor._internal_create_key),
        _descriptor.EnumValueDescriptor(
            name='STORAGE',
            index=1,
            number=1,
            serialized_options=None,
            type=None,
            create_key=_descriptor._internal_create_key),
        _descriptor.EnumValueDescriptor(
            name='RESTRICTED',
            index=2,
            number=3,
            serialized_options=None,
            type=None,
            create_key=_descriptor._internal_create_key),
    ],
    containing_type=None,
    serialized_options=None,
    serialized_start=179,
    serialized_end=225,
)
_sym_db.RegisterEnumDescriptor(_STORAGERESOLVERESPONSE_RESULT)

_STORAGERESOLVERESPONSE = _descriptor.Descriptor(
    name='StorageResolveResponse',
    full_name='spotify.download.proto.StorageResolveResponse',
    filename=None,
    file=DESCRIPTOR,
    containing_type=None,
    create_key=_descriptor._internal_create_key,
    fields=[
        _descriptor.FieldDescriptor(
            name='result',
            full_name='spotify.download.proto.StorageResolveResponse.result',
            index=0,
            number=1,
            type=14,
            cpp_type=8,
            label=1,
            has_default_value=False,
            default_value=0,
            message_type=None,
            enum_type=None,
            containing_type=None,
            is_extension=False,
            extension_scope=None,
            serialized_options=None,
            file=DESCRIPTOR,
            create_key=_descriptor._internal_create_key),
        _descriptor.FieldDescriptor(
            name='cdnurl',
            full_name='spotify.download.proto.StorageResolveResponse.cdnurl',
            index=1,
            number=2,
            type=9,
            cpp_type=9,
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
            create_key=_descriptor._internal_create_key),
        _descriptor.FieldDescriptor(
            name='fileid',
            full_name='spotify.download.proto.StorageResolveResponse.fileid',
            index=2,
            number=4,
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
            create_key=_descriptor._internal_create_key),
    ],
    extensions=[],
    nested_types=[],
    enum_types=[
        _STORAGERESOLVERESPONSE_RESULT,
    ],
    serialized_options=None,
    is_extendable=False,
    syntax='proto3',
    extension_ranges=[],
    oneofs=[],
    serialized_start=50,
    serialized_end=225,
)

_STORAGERESOLVERESPONSE.fields_by_name[
    'result'].enum_type = _STORAGERESOLVERESPONSE_RESULT
_STORAGERESOLVERESPONSE_RESULT.containing_type = _STORAGERESOLVERESPONSE
DESCRIPTOR.message_types_by_name[
    'StorageResolveResponse'] = _STORAGERESOLVERESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

StorageResolveResponse = _reflection.GeneratedProtocolMessageType(
    'StorageResolveResponse',
    (_message.Message, ),
    {
        'DESCRIPTOR': _STORAGERESOLVERESPONSE,
        '__module__': 'storage_resolve_pb2'
        # @@protoc_insertion_point(class_scope:spotify.download.proto.StorageResolveResponse)
    })
_sym_db.RegisterMessage(StorageResolveResponse)

DESCRIPTOR._options = None
# @@protoc_insertion_point(module_scope)
