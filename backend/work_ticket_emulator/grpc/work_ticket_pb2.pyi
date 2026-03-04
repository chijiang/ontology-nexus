import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WorkTicket(_message.Message):
    __slots__ = ("responseid", "osat", "why_osat_en_mask", "first_time_resolution", "ease_use", "survey_id", "time_period_id", "location_id", "product_id", "so_information_id")
    RESPONSEID_FIELD_NUMBER: _ClassVar[int]
    OSAT_FIELD_NUMBER: _ClassVar[int]
    WHY_OSAT_EN_MASK_FIELD_NUMBER: _ClassVar[int]
    FIRST_TIME_RESOLUTION_FIELD_NUMBER: _ClassVar[int]
    EASE_USE_FIELD_NUMBER: _ClassVar[int]
    SURVEY_ID_FIELD_NUMBER: _ClassVar[int]
    TIME_PERIOD_ID_FIELD_NUMBER: _ClassVar[int]
    LOCATION_ID_FIELD_NUMBER: _ClassVar[int]
    PRODUCT_ID_FIELD_NUMBER: _ClassVar[int]
    SO_INFORMATION_ID_FIELD_NUMBER: _ClassVar[int]
    responseid: str
    osat: int
    why_osat_en_mask: str
    first_time_resolution: int
    ease_use: int
    survey_id: int
    time_period_id: int
    location_id: int
    product_id: int
    so_information_id: int
    def __init__(self, responseid: _Optional[str] = ..., osat: _Optional[int] = ..., why_osat_en_mask: _Optional[str] = ..., first_time_resolution: _Optional[int] = ..., ease_use: _Optional[int] = ..., survey_id: _Optional[int] = ..., time_period_id: _Optional[int] = ..., location_id: _Optional[int] = ..., product_id: _Optional[int] = ..., so_information_id: _Optional[int] = ...) -> None: ...

class GetWorkTicketRequest(_message.Message):
    __slots__ = ("responseid",)
    RESPONSEID_FIELD_NUMBER: _ClassVar[int]
    responseid: str
    def __init__(self, responseid: _Optional[str] = ...) -> None: ...

class ListWorkTicketsRequest(_message.Message):
    __slots__ = ("query", "pagination")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    query: str
    pagination: _common_pb2.PaginationRequest
    def __init__(self, query: _Optional[str] = ..., pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListWorkTicketsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[WorkTicket]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[WorkTicket, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...
