"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Activity, Student, Enrollment


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables when starting in development (for now)
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities(db: Session = Depends(get_db)):
    db_activities = db.query(Activity).all()
    result = {}
    for a in db_activities:
        result[a.name] = {
            "description": a.description,
            "schedule": a.schedule,
            "max_participants": a.max_participants,
            "participants": [e.student.email for e in a.enrollments]
        }
    return result


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    # Validate activity exists
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Check if student exists, otherwise create
    student = db.query(Student).filter(Student.email == email).first()
    if not student:
        student = Student(email=email)
        db.add(student)
        db.commit()
        db.refresh(student)

    # Validate not already enrolled
    existing = db.query(Enrollment).filter(Enrollment.activity_id == activity.id, Enrollment.student_id == student.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    # Enforce capacity
    current = db.query(Enrollment).filter(Enrollment.activity_id == activity.id).count()
    if activity.max_participants and current >= activity.max_participants:
        raise HTTPException(status_code=400, detail="Activity is full")

    enrollment = Enrollment(activity_id=activity.id, student_id=student.id)
    db.add(enrollment)
    db.commit()
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str, db: Session = Depends(get_db)):
    activity = db.query(Activity).filter(Activity.name == activity_name).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    student = db.query(Student).filter(Student.email == email).first()
    if not student:
        raise HTTPException(status_code=400, detail="Student not found")

    enrollment = db.query(Enrollment).filter(Enrollment.activity_id == activity.id, Enrollment.student_id == student.id).first()
    if not enrollment:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    db.delete(enrollment)
    db.commit()
    return {"message": f"Unregistered {email} from {activity_name}"}
