-- =====================================================================
-- GEU EduTrack - DBMS objects (run in MySQL Workbench AFTER `python manage.py migrate`)
-- Tables are created by Django (names: student, teacher, course, enrollment,
-- attendance, marks, os_process). This file adds: indexes, views, triggers,
-- stored procedures and example JOIN / GROUP BY queries.
-- =====================================================================
USE edutrack;

-- ---------- INDEXING (Django already made idx_student_name & idx_att_student_date)
CREATE INDEX idx_marks_course ON marks (course_id, exam_type);

-- ---------- VIEWS
CREATE OR REPLACE VIEW student_attendance_view AS
SELECT s.student_id, s.roll_no, s.name AS student_name, c.course_id, c.course_name,
       COUNT(a.attendance_id)                              AS total_classes,
       SUM(a.status = 'Present')                           AS present,
       ROUND(100 * SUM(a.status = 'Present') / COUNT(a.attendance_id), 1) AS attendance_pct
FROM enrollment e
JOIN student s ON s.student_id = e.student_id
JOIN course  c ON c.course_id  = e.course_id
LEFT JOIN attendance a ON a.student_id = e.student_id AND a.course_id = e.course_id
GROUP BY s.student_id, s.roll_no, s.name, c.course_id, c.course_name;

CREATE OR REPLACE VIEW student_performance_view AS
SELECT s.student_id, s.roll_no, s.name AS student_name, c.course_name,
       ROUND(AVG(m.marks), 2) AS avg_marks, COUNT(m.mark_id) AS exams_taken
FROM enrollment e
JOIN student s ON s.student_id = e.student_id
JOIN course  c ON c.course_id  = e.course_id
LEFT JOIN marks m ON m.student_id = e.student_id AND m.course_id = e.course_id
GROUP BY s.student_id, s.roll_no, s.name, c.course_name;

CREATE OR REPLACE VIEW course_summary_view AS
SELECT c.course_id, c.course_name, t.name AS teacher_name,
       COUNT(DISTINCT e.student_id) AS students_enrolled,
       ROUND(AVG(m.marks), 2)       AS avg_marks
FROM course c
LEFT JOIN teacher t    ON t.teacher_id = c.teacher_id
LEFT JOIN enrollment e ON e.course_id  = c.course_id
LEFT JOIN marks m      ON m.course_id  = c.course_id
GROUP BY c.course_id, c.course_name, t.name;

-- ---------- TRIGGERS
DELIMITER $$
DROP TRIGGER IF EXISTS trg_attendance_before_insert $$
CREATE TRIGGER trg_attendance_before_insert
BEFORE INSERT ON attendance
FOR EACH ROW
BEGIN
    -- 1) only enrolled students can be marked
    IF NOT EXISTS (SELECT 1 FROM enrollment
                   WHERE student_id = NEW.student_id AND course_id = NEW.course_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Student is not enrolled in this course';
    END IF;
    -- 2) block duplicate entry for the same day
    IF EXISTS (SELECT 1 FROM attendance
               WHERE student_id = NEW.student_id AND course_id = NEW.course_id
                 AND attendance_date = NEW.attendance_date) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Attendance already marked for this date';
    END IF;
END $$

DROP TRIGGER IF EXISTS trg_marks_before_insert $$
CREATE TRIGGER trg_marks_before_insert
BEFORE INSERT ON marks
FOR EACH ROW
BEGIN
    IF NEW.marks < 0 OR NEW.marks > 100 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Marks must be between 0 and 100';
    END IF;
END $$

-- ---------- STORED PROCEDURES
DROP PROCEDURE IF EXISTS GetStudentReport $$
CREATE PROCEDURE GetStudentReport(IN p_student_id INT)
BEGIN
    SELECT s.roll_no, s.name, s.branch, s.year FROM student s WHERE s.student_id = p_student_id;
    SELECT course_name, total_classes, present, attendance_pct
      FROM student_attendance_view WHERE student_id = p_student_id;
    SELECT course_name, avg_marks, exams_taken
      FROM student_performance_view WHERE student_id = p_student_id;
END $$

DROP PROCEDURE IF EXISTS GetCourseSummary $$
CREATE PROCEDURE GetCourseSummary(IN p_course_id INT)
BEGIN
    SELECT * FROM course_summary_view WHERE course_id = p_course_id;
END $$
DELIMITER ;

-- ---------- TRANSACTION example (enrol a student - all or nothing)
-- START TRANSACTION;
-- INSERT INTO enrollment (student_id, course_id, enrollment_date, status) VALUES (1, 2, CURDATE(), 'Active');
-- COMMIT;   -- or ROLLBACK;

-- ---------- Try them
-- SELECT * FROM student_attendance_view WHERE attendance_pct < 75;
-- CALL GetStudentReport(1);
-- CALL GetCourseSummary(1);
