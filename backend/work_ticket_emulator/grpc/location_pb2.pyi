import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Location(_message.Message):
    __slots__ = ("id", "geo_ops", "px_region", "px_sub_region", "sub_region_1", "country_name_ops")
    ID_FIELD_NUMBER: _ClassVar[int]
    GEO_OPS_FIELD_NUMBER: _ClassVar[int]
    PX_REGION_FIELD_NUMBER: _ClassVar[int]
    PX_SUB_REGION_FIELD_NUMBER: _ClassVar[int]
    SUB_REGION_1_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_NAME_OPS_FIELD_NUMBER: _ClassVar[int]
    id: int
    geo_ops: str
    px_region: str
    px_sub_region: str
    sub_region_1: str
    country_name_ops: str
    def __init__(self, id: _Optional[int] = ..., geo_ops: _Optional[str] = ..., px_region: _Optional[str] = ..., px_sub_region: _Optional[str] = ..., sub_region_1: _Optional[str] = ..., country_name_ops: _Optional[str] = ...) -> None: ...

class GetLocationRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class ListLocationsRequest(_message.Message):
    __slots__ = ("query", "pagination")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    query: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, query: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListLocationsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[Location]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[Location, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...
