
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_temperature: Mapped[float] = mapped_column(Float, nullable=False)
    max_temperature: Mapped[float] = mapped_column(Float, nullable=False)

    shipments: Mapped[list["Shipment"]] = relationship(
        back_populates="product"
    )


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="CREATED", nullable=False
    )
    departure_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    delivery_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    product: Mapped["Product"] = relationship(
        back_populates="shipments"
    )
    containers: Mapped[list["Container"]] = relationship(
        back_populates="shipment"
    )


class Container(Base):
    __tablename__ = "containers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    container_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id"), nullable=False
    )

    shipment: Mapped["Shipment"] = relationship(
        back_populates="containers"
    )
    sensors: Mapped[list["Sensor"]] = relationship(
        back_populates="container"
    )


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    container_id: Mapped[int] = mapped_column(
        ForeignKey("containers.id"), nullable=False
    )
    sensor_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    calibrated: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    container: Mapped["Container"] = relationship(
        back_populates="sensors"
    )
    readings: Mapped[list["SensorReading"]] = relationship(
        back_populates="sensor"
    )


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reading_code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    sensor_id: Mapped[int] = mapped_column(
        ForeignKey("sensors.id"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(
        String(10), nullable=False
    )

    sensor: Mapped["Sensor"] = relationship(
        back_populates="readings"
    )


class Excursion(Base):
    __tablename__ = "excursions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    excursion_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False
    )
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="OPEN", nullable=False
    )
