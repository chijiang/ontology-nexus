import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Product(_message.Message):
    __slots__ = ("id", "brand_ops", "product_group_ops", "product_series", "machine_type_4_digital")
    ID_FIELD_NUMBER: _ClassVar[int]
    BRAND_OPS_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_GROUP_OPS_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_SERIES_FIELD_NUMBER: _ClassVar[int]
    MACHINE_TYPE_4_DIGITAL_FIELD_NUMBER: _ClassVar[int]
    id: int
    brand_ops: str
    product_group_ops: str
    product_series: str
    machine_type_4_digital: str
    def __init__(self, id: _Optional[int] = ..., brand_ops: _Optional[str] = ..., product_group_ops: _Optional[str] = ..., product_series: _Optional[str] = ..., machine_type_4_digital: _Optional[str] = ...) -> None: ...

class GetProductRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class ListProductsRequest(_message.Message):
    __slots__ = ("query", "pagination")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    query: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, query: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListProductsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[Product]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[Product, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...
