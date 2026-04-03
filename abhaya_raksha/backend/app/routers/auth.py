from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Worker
from ..schemas import WorkerRegister, WorkerLogin, Token, WorkerOut
from ..auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=WorkerOut, status_code=201)
def register(data: WorkerRegister, db: Session = Depends(get_db)):
    if db.query(Worker).filter(Worker.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    worker = Worker(
        name=data.name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        worker_type=data.worker_type,
        city=data.city,
        zone=data.zone,
        lat=data.lat,
        lng=data.lng,
        avg_daily_income=data.avg_daily_income
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker

@router.post("/login", response_model=Token)
def login(data: WorkerLogin, db: Session = Depends(get_db)):
    worker = db.query(Worker).filter(Worker.email == data.email).first()
    if not worker or not verify_password(data.password, worker.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(worker.id)})
    return {"access_token": token, "is_admin": worker.is_admin}
