import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TimePeriod(_message.Message):
    __slots__ = ("id", "interview_end", "interview_end_month_ops")
    ID_FIELD_NUMBER: _ClassVar[int]
    INTERVIEW_END_FIELD_NUMBER: _ClassVar[int]
    INTERVIEW_END_MONTH_OPS_FIELD_NUMBER: _ClassVar[int]
    id: int
    interview_end: str
    interview_end_month_ops: str
    def __init__(self, id: _Optional[int] = ..., interview_end: _Optional[str] = ..., interview_end_month_ops: _Optional[str] = ...) -> None: ...

class GetTimePeriodRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class ListTimePeriodsRequest(_message.Message):
    __slots__ = ("query", "pagination")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    query: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, query: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListTimePeriodsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[TimePeriod]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[TimePeriod, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...
