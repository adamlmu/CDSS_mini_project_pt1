from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ObservationBase(BaseModel):
    patient_id: int
    loinc_num: str
    value_num: float
    start: datetime
    end: Optional[datetime] = None

class ObservationCreate(ObservationBase): ...

class ObservationOut(ObservationBase):
    obs_id: int
    class Config:
        orm_mode = True

class PatientBase(BaseModel):
    first_name: str
    last_name: str
    gender: str = Field(pattern=r"^[MF]$")
    birth_date: datetime

class PatientCreate(PatientBase): ...

class PatientOut(PatientBase):
    patient_id: int
    observations: List[ObservationOut] = []
    class Config:
        orm_mode = True
