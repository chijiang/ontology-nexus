from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Survey(Base):
    __tablename__ = "surveys"
    id = Column(Integer, primary_key=True, autoincrement=True)
    survey_medium = Column(String)
    language = Column(String)


class TimePeriod(Base):
    __tablename__ = "time_periods"
    id = Column(Integer, primary_key=True, autoincrement=True)
    interview_end = Column(String)
    interview_end_month_ops = Column(String)


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    geo_ops = Column(String)
    px_region = Column(String)
    px_sub_region = Column(String)
    sub_region_1 = Column(String)
    country_name_ops = Column(String)


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, autoincrement=True)
    brand_ops = Column(String)
    product_group_ops = Column(String)
    product_series = Column(String)
    machine_type_4_digital = Column(String)


class SOInformation(Base):
    __tablename__ = "so_informations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    program = Column(String)
    trans_servdelivery = Column(String)
    warranty = Column(String)
    sdf_code = Column(String)
    sdf_description = Column(String)
    comm_channel = Column(String)
    accounting_indicator_adjusted_ops = Column(String)
    service_provider_name_m = Column(String)
    primary_vendor_name_m = Column(String)


class WorkTicket(Base):
    __tablename__ = "work_tickets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    responseid = Column(String, unique=True, index=True)
    osat = Column(Integer)
    why_osat_en_mask = Column(String)
    first_time_resolution = Column(Integer)
    ease_use = Column(Integer)
    kpi_id = Column(String, default="T3B")

    # Foreign Keys
    survey_id = Column(Integer, ForeignKey("surveys.id"))
    time_period_id = Column(Integer, ForeignKey("time_periods.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    so_information_id = Column(Integer, ForeignKey("so_informations.id"))

    # Relationships
    survey = relationship("Survey")
    time_period = relationship("TimePeriod")
    location = relationship("Location")
    product = relationship("Product")
    so_information = relationship("SOInformation")
