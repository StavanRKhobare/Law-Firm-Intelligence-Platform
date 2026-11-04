-- Hearings, deadlines, tasks and remarks for the sample firm, dated around today so the
-- dashboards have something to show. Load once, after sample_data.sql. Not for real firm data.

UPDATE legal_case c
SET disposed_on = COALESCE(c.disposed_on, a.changed_at::date, c.date_filed + 400),
    outcome = v.outcome
FROM (VALUES (1, 'Won'), (4, 'Settled'), (8, 'Won')) AS v(case_id, outcome)
LEFT JOIN (
    SELECT case_id, max(changed_at) AS changed_at FROM case_status_audit
    WHERE new_status = 'Disposed' GROUP BY case_id
) a ON a.case_id = v.case_id
WHERE c.case_id = v.case_id;

INSERT INTO hearing (case_id, hearing_date, hearing_time, court_id, courtroom, judge, purpose, status, outcome, remarks, attended_by)
SELECT v.case_id, CURRENT_DATE + v.days, v.at_time::time, c.court_id, v.room, v.judge, v.purpose, v.status, v.outcome, v.remarks, v.attended_by
FROM (VALUES
    (2, -60, '10:30', 'Court 4', 'Shri R. Kulkarni', 'Plea recording', 'Adjourned', 'Accused sought time', 'Vakalat for accused filed late.', 1),
    (2, -21, '11:00', 'Court 4', 'Shri R. Kulkarni', 'Complainant evidence', 'Held', 'PW1 examined in chief', 'Cross-examination next date.', 1),
    (2, 3, '10:30', 'Court 4', 'Shri R. Kulkarni', 'Cross-examination of PW1', 'Scheduled', NULL, NULL, NULL),
    (5, 0, '14:00', 'Court 2', 'Smt. A. Hegde', 'Arguments on bail', 'Scheduled', NULL, NULL, NULL),
    (10, -14, '10:45', 'Hall 7', 'Hon. Justice S. Murthy', 'Admission', 'Adjourned', 'Notice to State', 'State to file objections.', 1),
    (10, 6, '10:45', 'Hall 7', 'Hon. Justice S. Murthy', 'Objections and admission', 'Scheduled', NULL, NULL, NULL),
    (7, 1, '11:30', 'Family Court 3', 'Smt. P. Rao', 'Mediation report', 'Scheduled', NULL, NULL, NULL),
    (3, -2, '12:00', 'Family Court 1', 'Smt. P. Rao', 'Interim maintenance', 'Scheduled', NULL, NULL, NULL),
    (6, 12, '10:00', 'Court 11', NULL, 'First hearing', 'Scheduled', NULL, NULL, NULL)
) AS v(case_id, days, at_time, room, judge, purpose, status, outcome, remarks, attended_by)
JOIN legal_case c ON c.case_id = v.case_id;

INSERT INTO task (title, description, kind, priority, status, due_date, case_id, assignee_id, created_by)
SELECT v.title, v.description, v.kind, v.priority, 'Open', CURRENT_DATE + v.days, v.case_id,
       (SELECT user_id FROM users WHERE username = v.assignee),
       (SELECT user_id FROM users WHERE username = 'admin')
FROM (VALUES
    ('File reply to objections', 'State objections were served last week.', 'Reply', 'High', 4, 10, 'lawyer1'),
    ('Last date to file appeal against acquittal order', NULL, 'Limitation', 'High', 18, 10, 'lawyer1'),
    ('Certified copy of cheque return memo', 'Needed for cross-examination.', 'Task', 'Normal', -2, 2, 'lawyer1'),
    ('Compliance affidavit in bail matter', NULL, 'Compliance', 'High', -1, 5, 'lawyer1'),
    ('Update cause list for next week', NULL, 'Task', 'Low', 2, NULL, 'staff1'),
    ('Index documents for mediation', NULL, 'Filing', 'Normal', 1, 7, 'staff1')
) AS v(title, description, kind, priority, days, case_id, assignee);

INSERT INTO case_note (case_id, body, author_id, author_name, created_at)
SELECT v.case_id, v.body, u.user_id, u.full_name, now() - (v.days_ago || ' days')::interval
FROM (VALUES
    (2, 'Client confirmed the original cheque is with us. Keep it ready for the next date.', 'lawyer1', 2),
    (5, 'Discussed bail conditions with client. Surety is ready.', 'lawyer1', 1),
    (10, 'State counsel asked for two weeks. Oppose any further time.', 'lawyer1', 5)
) AS v(case_id, body, username, days_ago)
JOIN users u ON u.username = v.username;
