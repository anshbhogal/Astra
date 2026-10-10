"""Student Benchmark Microservice containing Injected Bugs BUG-STUD-001 through BUG-STUD-012."""

import datetime
import sqlite3
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request, Response

from benchmark_apps.base_app import BenchmarkEnvironment, create_benchmark_app

app = create_benchmark_app("Benchmark Student API", version="1.0.0")

# In-memory database setup
_db = sqlite3.connect(":memory:", check_same_thread=False)
_cursor = _db.cursor()
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        dob TEXT,
        roll_number TEXT UNIQUE,
        department TEXT,
        gpa REAL DEFAULT 3.0
    )
""")
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id TEXT PRIMARY KEY,
        title TEXT,
        capacity INTEGER,
        enrolled INTEGER DEFAULT 0,
        prereqs TEXT
    )
""")
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        student_id TEXT,
        course_id TEXT,
        enrolled_at TEXT,
        PRIMARY KEY (student_id, course_id)
    )
""")
_cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_aid (
        student_id TEXT PRIMARY KEY,
        scholarship_amount REAL
    )
""")

# Seed initial records
_cursor.execute("INSERT OR REPLACE INTO students VALUES ('stud_1', 'John', 'Doe', '2001-01-01', 'ROLL-101', 'CS', 3.5)")
_cursor.execute("INSERT OR REPLACE INTO students VALUES ('stud_alice', 'Alice', 'Wonder', '2002-03-15', 'ROLL-102', 'CS', 3.9)")
_cursor.execute("INSERT OR REPLACE INTO students VALUES ('stud_bob', 'Bob', 'Builder', '2002-07-20', 'ROLL-103', 'EE', 3.2)")
_cursor.execute("INSERT OR REPLACE INTO courses VALUES ('cs_101', 'Intro to CS', 30, 30, '')")
_cursor.execute("INSERT OR REPLACE INTO courses VALUES ('cs_401_adv', 'Advanced Distributed Systems', 20, 5, 'cs_101,cs_201')")
_cursor.execute("INSERT OR REPLACE INTO financial_aid VALUES ('stud_alice', 5000.0)")
_cursor.execute("INSERT OR REPLACE INTO financial_aid VALUES ('stud_bob', 1200.0)")
_db.commit()


def reset_student_db():
    _cursor.execute("DELETE FROM students WHERE id NOT IN ('stud_1', 'stud_alice', 'stud_bob')")
    _cursor.execute("UPDATE courses SET enrolled = 30 WHERE id = 'cs_101'")
    _cursor.execute("UPDATE courses SET enrolled = 5 WHERE id = 'cs_401_adv'")
    _cursor.execute("DELETE FROM enrollments")
    _db.commit()


@app.get("/api/v1/student/health")
async def health():
    return {"status": "HEALTHY", "service": "student"}


@app.get("/api/v1/students")
async def list_students():
    _cursor.execute("SELECT id, first_name, last_name, roll_number, department, gpa FROM students")
    rows = _cursor.fetchall()
    return [{"id": r[0], "first_name": r[1], "last_name": r[2], "roll_number": r[3], "department": r[4], "gpa": r[5]} for r in rows]


@app.post("/api/v1/students", status_code=201)
async def create_student(request: Request):
    payload = await request.json()
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    dob_str = payload.get("dob", "2000-01-01")
    roll = payload.get("roll_number", f"ROLL-{uuid.uuid4().hex[:6]}")
    dept = payload.get("department", "CS")

    # BUG-STUD-001: Accepts future DOB (e.g. 2035)
    if not BenchmarkEnvironment.is_bug_active("BUG-STUD-001"):
        try:
            parsed_dob = datetime.date.fromisoformat(dob_str)
            if parsed_dob > datetime.date.today():
                raise HTTPException(status_code=422, detail="Date of birth cannot be in the future")
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format")

    # BUG-STUD-008: Stored XSS accepted
    if not BenchmarkEnvironment.is_bug_active("BUG-STUD-008"):
        if "<script>" in first_name or "<script>" in last_name:
            raise HTTPException(status_code=422, detail="Invalid characters in name")

    new_id = f"stud_{uuid.uuid4().hex[:6]}"

    # BUG-STUD-003: Duplicate roll number raises unhandled 500 SQLite error instead of 409
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-003"):
        _cursor.execute("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?)", (new_id, first_name, last_name, dob_str, roll, dept, 3.0))
        _db.commit()
    else:
        _cursor.execute("SELECT id FROM students WHERE roll_number = ?", (roll,))
        if _cursor.fetchone():
            raise HTTPException(status_code=409, detail="Roll number already registered")
        _cursor.execute("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?, ?)", (new_id, first_name, last_name, dob_str, roll, dept, 3.0))
        _db.commit()

    return {"status": 201, "student_id": new_id, "first_name": first_name}


@app.put("/api/v1/students/{student_id}/gpa")
async def update_gpa(student_id: str, request: Request):
    payload = await request.json()
    gpa = payload.get("gpa", 3.0)

    # BUG-STUD-002: Accepts GPA 5.5 (standard 0.0 to 4.0)
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-002"):
        _cursor.execute("UPDATE students SET gpa = ? WHERE id = ?", (gpa, student_id))
        _db.commit()
        return {"status": 200, "gpa": gpa}
    else:
        if gpa < 0.0 or gpa > 4.0:
            raise HTTPException(status_code=422, detail="GPA must be between 0.0 and 4.0")
        _cursor.execute("UPDATE students SET gpa = ? WHERE id = ?", (gpa, student_id))
        _db.commit()
        return {"status": 200, "gpa": gpa}


