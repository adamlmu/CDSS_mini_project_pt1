from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app import models, schemas

async def create_patient(db: AsyncSession, data: schemas.PatientCreate) -> models.Patient:
    p = models.Patient(**data.dict())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p

async def create_observation(db: AsyncSession, data: schemas.ObservationCreate) -> models.Observation:
    o = models.Observation(
        patient_id  = data.patient_id,
        loinc_num   = data.loinc_num,
        value_num   = data.value_num,
        valid_start = data.start,
        valid_end   = data.end,
        txn_start   = datetime.utcnow(),
        txn_end     = None
    )
    db.add(o)
    await db.commit()
    await db.refresh(o)
    return o

async def observations_history(
    db: AsyncSession,
    patient_id: int,
    loinc: str,
    since: datetime,
    until: datetime
) -> List[models.Observation]:
    stmt = (
        select(models.Observation)
        .where(models.Observation.patient_id == patient_id)
        .where(models.Observation.loinc_num    == loinc)
        .where(models.Observation.txn_end      == None)
        .where(models.Observation.valid_start <= until)
        .where(or_(
            models.Observation.valid_end == None,
            models.Observation.valid_end >= since
        ))
        .order_by(models.Observation.valid_start)
    )
    return (await db.scalars(stmt)).all()

async def update_observation_value(
    db: AsyncSession,
    obs_id: int,
    new_value: float
) -> Optional[models.Observation]:
    old = await db.get(models.Observation, obs_id)
    if not old:
        return None
    old.txn_end = datetime.utcnow()
    await db.commit()

    new = models.Observation(
        patient_id  = old.patient_id,
        loinc_num   = old.loinc_num,
        value_num   = new_value,
        valid_start = old.valid_start,
        valid_end   = old.valid_end,
        txn_start   = datetime.utcnow(),
        txn_end     = None
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new

async def retroactive_update(
    db: AsyncSession,
    patient_name: str,
    loinc_code: str,
    measured_at: datetime,
    txn_at: datetime,
    new_value: float
) -> List[models.Observation]:
    first, last = patient_name.split(maxsplit=1)
    p = (await db.scalars(
            select(models.Patient)
            .where(and_(models.Patient.first_name==first,
                        models.Patient.last_name ==last))
         )).first()
    if not p: return []

    old = (await db.scalars(
            select(models.Observation)
            .where(models.Observation.patient_id==p.patient_id)
            .where(models.Observation.loinc_num   == loinc_code)
            .where(models.Observation.valid_start == measured_at)
            .order_by(desc(models.Observation.txn_start))
            .limit(1)
    )).first()
    if not old: return []

    old.txn_end = txn_at
    await db.commit()

    new = models.Observation(
        patient_id  = old.patient_id,
        loinc_num   = old.loinc_num,
        value_num   = new_value,
        valid_start = old.valid_start,
        valid_end   = old.valid_end,
        txn_start   = txn_at,
        txn_end     = None
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return [old, new]

async def retroactive_delete(
    db: AsyncSession,
    patient_name: str,
    loinc_code: str,
    delete_at: datetime,
    measured_at: Optional[datetime] = None
) -> List[models.Observation]:
    first, last = patient_name.split(maxsplit=1)
    p = (await db.scalars(
            select(models.Patient)
            .where(and_(models.Patient.first_name==first,
                        models.Patient.last_name ==last))
         )).first()
    if not p: return []

    base = select(models.Observation).where(
        models.Observation.patient_id==p.patient_id,
        models.Observation.loinc_num   == loinc_code,
        models.Observation.txn_end     == None
    )
    if measured_at is not None:
        base = base.where(models.Observation.valid_start == measured_at)
    else:
        day_start = datetime.combine(delete_at.date(), datetime.min.time())
        day_end   = datetime.combine(delete_at.date(), datetime.max.time())
        base = base.where(models.Observation.valid_start.between(day_start,day_end))

    old = (await db.scalars(base.order_by(desc(models.Observation.valid_start)).limit(1))).first()
    if not old: return []

    old.txn_end = delete_at
    await db.commit()
    return [old]

async def get_loinc_name(db: AsyncSession, loinc_code: str) -> Optional[str]:
    lo = (await db.scalars(
            select(models.Loinc).where(models.Loinc.loinc_num==loinc_code)
          )).first()
    return lo.common_name if lo else None
