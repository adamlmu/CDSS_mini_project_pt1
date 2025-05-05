from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base

class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name  = Column(String, nullable=False)
    gender     = Column(String(1), nullable=False)
    birth_date = Column(Date, nullable=False)

    observations = relationship("Observation", back_populates="patient")


class Observation(Base):
    __tablename__ = "observations"

    obs_id      = Column(Integer, primary_key=True, index=True)
    patient_id  = Column(Integer, ForeignKey("patients.patient_id"), nullable=False, index=True)
    loinc_num   = Column(String, nullable=False, index=True)
    value_num   = Column(Float, nullable=False)
    valid_start = Column(DateTime, nullable=False)
    valid_end   = Column(DateTime, nullable=True)
    txn_start   = Column(DateTime, nullable=False, default=datetime.utcnow)
    txn_end     = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="observations")


class Loinc(Base):
    __tablename__ = "loinc"

    loinc_num   = Column(String, primary_key=True, index=True)
    common_name = Column(String, nullable=False)
