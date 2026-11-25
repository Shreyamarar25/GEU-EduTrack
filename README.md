# GEU EduTrack

**College Academic & Process Management System** | Team InnoVision (T256) | PBL Phase 3 (Final)

GEU EduTrack is an academic management system that handles students, courses, attendance, marks and report generation, and combines DBMS concepts with Operating System concepts. Report generation requests are treated as OS processes, so scheduling, process states, deadlock handling and synchronization can be demonstrated on real application data.

## Problem Statement / Objective

Academic record systems usually show only data and never explain how the underlying work is managed. This project aims to:

- Build a role-based academic portal (Admin, Teacher, Student, Exam Cell) backed by a properly designed relational database.
- Apply DBMS concepts: schema design, constraints, views, triggers and stored procedures.
- Apply OS concepts in a practical setting: CPU scheduling, process states, memory allocation, resource allocation, deadlock avoidance and synchronization.
- Integrate both sides, so that report requests made in the application are stored as OS processes and run through the scheduler.

## Team Members

| Name | Role in the project |
|---|---|
| Shreya | Process model, resource pool, live safety check, deadlock detection and Banker's algorithm |
| Rithisha | Synchronization demos, scheduler views (queue lock, bounded queue, FinishTask), serializers, README |
| Vanshika | Scheduler and OS concept APIs, URL routing, frontend scheduler and OS concept pages |

## Technologies / Tools Used

| Area | Technology |
|---|---|
| Backend | Python, Django, Django REST Framework, django-cors-headers |
| Database | SQLite (default), MySQL (optional, for triggers, views and procedures) |
| Frontend | HTML, CSS, JavaScript (no framework) |
| Tools | Git and GitHub, VS Code, Live Server, MySQL Workbench |

## Project Structure

```
edutrack/
  backend/
    config/         settings, urls
    academics/      models, serializers, views (REST APIs), role permissions, seed command
    scheduler/      scheduler.py (FCFS / SJF / Priority), memory allocation (First / Best / Worst Fit),
                    resources.py, live.py,
                    deadlock.py (Banker's algorithm), synchronization.py, api.py
    sql/            dbms_objects.sql (views, triggers, stored procedures for MySQL)
  frontend/         plain HTML + CSS + JavaScript
```

## Major Features / Modules

- **Authentication and role dashboards:** separate dashboards for Admin, Teacher, Student and Exam Cell.
- **Academic module:** students, courses, attendance and marks with REST APIs.
- **DBMS objects:** constraints in `models.py`, plus views, triggers and stored procedures in `sql/dbms_objects.sql`.
- **CPU scheduler:** FCFS, SJF and Priority scheduling with a Gantt chart on the scheduler page.
- **Process states:** report requests move through states such as Waiting, Running and Held back, and can be finished from the scheduler page.
- **Memory allocation:** First Fit, Best Fit and Worst Fit partition allocation strategies, with a comparison of how each one places processes.
- **Resource management and deadlock:** a resource pool, per-report resource needs, a live Banker's safety check for queued tasks, and deadlock detection.
- **Synchronization:** a race condition demo (with and without a mutex) and a producer-consumer demo using a bounded buffer, two semaphores and a mutex. The report-request queue in the scheduler is protected by a lock and has a fixed size.
- **OS-DBMS integration:** report requests (attendance and performance reports) are saved as `OsProcess` records, scheduled, run, finished and then downloaded by the requester.
- **Admin OS concept pages:** Deadlock and Synchronization pages in the Admin dashboard.

## Setup / Installation

### 1. Run the backend (SQLite, works instantly)
```
cd backend
python -m venv venv
venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # demo users + sample data
python manage.py runserver     # API at http://127.0.0.1:8000/api/
```

### 2. Run the frontend
In VS Code install the **Live Server** extension, then right-click `frontend/index.html` and choose *Open with Live Server*.
Or run `cd frontend && python -m http.server 5500` and open http://127.0.0.1:5500

Demo logins: `admin/admin123`, `teacher1/teacher123`, `student1/student123`, `exam1/exam123`

### 3. Switch to MySQL (needed to show triggers, views and procedures)
1. In MySQL Workbench run `CREATE DATABASE edutrack;`
2. Set environment variables, then migrate and seed again. In Windows PowerShell:
   ```
   $env:USE_MYSQL="1"; $env:DB_PASSWORD="your_mysql_password"
   python manage.py migrate
   python manage.py seed
   ```
3. In Workbench open and run `backend/sql/dbms_objects.sql`.

## Project Status (Phase 3 - Complete)

| Milestone | Status |
|---|---|
| Schema and ER design | Done |
| DBMS objects and constraints | Done (`models.py`, `sql/dbms_objects.sql`) |
| Backend REST APIs | Done |
| Authentication and role dashboards | Done |
| Academic UI | Done |
| Scheduler and process states | Done (FCFS / SJF / Priority, Gantt chart, Finish button) |
| Memory allocation (First / Best / Worst Fit) | Done |
| Resource pool, Banker's algorithm, deadlock detection | Done |
| Synchronization (mutex, semaphores, producer-consumer) | Done |
| OS-DBMS integration (OS_PROCESS read/write) | Done |
| Testing, final reports, demo | Done |

All planned modules are complete. Phase 1 covered design, Phase 2 covered the core backend and scheduler, and Phase 3 added the OS concepts, integration and final polish.

## Features
- Role-based login and dashboards for Admin, Teacher, Student and Exam Cell
- Manage students, teachers, courses, enrollments, attendance and marks
- Attendance and performance reports, downloadable as PDF
- Report requests go through an OS scheduler queue (FCFS, SJF, Priority) and are approved by the Admin
- Deadlock and Synchronization pages for the Admin

## OS concepts used
| Concept | Where |
|---|---|
| CPU scheduling (FCFS, SJF, Priority) | `scheduler/scheduler.py`, OS Scheduler page |
| Process states (NEW, READY, WAITING, RUNNING, COMPLETED) | `OsProcess` model |
| Deadlock detection and Banker's algorithm | `scheduler/deadlock.py`, `scheduler/live.py`, Deadlock page |
| Mutex and race condition | `scheduler/synchronization.py`, Synchronization page |
| Producer-consumer (bounded buffer) | report request queue (max 5 waiting requests) |
