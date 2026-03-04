import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SOInformation(_message.Message):
    __slots__ = ("id", "program", "trans_servdelivery", "warranty", "sdf_code", "sdf_description", "comm_channel", "accounting_indicator_adjusted_ops", "service_provider_name_m", "primary_vendor_name_m")
    ID_FIELD_NUMBER: _ClassVar[int]
    PROGRAM_FIELD_NUMBER: _ClassVar[int]
    TRANS_SERVDELIVERY_FIELD_NUMBER: _ClassVar[int]
    WARRANTY_FIELD_NUMBER: _ClassVar[int]
    SDF_CODE_FIELD_NUMBER: _ClassVar[int]
    SDF_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    COMM_CHANNEL_FIELD_NUMBER: _ClassVar[int]
    ACCOUNTING_INDICATOR_ADJUSTED_OPS_FIELD_NUMBER: _ClassVar[int]
    SERVICE_PROVIDER_NAME_M_FIELD_NUMBER: _ClassVar[int]
    PRIMARY_VENDOR_NAME_M_FIELD_NUMBER: _ClassVar[int]
    id: int
    program: str
    trans_servdelivery: str
    warranty: str
    sdf_code: str
    sdf_description: str
    comm_channel: str
    accounting_indicator_adjusted_ops: str
    service_provider_name_m: str
    primary_vendor_name_m: str
    def __init__(self, id: _Optional[int] = ..., program: _Optional[str] = ..., trans_servdelivery: _Optional[str] = ..., warranty: _Optional[str] = ..., sdf_code: _Optional[str] = ..., sdf_description: _Optional[str] = ..., comm_channel: _Optional[str] = ..., accounting_indicator_adjusted_ops: _Optional[str] = ..., service_provider_name_m: _Optional[str] = ..., primary_vendor_name_m: _Optional[str] = ...) -> None: ...

class GetSOInformationRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class ListSOInformationsRequest(_message.Message):
    __slots__ = ("query", "pagination")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    query: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, query: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListSOInformationsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[SOInformation]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[SOInformation, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...
