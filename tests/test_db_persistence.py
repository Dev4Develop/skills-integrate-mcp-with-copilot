import os
import tempfile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys, os
# ensure project root is on sys.path for imports in CI
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.models import Base, Activity, Student, Enrollment


def test_create_activity_and_enroll(tmp_path):
    db_file = tmp_path / "test.db"
    url = f"sqlite:///{db_file}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = Session()
    act = Activity(name="Test Club", description="desc", schedule="now", max_participants=2)
    db.add(act)
    db.commit()
    db.refresh(act)

    s = Student(email="stu@example.com", name="Stu")
    db.add(s)
    db.commit()
    db.refresh(s)

    e = Enrollment(activity_id=act.id, student_id=s.id)
    db.add(e)
    db.commit()

    # reload and assert
    a = db.query(Activity).filter(Activity.name == "Test Club").first()
    assert a is not None
    assert len(a.enrollments) == 1
