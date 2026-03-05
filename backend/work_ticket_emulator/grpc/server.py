import asyncio
import logging
from typing import Optional
import math

import grpc
from grpc.aio import ServicerContext
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from grpc_reflection.v1alpha import reflection

from ..database import async_session_maker
from ..models import WorkTicket, Survey, TimePeriod, Location, Product, SOInformation

# Import generated protobuf classes
from . import (
    common_pb2,
    location_pb2,
    location_pb2_grpc,
    product_pb2,
    product_pb2_grpc,
    survey_pb2,
    survey_pb2_grpc,
    time_period_pb2,
    time_period_pb2_grpc,
    so_information_pb2,
    so_information_pb2_grpc,
    work_ticket_pb2,
    work_ticket_pb2_grpc,
)

logger = logging.getLogger(__name__)


def _safe_str(val) -> str:
    if val is None:
        return ""
    return str(val)


def _calc_pagination(
    total: int, page: int, page_size: int
) -> common_pb2.PaginationResponse:
    page = page if page > 0 else 1
    page_size = page_size if page_size > 0 else 20
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    return common_pb2.PaginationResponse(
        total=total, page=page, page_size=page_size, total_pages=total_pages
    )


# --- Survey Servicer ---
class SurveyServicer(survey_pb2_grpc.SurveyServiceServicer):
    async def GetSurvey(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            result = await session.execute(
                select(Survey).where(Survey.id == request.id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Survey not found")
            return survey_pb2.Survey(
                id=obj.id,
                survey_medium=_safe_str(obj.survey_medium),
                language=_safe_str(obj.language),
            )

    async def ListSurveys(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(Survey)
            if request.query:
                q = f"%{request.query}%"
                stmt = stmt.where(
                    or_(Survey.survey_medium.ilike(q), Survey.language.ilike(q))
                )

            total = await session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            objs = (await session.execute(stmt)).scalars().all()

            items = [
                survey_pb2.Survey(
                    id=o.id,
                    survey_medium=_safe_str(o.survey_medium),
                    language=_safe_str(o.language),
                )
                for o in objs
            ]
            return survey_pb2.ListSurveysResponse(
                items=items, pagination=_calc_pagination(total, page, page_size)
            )


# --- TimePeriod Servicer ---
class TimePeriodServicer(time_period_pb2_grpc.TimePeriodServiceServicer):
    async def GetTimePeriod(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            result = await session.execute(
                select(TimePeriod).where(TimePeriod.id == request.id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                await context.abort(grpc.StatusCode.NOT_FOUND, "TimePeriod not found")
            return time_period_pb2.TimePeriod(
                id=obj.id,
                interview_end=_safe_str(obj.interview_end),
                interview_end_month_ops=_safe_str(obj.interview_end_month_ops),
            )

    async def ListTimePeriods(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(TimePeriod)
            if request.query:
                q = f"%{request.query}%"
                stmt = stmt.where(
                    or_(
                        TimePeriod.interview_end.ilike(q),
                        TimePeriod.interview_end_month_ops.ilike(q),
                    )
                )

            total = await session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            objs = (await session.execute(stmt)).scalars().all()

            items = [
                time_period_pb2.TimePeriod(
                    id=o.id,
                    interview_end=_safe_str(o.interview_end),
                    interview_end_month_ops=_safe_str(o.interview_end_month_ops),
                )
                for o in objs
            ]
            return time_period_pb2.ListTimePeriodsResponse(
                items=items, pagination=_calc_pagination(total, page, page_size)
            )


# --- Location Servicer ---
class LocationServicer(location_pb2_grpc.LocationServiceServicer):
    async def GetLocation(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            result = await session.execute(
                select(Location).where(Location.id == request.id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Location not found")
            return location_pb2.Location(
                id=obj.id,
                geo_ops=_safe_str(obj.geo_ops),
                px_region=_safe_str(obj.px_region),
                px_sub_region=_safe_str(obj.px_sub_region),
                sub_region_1=_safe_str(obj.sub_region_1),
                country_name_ops=_safe_str(obj.country_name_ops),
            )

    async def ListLocations(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(Location)
            if request.query:
                q = f"%{request.query}%"
                stmt = stmt.where(
                    or_(
                        Location.country_name_ops.ilike(q),
                        Location.geo_ops.ilike(q),
                        Location.px_region.ilike(q),
                    )
                )

            total = await session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            objs = (await session.execute(stmt)).scalars().all()

            items = [
                location_pb2.Location(
                    id=o.id,
                    geo_ops=_safe_str(o.geo_ops),
                    px_region=_safe_str(o.px_region),
                    px_sub_region=_safe_str(o.px_sub_region),
                    sub_region_1=_safe_str(o.sub_region_1),
                    country_name_ops=_safe_str(o.country_name_ops),
                )
                for o in objs
            ]
            return location_pb2.ListLocationsResponse(
                items=items, pagination=_calc_pagination(total, page, page_size)
            )


# --- Product Servicer ---
class ProductServicer(product_pb2_grpc.ProductServiceServicer):
    async def GetProduct(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            result = await session.execute(
                select(Product).where(Product.id == request.id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Product not found")
            return product_pb2.Product(
                id=obj.id,
                brand_ops=_safe_str(obj.brand_ops),
                product_group_ops=_safe_str(obj.product_group_ops),
                product_series=_safe_str(obj.product_series),
                machine_type_4_digital=_safe_str(obj.machine_type_4_digital),
            )

    async def ListProducts(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(Product)
            if request.query:
                q = f"%{request.query}%"
                stmt = stmt.where(
                    or_(
                        Product.brand_ops.ilike(q),
                        Product.product_group_ops.ilike(q),
                        Product.product_series.ilike(q),
                    )
                )

            total = await session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            objs = (await session.execute(stmt)).scalars().all()

            items = [
                product_pb2.Product(
                    id=o.id,
                    brand_ops=_safe_str(o.brand_ops),
                    product_group_ops=_safe_str(o.product_group_ops),
                    product_series=_safe_str(o.product_series),
                    machine_type_4_digital=_safe_str(o.machine_type_4_digital),
                )
                for o in objs
            ]
            return product_pb2.ListProductsResponse(
                items=items, pagination=_calc_pagination(total, page, page_size)
            )


# --- SOInformation Servicer ---
class SOInformationServicer(so_information_pb2_grpc.SOInformationServiceServicer):
    async def GetSOInformation(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            result = await session.execute(
                select(SOInformation).where(SOInformation.id == request.id)
            )
            obj = result.scalar_one_or_none()
            if not obj:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND, "SOInformation not found"
                )
            return so_information_pb2.SOInformation(
                id=obj.id,
                program=_safe_str(obj.program),
                trans_servdelivery=_safe_str(obj.trans_servdelivery),
                warranty=_safe_str(obj.warranty),
                sdf_code=_safe_str(obj.sdf_code),
                sdf_description=_safe_str(obj.sdf_description),
                comm_channel=_safe_str(obj.comm_channel),
                accounting_indicator_adjusted_ops=_safe_str(
                    obj.accounting_indicator_adjusted_ops
                ),
                service_provider_name_m=_safe_str(obj.service_provider_name_m),
                primary_vendor_name_m=_safe_str(obj.primary_vendor_name_m),
            )

    async def ListSOInformations(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(SOInformation)
            if request.query:
                q = f"%{request.query}%"
                stmt = stmt.where(
                    or_(
                        SOInformation.program.ilike(q),
                        SOInformation.warranty.ilike(q),
                        SOInformation.service_provider_name_m.ilike(q),
                    )
                )

            total = await session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )
            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            objs = (await session.execute(stmt)).scalars().all()

            items = [
                so_information_pb2.SOInformation(
                    id=o.id,
                    program=_safe_str(o.program),
                    trans_servdelivery=_safe_str(o.trans_servdelivery),
                    warranty=_safe_str(o.warranty),
                    sdf_code=_safe_str(o.sdf_code),
                    sdf_description=_safe_str(o.sdf_description),
                    comm_channel=_safe_str(o.comm_channel),
                    accounting_indicator_adjusted_ops=_safe_str(
                        o.accounting_indicator_adjusted_ops
                    ),
                    service_provider_name_m=_safe_str(o.service_provider_name_m),
                    primary_vendor_name_m=_safe_str(o.primary_vendor_name_m),
                )
                for o in objs
            ]
            return so_information_pb2.ListSOInformationsResponse(
                items=items, pagination=_calc_pagination(total, page, page_size)
            )


# --- WorkTicket Servicer ---
class WorkTicketServicer(work_ticket_pb2_grpc.WorkTicketServiceServicer):
    def _model_to_pb(self, model: WorkTicket) -> work_ticket_pb2.WorkTicket:
        return work_ticket_pb2.WorkTicket(
            responseid=_safe_str(model.responseid),
            osat=model.osat or 0,
            why_osat_en_mask=_safe_str(model.why_osat_en_mask),
            first_time_resolution=model.first_time_resolution or 0,
            ease_use=model.ease_use or 0,
            survey_id=model.survey_id or 0,
            time_period_id=model.time_period_id or 0,
            location_id=model.location_id or 0,
            product_id=model.product_id or 0,
            so_information_id=model.so_information_id or 0,
            kpi_id=model.kpi_id or "T3B",
        )

    async def ListKPIs(self, request, context: ServicerContext):
        page = request.pagination.page if request.HasField("pagination") else 1
        page_size = (
            request.pagination.page_size if request.HasField("pagination") else 20
        )
        return work_ticket_pb2.ListKPIsResponse(
            items=[
                work_ticket_pb2.KPI(
                    id="T3B",
                    name="T3B",
                    description="客户评分大于等于8分的比例  (越高越好）",
                )
            ],
            pagination=_calc_pagination(1, page, page_size),
        )

    async def GetWorkTicket(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(WorkTicket).where(WorkTicket.responseid == request.responseid)
            result = await session.execute(stmt)
            ticket = result.scalar_one_or_none()

            if not ticket:
                await context.abort(
                    grpc.StatusCode.NOT_FOUND,
                    f"Work Ticket {request.responseid} not found",
                )

            return self._model_to_pb(ticket)

    async def ListWorkTickets(self, request, context: ServicerContext):
        async with async_session_maker() as session:
            stmt = select(WorkTicket)

            if request.query:
                q = f"%{request.query}%"
                stmt = (
                    stmt.join(WorkTicket.location)
                    .join(WorkTicket.so_information)
                    .where(
                        or_(
                            WorkTicket.responseid.ilike(q),
                            WorkTicket.why_osat_en_mask.ilike(q),
                            Location.country_name_ops.ilike(q),
                            SOInformation.program.ilike(q),
                        )
                    )
                )

            total = await session.scalar(
                select(func.count()).select_from(stmt.subquery())
            )

            page = request.pagination.page if request.HasField("pagination") else 1
            page_size = (
                request.pagination.page_size if request.HasField("pagination") else 20
            )

            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            result = await session.execute(stmt)
            tickets = result.scalars().all()

            pb_tickets = [self._model_to_pb(t) for t in tickets]
            return work_ticket_pb2.ListWorkTicketsResponse(
                items=pb_tickets, pagination=_calc_pagination(total, page, page_size)
            )

    async def CalculateT3bPipeline(self, request, context: ServicerContext):
        from ..t3bCalculator import t3b_pipeline

        conditions = {}

        GEO_OPS_MAP = {
            work_ticket_pb2.AP: "AP",
            work_ticket_pb2.NA: "NA",
            work_ticket_pb2.EMEA: "EMEA",
        }
        PX_REGION_MAP = {
            work_ticket_pb2.WE: "WE",
        }
        COUNTRY_NAME_MAP = {
            work_ticket_pb2.INDIA: "INDIA",
            work_ticket_pb2.CANADA: "CANADA",
            work_ticket_pb2.FRANCE: "FRANCE",
        }
        PROGRAM_MAP = {
            work_ticket_pb2.Standard_Commercial: "Standard Commercial",
            work_ticket_pb2.Premier_Support: "Premier Support",
        }
        TRANS_MAP = {
            work_ticket_pb2.ONS: "ONS",
            work_ticket_pb2.CRU: "CRU",
            work_ticket_pb2.CIN: "CIN",
        }

        if request.geo_ops:
            conditions["geo_ops"] = [
                GEO_OPS_MAP[v] for v in request.geo_ops if v in GEO_OPS_MAP
            ]
        if request.px_region:
            conditions["PX_Region"] = [
                PX_REGION_MAP[v] for v in request.px_region if v in PX_REGION_MAP
            ]
        if request.country_name_ops:
            conditions["country_name_ops"] = [
                COUNTRY_NAME_MAP[v]
                for v in request.country_name_ops
                if v in COUNTRY_NAME_MAP
            ]
        if request.program:
            conditions["program"] = [
                PROGRAM_MAP[v] for v in request.program if v in PROGRAM_MAP
            ]
        if request.trans_servdelivery:
            conditions["trans_servdelivery"] = [
                TRANS_MAP[v] for v in request.trans_servdelivery if v in TRANS_MAP
            ]

        if request.HasField("start_year"):
            conditions["start_year"] = request.start_year
        if request.HasField("start_month"):
            conditions["start_month"] = request.start_month
        if request.HasField("end_year"):
            conditions["end_year"] = request.end_year
        if request.HasField("end_month"):
            conditions["end_month"] = request.end_month

        try:
            df_t3b, r2, dim_importance = await asyncio.to_thread(
                t3b_pipeline, conditions
            )
            return work_ticket_pb2.T3bPipelineResponse(
                t3b_by_month=df_t3b, overall_r2=r2, dim_importance=dim_importance
            )
        except Exception as e:
            logger.error(f"Error in CalculateT3bPipeline: {e}", exc_info=True)
            await context.abort(grpc.StatusCode.INTERNAL, str(e))


async def serve(host="[::]", port="50052"):
    """Start the gRPC server"""
    server = grpc.aio.server()

    # Register all servicers
    work_ticket_pb2_grpc.add_WorkTicketServiceServicer_to_server(
        WorkTicketServicer(), server
    )
    survey_pb2_grpc.add_SurveyServiceServicer_to_server(SurveyServicer(), server)
    time_period_pb2_grpc.add_TimePeriodServiceServicer_to_server(
        TimePeriodServicer(), server
    )
    location_pb2_grpc.add_LocationServiceServicer_to_server(LocationServicer(), server)
    product_pb2_grpc.add_ProductServiceServicer_to_server(ProductServicer(), server)
    so_information_pb2_grpc.add_SOInformationServiceServicer_to_server(
        SOInformationServicer(), server
    )

    service_names = (
        work_ticket_pb2.DESCRIPTOR.services_by_name["WorkTicketService"].full_name,
        survey_pb2.DESCRIPTOR.services_by_name["SurveyService"].full_name,
        time_period_pb2.DESCRIPTOR.services_by_name["TimePeriodService"].full_name,
        location_pb2.DESCRIPTOR.services_by_name["LocationService"].full_name,
        product_pb2.DESCRIPTOR.services_by_name["ProductService"].full_name,
        so_information_pb2.DESCRIPTOR.services_by_name[
            "SOInformationService"
        ].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port(f"{host}:{port}")

    logger.info(
        f"Starting work_ticket_emulator gRPC server (SQLite Multi-Service) on {host}:{port}"
    )
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