@app.post("/api/v1/courses/{course_id}/enroll")
async def enroll_course(course_id: str, request: Request):
    payload = await request.json()
    student_id = payload.get("student_id", "stud_1")

    _cursor.execute("SELECT capacity, enrolled FROM courses WHERE id = ?", (course_id,))
    row = _cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Course not found")

    capacity, enrolled = row[0], row[1]

    # BUG-STUD-004: Over-enrollment permitted beyond capacity
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-004"):
        new_enrolled = enrolled + 1
        _cursor.execute("UPDATE courses SET enrolled = ? WHERE id = ?", (new_enrolled, course_id))
        _db.commit()
        return {"status": 200, "enrolled_count": new_enrolled}
    else:
        if enrolled >= capacity:
            raise HTTPException(status_code=400, detail="Course is at full capacity")
        new_enrolled = enrolled + 1
        _cursor.execute("UPDATE courses SET enrolled = ? WHERE id = ?", (new_enrolled, course_id))
        _db.commit()
        return {"status": 200, "enrolled_count": new_enrolled}


@app.post("/api/v1/courses/{course_id}/drop")
async def drop_course(course_id: str, request: Request):
    payload = await request.json()

    # BUG-STUD-005: Drop past deadline allowed without penalty
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-005"):
        return {"status": 200, "dropped": True}
    else:
        # Policy: past deadline drops forbidden
        raise HTTPException(status_code=400, detail="Cannot drop course after semester deadline")


@app.get("/api/v1/students/{student_id}/transcripts")
async def get_transcripts(student_id: str, semester: str = "Fall2025"):
    # BUG-STUD-006: Semester filter SQL injection crash 500
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-006"):
        query = f"SELECT student_id, course_id FROM enrollments WHERE semester = '{semester}'"
        _cursor.execute(query)  # Unhandled SQLite syntax crash if quotes present
        rows = _cursor.fetchall()
    else:
        rows = []

    return {"status": 200, "transcripts": rows}


@app.post("/api/v1/courses/{course_id}/register")
async def register_advanced_course(course_id: str, request: Request):
    payload = await request.json()

    # BUG-STUD-007: Prerequisite check bypass
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-007"):
        return {"status": 200, "registered": True}
    else:
        _cursor.execute("SELECT prereqs FROM courses WHERE id = ?", (course_id,))
        row = _cursor.fetchone()
        if row and row[0]:
            raise HTTPException(status_code=400, detail=f"Prerequisites not fulfilled: {row[0]}")
        return {"status": 200, "registered": True}


@app.post("/api/v1/students/{student_id}/study-plan")
async def create_study_plan(student_id: str, request: Request):
    payload = await request.json()
    credits_val = payload.get("credits", 15)

    # BUG-STUD-009: Negative credit hours allowed (-3)
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-009"):
        return {"status": 200, "credits": credits_val}
    else:
        if credits_val < 1:
            raise HTTPException(status_code=422, detail="Credits must be a positive integer")
        return {"status": 200, "credits": credits_val}


@app.post("/api/v1/grades/batch-upload")
async def batch_upload_grades(request: Request):
    payload = await request.json()
    grades_list = payload.get("grades", [])

    # BUG-STUD-010: Failure leaves partial commit without rollback
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-010"):
        committed = 0
        for item in grades_list:
            if item.get("student_id") == "invalid_id_999":
                # Simulated crash without rolling back prior items
                return Response(
                    content='{"status": 500, "committed_items": 1, "rolled_back": false}',
                    status_code=500,
                    media_type="application/json"
                )
            committed += 1
        return {"status": 200, "committed_items": committed}
    else:
        for item in grades_list:
            if item.get("student_id") == "invalid_id_999":
                raise HTTPException(status_code=400, detail="Batch failed: transaction rolled back")
        return {"status": 200, "committed_items": len(grades_list)}


@app.get("/api/v1/students/{student_id}/financial-aid")
async def get_financial_aid(student_id: str, request: Request):
    header_user = request.headers.get("X-Student-Id", student_id)

    # BUG-STUD-011: IDOR allows viewing another student's aid ledger
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-011"):
        _cursor.execute("SELECT scholarship_amount FROM financial_aid WHERE student_id = ?", (student_id,))
        row = _cursor.fetchone()
        amt = row[0] if row else 0.0
        return {"status": 200, "scholarship_amount": amt}
    else:
        if header_user != student_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view financial aid records of other students")
        _cursor.execute("SELECT scholarship_amount FROM financial_aid WHERE student_id = ?", (student_id,))
        row = _cursor.fetchone()
        amt = row[0] if row else 0.0
        return {"status": 200, "scholarship_amount": amt}


@app.get("/api/v1/departments/{department_id}/rankings")
async def get_department_rankings(department_id: str):
    # BUG-STUD-012: Student with null department crashes ranking calculation endpoint
    if BenchmarkEnvironment.is_bug_active("BUG-STUD-012"):
        student_val = None
        ranking_calc = student_val < 3.5  # TypeError: '<' not supported between instances of 'NoneType' and 'float'
    return {"status": 200, "rankings": []}
