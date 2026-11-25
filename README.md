# GEU EduTrack - Phase 2 (about 55% complete)

```
edutrack/
  backend/    Django + Django REST Framework (Python)
    config/         settings, urls
    academics/      models, serializers, views (REST APIs), role permissions, seed command
    scheduler/      scheduler.py  -> FCFS / SJF / Priority (standalone)
    sql/            dbms_objects.sql -> views, triggers, stored procedures (MySQL)
  frontend/   plain HTML + CSS + JavaScript (no framework)
```

## 1. Run the backend (SQLite - works instantly)
```
cd backend
python -m venv venv
venv\Scripts\activate          (Windows)   |   source venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed          # demo users + sample data
python manage.py runserver     # API at http://127.0.0.1:8000/api/
```

## 2. Run the frontend
In VS Code install the **Live Server** extension, right-click `frontend/index.html` -> *Open with Live Server*.
(Or: `cd frontend && python -m http.server 5500` and open http://127.0.0.1:5500)

Demo logins: admin/admin123, teacher1/teacher123, student1/student123, exam1/exam123

## 3. Switch to MySQL (needed to show triggers/views/procedures)
1. In MySQL Workbench: `CREATE DATABASE edutrack;`
2. Set environment variables, then migrate + seed again.
   Windows PowerShell:
   ```
   $env:USE_MYSQL="1"; $env:DB_PASSWORD="your_mysql_password"
   python manage.py migrate
   python manage.py seed
   ```
3. In Workbench open and run `backend/sql/dbms_objects.sql`.

## Phase 2 status (matches your report)
| Milestone | Status |
|---|---|
| Schema + ER design | Done |
| DBMS objects + constraints | Done (`models.py`, `sql/dbms_objects.sql`) |
| Backend REST APIs | Done |
| Authentication + role dashboards | Done |
| Academic UI | In progress (all main screens work, styling is basic) |
| Scheduler + process states | In progress (algorithms + Gantt work on entered data) |
| OS-DBMS integration (OS_PROCESS read/write) | Phase 3 |
| Testing, final reports, demo | Phase 3 |
