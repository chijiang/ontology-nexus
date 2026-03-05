import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GeoOps(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GEO_OPS_UNSPECIFIED: _ClassVar[GeoOps]
    AP: _ClassVar[GeoOps]
    NA: _ClassVar[GeoOps]
    EMEA: _ClassVar[GeoOps]

class PxRegion(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PX_REGION_UNSPECIFIED: _ClassVar[PxRegion]
    WE: _ClassVar[PxRegion]

class CountryNameOps(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COUNTRY_NAME_OPS_UNSPECIFIED: _ClassVar[CountryNameOps]
    INDIA: _ClassVar[CountryNameOps]
    CANADA: _ClassVar[CountryNameOps]
    FRANCE: _ClassVar[CountryNameOps]

class Program(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PROGRAM_UNSPECIFIED: _ClassVar[Program]
    Standard_Commercial: _ClassVar[Program]
    Premier_Support: _ClassVar[Program]

class TransServdelivery(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TRANS_SERVDELIVERY_UNSPECIFIED: _ClassVar[TransServdelivery]
    ONS: _ClassVar[TransServdelivery]
    CRU: _ClassVar[TransServdelivery]
    CIN: _ClassVar[TransServdelivery]
GEO_OPS_UNSPECIFIED: GeoOps
AP: GeoOps
NA: GeoOps
EMEA: GeoOps
PX_REGION_UNSPECIFIED: PxRegion
WE: PxRegion
COUNTRY_NAME_OPS_UNSPECIFIED: CountryNameOps
INDIA: CountryNameOps
CANADA: CountryNameOps
FRANCE: CountryNameOps
PROGRAM_UNSPECIFIED: Program
Standard_Commercial: Program
Premier_Support: Program
TRANS_SERVDELIVERY_UNSPECIFIED: TransServdelivery
ONS: TransServdelivery
CRU: TransServdelivery
CIN: TransServdelivery

class WorkTicket(_message.Message):
    __slots__ = ("responseid", "osat", "why_osat_en_mask", "first_time_resolution", "ease_use", "survey_id", "time_period_id", "location_id", "product_id", "so_information_id", "kpi_id")
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
    KPI_ID_FIELD_NUMBER: _ClassVar[int]
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
    kpi_id: str
    def __init__(self, responseid: _Optional[str] = ..., osat: _Optional[int] = ..., why_osat_en_mask: _Optional[str] = ..., first_time_resolution: _Optional[int] = ..., ease_use: _Optional[int] = ..., survey_id: _Optional[int] = ..., time_period_id: _Optional[int] = ..., location_id: _Optional[int] = ..., product_id: _Optional[int] = ..., so_information_id: _Optional[int] = ..., kpi_id: _Optional[str] = ...) -> None: ...

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

class KPI(_message.Message):
    __slots__ = ("id", "name", "description")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class ListKPIsRequest(_message.Message):
    __slots__ = ("pagination",)
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    pagination: _common_pb2.PaginationRequest
    def __init__(self, pagination: _Optional[_Union[_common_pb2.PaginationRequest, _Mapping]] = ...) -> None: ...

class ListKPIsResponse(_message.Message):
    __slots__ = ("items", "pagination")
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    PAGINATION_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[KPI]
    pagination: _common_pb2.PaginationResponse
    def __init__(self, items: _Optional[_Iterable[_Union[KPI, _Mapping]]] = ..., pagination: _Optional[_Union[_common_pb2.PaginationResponse, _Mapping]] = ...) -> None: ...

class T3bPipelineRequest(_message.Message):
    __slots__ = ("geo_ops", "px_region", "country_name_ops", "program", "trans_servdelivery", "start_year", "start_month", "end_year", "end_month")
    GEO_OPS_FIELD_NUMBER: _ClassVar[int]
    PX_REGION_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_NAME_OPS_FIELD_NUMBER: _ClassVar[int]
    PROGRAM_FIELD_NUMBER: _ClassVar[int]
    TRANS_SERVDELIVERY_FIELD_NUMBER: _ClassVar[int]
    START_YEAR_FIELD_NUMBER: _ClassVar[int]
    START_MONTH_FIELD_NUMBER: _ClassVar[int]
    END_YEAR_FIELD_NUMBER: _ClassVar[int]
    END_MONTH_FIELD_NUMBER: _ClassVar[int]
    geo_ops: _containers.RepeatedScalarFieldContainer[GeoOps]
    px_region: _containers.RepeatedScalarFieldContainer[PxRegion]
    country_name_ops: _containers.RepeatedScalarFieldContainer[CountryNameOps]
    program: _containers.RepeatedScalarFieldContainer[Program]
    trans_servdelivery: _containers.RepeatedScalarFieldContainer[TransServdelivery]
    start_year: int
    start_month: int
    end_year: int
    end_month: int
    def __init__(self, geo_ops: _Optional[_Iterable[_Union[GeoOps, str]]] = ..., px_region: _Optional[_Iterable[_Union[PxRegion, str]]] = ..., country_name_ops: _Optional[_Iterable[_Union[CountryNameOps, str]]] = ..., program: _Optional[_Iterable[_Union[Program, str]]] = ..., trans_servdelivery: _Optional[_Iterable[_Union[TransServdelivery, str]]] = ..., start_year: _Optional[int] = ..., start_month: _Optional[int] = ..., end_year: _Optional[int] = ..., end_month: _Optional[int] = ...) -> None: ...

class T3bPipelineResponse(_message.Message):
    __slots__ = ("t3b_by_month", "overall_r2", "dim_importance")
    class T3bByMonthEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class DimImportanceEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...
    T3B_BY_MONTH_FIELD_NUMBER: _ClassVar[int]
    OVERALL_R2_FIELD_NUMBER: _ClassVar[int]
    DIM_IMPORTANCE_FIELD_NUMBER: _ClassVar[int]
    t3b_by_month: _containers.ScalarMap[str, str]
    overall_r2: float
    dim_importance: _containers.ScalarMap[str, float]
    def __init__(self, t3b_by_month: _Optional[_Mapping[str, str]] = ..., overall_r2: _Optional[float] = ..., dim_importance: _Optional[_Mapping[str, float]] = ...) -> None: ...
