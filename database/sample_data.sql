-- Sample firm for demos and tests. Load only into a freshly migrated, empty database.
-- Do not load this on a real firm database.

-- ---------------------------------------------------------------------------
-- Sample data for the application. This is not an ML training corpus.
-- Dates stay on or before 22 Oct 2026, which is the project clock used here.
-- ---------------------------------------------------------------------------

INSERT INTO practice_group (group_id, group_name, description, email, contactno) VALUES
(1, 'Criminal Litigation', 'Trials, bail, and criminal appeals', 'criminal@sample-chambers.test', '08040001001'),
(2, 'Civil Litigation', 'Property, contract, and injunctions', 'civil@sample-chambers.test', '08040001002'),
(3, 'Family Law', 'Marriage, maintenance, and custody', 'family@sample-chambers.test', '08040001003'),
(4, 'Corporate Disputes', 'Shareholder and tribunal work', 'corporate@sample-chambers.test', '08040001004');

INSERT INTO pincode_area (pincode, city, district, state) VALUES
('560001', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560009', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560011', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560024', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560025', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560038', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560058', 'Bengaluru', 'Bengaluru Urban', 'Karnataka'),
('560066', 'Bengaluru', 'Bengaluru Urban', 'Karnataka');

INSERT INTO location (location_id, landmark, streetno, pincode) VALUES
(1, 'MG Road commercial complex', '12', '560001'),
(2, 'Jayanagar 4th Block', '27', '560011'),
(3, 'Whitefield IT campus', '4', '560066'),
(4, 'Indiranagar 100 Feet Road', '100', '560038'),
(5, 'Hebbal residential layout', '8', '560024'),
(6, 'Peenya industrial estate', '2', '560058');

INSERT INTO court (court_id, court_name, court_type, pincode) VALUES
(1, 'City Civil Court, Bengaluru', 'City Civil Court', '560009'),
(2, 'Chief Metropolitan Magistrate Court, Bengaluru', 'Magistrate Court', '560001'),
(3, 'High Court of Karnataka', 'High Court', '560001'),
(4, 'Debt Recovery Tribunal, Bengaluru', 'Tribunal', '560025');

INSERT INTO lawyer (lawyer_id, fname, lname, designation, phoneno, bar_id, group_id) VALUES
(1, 'Ananya', 'Rao', 'Partner', '9845000001', 'KAR/1234/2012', 1),
(2, 'Vikram', 'Iyer', 'Senior Associate', '9845000002', 'KAR/5678/2016', 1),
(3, 'Meera', 'Nair', 'Partner', '9845000003', 'KAR/2345/2011', 2),
(4, 'Rohan', 'Desai', 'Associate', '9845000004', 'KAR/8901/2019', 2),
(5, 'Farah', 'Khan', 'Partner', '9845000005', 'KAR/3456/2014', 3),
(6, 'Arjun', 'Menon', 'Associate', '9845000006', 'KAR/9012/2020', 4);

INSERT INTO client (client_id, fname, lname, email, address, sex, notes) VALUES
(1, 'Lakshmi', 'Prasad', 'lakshmi.prasad@example.test', 'Jayanagar, Bengaluru', 'F', 'Property owner. Prefers email updates.'),
(2, 'Suresh', 'Bhat', 'suresh.bhat@example.test', 'Rajajinagar, Bengaluru', 'M', 'Cheque-dishonour complainant.'),
(3, 'Nalini', 'George', 'nalini.george@example.test', 'Hebbal, Bengaluru', 'F', 'Maintenance petition. Documents in Kannada and English.'),
(4, 'Helios Components', 'Pvt Ltd', 'legal@helios.example.test', 'Whitefield, Bengaluru', 'O', 'Corporate client. Use the company name on filings.'),
(5, 'Imran', 'Qureshi', 'imran.q@example.test', 'Shivajinagar, Bengaluru', 'M', 'Accused in a hurt case. Bail already granted.'),
(6, 'Divya', 'Shetty', 'divya.shetty@example.test', 'Indiranagar, Bengaluru', 'F', 'Seeking dissolution of marriage.'),
(7, 'Northwind', 'Traders', 'ops@northwind.example.test', 'Peenya, Bengaluru', 'O', 'Supply contract dispute.'),
(8, 'Kiran', 'Joshi', 'kiran.joshi@example.test', 'Malleshwaram, Bengaluru', 'M', 'Shareholder in a closely held company.');

INSERT INTO opposing_party (party_id, fname, lname, email, address, sex, repeat_party) VALUES
(1, 'Ravi', 'Hegde', 'ravi.hegde@example.test', 'Basavanagudi, Bengaluru', 'M', false),
(2, 'Oasis Retail', 'Pvt Ltd', 'notices@oasis.example.test', 'MG Road, Bengaluru', 'O', false),
(3, 'Prakash', 'George', 'prakash.george@example.test', 'Hebbal, Bengaluru', 'M', false),
(4, 'State', 'Prosecution', NULL, 'Bengaluru', 'O', false),
(5, 'Aditya', 'Shetty', 'aditya.shetty@example.test', 'Indiranagar, Bengaluru', 'M', false),
(6, 'Summit', 'Alloys', 'accounts@summit.example.test', 'Peenya, Bengaluru', 'O', false),
(7, 'Neelam', 'Joshi', 'neelam.joshi@example.test', 'Koramangala, Bengaluru', 'F', false),
(8, 'Harish', 'Pai', 'harish.pai@example.test', 'Jayanagar, Bengaluru', 'M', false);

INSERT INTO client_phone_no (client_id, phoneno) VALUES
(1, '9845111001'),
(2, '9845111002'),
(3, '9845111003'),
(5, '9845111005');

INSERT INTO opposing_party_phone_no (party_id, phoneno) VALUES
(1, '9845222001'),
(3, '9845222003'),
(5, '9845222005');

INSERT INTO legal_case (
    case_id, matter_title, matter_description, case_number,
    date_cause, date_filed, status, court_id, location_id
) VALUES
(1, 'Recovery of possession, Jayanagar house',
 'Client seeks possession of a house occupied by a relative after a failed family arrangement. The plaint relies on title deeds and municipal tax receipts.',
 'OS 112/2024', '2024-01-18', '2024-02-02', 'Disposed', 1, 2),
(2, 'Complaint under NI Act for dishonoured cheque',
 'A cheque issued towards goods supplied at MG Road was returned unpaid. Notice of demand was served and the drawer did not pay.',
 'CC 448/2024', '2024-05-12', '2024-06-03', 'Hearing', 2, 1),
(3, 'Maintenance under personal law',
 'Petition for monthly maintenance and residence after the respondent left the Hebbal household.',
 'MC 77/2025', '2024-11-20', '2025-01-09', 'Pending', 1, 5),
(4, 'Oppression and mismanagement petition',
 'Minority shareholder alleges exclusion from management and diversion of Whitefield unit receipts.',
 'CP 19/2024', '2024-03-02', '2024-03-28', 'Disposed', 4, 3),
(5, 'Defence in a hurt prosecution',
 'Client is accused of causing hurt during a dispute at an Indiranagar shop. The defence is private defence and lack of intent.',
 'CC 902/2025', '2025-02-14', '2025-03-01', 'Hearing', 2, 4),
(6, 'Damages for delayed industrial supply',
 'Peenya buyer claims damages for late delivery of components and a consequent line stoppage.',
 'OS 640/2025', '2025-04-08', '2025-05-02', 'Filed', 1, 6),
(7, 'Divorce and return of stridhan',
 'Petition for dissolution and return of jewellery and household articles listed in the schedule.',
 'MC 210/2025', '2025-06-01', '2025-06-19', 'Hearing', 1, 4),
(8, 'Temporary injunction against alienation',
 'Urgent application to restrain sale of the Jayanagar schedule property while title is in dispute.',
 'OS 113/2024', '2024-02-10', '2024-02-16', 'Disposed', 1, 2),
(9, 'Second NI Act complaint, same drawer',
 'A later cheque from the same retail account was also dishonoured after a partial settlement failed.',
 'CC 771/2025', '2025-08-22', '2025-09-10', 'Filed', 2, 1),
(10, 'Appeal against acquittal',
 'Appeal challenging an acquittal in a hurt case tried by the magistrate. The record is before the High Court.',
 'CRL.A 55/2026', '2025-01-30', '2026-01-20', 'Hearing', 3, 4),
(11, 'Custody of minor child',
 'Interim and final custody sought for a child residing with the respondent in Hebbal.',
 'G&W 14/2026', '2025-12-02', '2026-01-08', 'Pending', 1, 5),
(12, 'Recovery before the tribunal',
 'Lender seeks recovery of a term loan secured against the Whitefield plant.',
 'OA 88/2026', '2026-02-11', '2026-03-04', 'Filed', 4, 3);

INSERT INTO matter_type (case_id, matter_type) VALUES
(1, 'Civil'), (2, 'Criminal'), (3, 'Family'), (4, 'Corporate'),
(5, 'Criminal'), (6, 'Civil'), (7, 'Family'), (8, 'Civil'),
(9, 'Criminal'), (10, 'Criminal'), (11, 'Family'), (12, 'Corporate');

INSERT INTO statute_section (case_id, statute_section) VALUES
(1, 'Specific Relief Act 5'),
(1, 'CPC Order VII'),
(2, 'NI Act 138'),
(3, 'Hindu Adoptions and Maintenance Act 18'),
(4, 'Companies Act 241'),
(5, 'BNS 115'),
(6, 'Contract Act 73'),
(7, 'Hindu Marriage Act 13'),
(8, 'CPC Order XXXIX'),
(9, 'NI Act 138'),
(10, 'BNSS 419'),
(11, 'Hindu Minority and Guardianship Act 6'),
(12, 'RDDBFI Act 19');

INSERT INTO case_client (case_id, client_id) VALUES
(1, 1), (2, 2), (3, 3), (4, 8), (5, 5), (6, 7),
(7, 6), (8, 1), (9, 2), (10, 5), (11, 3), (12, 4);

INSERT INTO case_opposing_party (case_id, party_id) VALUES
(1, 1), (2, 2), (3, 3), (4, 7), (5, 4), (6, 6),
(7, 5), (8, 8), (9, 2), (10, 4), (11, 3), (12, 7);

INSERT INTO case_lawyer (case_id, lawyer_id, role, assigned_date, end_date) VALUES
(1, 3, 'Lead Counsel', '2024-02-02', NULL),
(1, 4, 'Associate', '2024-02-02', NULL),
(2, 1, 'Lead Counsel', '2024-06-03', NULL),
(2, 2, 'Associate', '2024-06-10', NULL),
(3, 5, 'Lead Counsel', '2025-01-09', NULL),
(4, 3, 'Lead Counsel', '2024-03-28', '2024-11-01'),
(4, 6, 'Associate', '2024-03-28', NULL),
(5, 1, 'Lead Counsel', '2025-03-01', NULL),
(5, 2, 'Research', '2025-03-05', '2025-06-01'),
(6, 3, 'Lead Counsel', '2025-05-02', NULL),
(6, 4, 'Associate', '2025-05-02', NULL),
(7, 5, 'Lead Counsel', '2025-06-19', NULL),
(8, 4, 'Lead Counsel', '2024-02-16', NULL),
(9, 2, 'Lead Counsel', '2025-09-10', NULL),
(9, 1, 'Associate', '2025-09-12', NULL),
(10, 1, 'Lead Counsel', '2026-01-20', NULL),
(10, 2, 'Associate', '2026-01-20', NULL),
(11, 5, 'Lead Counsel', '2026-01-08', NULL),
(12, 6, 'Lead Counsel', '2026-03-04', NULL),
(12, 3, 'Associate', '2026-03-04', NULL);

-- Keep the sample statuses. The evidence trigger would otherwise move every Filed matter to Hearing.
ALTER TABLE evidence DISABLE TRIGGER evidence_advances_status;

INSERT INTO evidence (description, filed_date, mongo_id, status, lawyer_id, case_id) VALUES
('Certified copy of the title deed and tax receipts', '2024-02-20', NULL, 'Produced', 3, 1),
('Bank return memo and statutory notice', '2024-06-18', NULL, 'Filed', 1, 2),
('Affidavit of assets and liabilities', '2025-02-02', NULL, 'Under Review', 5, 3),
('Board minutes and bank statements of the Whitefield unit', '2024-04-15', NULL, 'Produced', 6, 4),
('Wound certificate relied on by the prosecution, with defence notes', '2025-04-02', NULL, 'Received', 2, 5),
('Purchase order and delivery challans', '2025-05-20', NULL, 'Received', 4, 6),
('Schedule of stridhan with photographs', '2025-07-01', NULL, 'Filed', 5, 7),
('Application and affidavit for temporary injunction', '2024-02-16', NULL, 'Produced', 4, 8),
('Second statutory notice and postal acknowledgement', '2025-09-25', NULL, 'Received', 2, 9),
('Certified copy of the magistrate judgment', '2026-02-11', NULL, 'Filed', 1, 10),
('School records and residence affidavit', '2026-02-18', NULL, 'Under Review', 5, 11),
('Loan agreement and statement of account', '2026-03-20', NULL, 'Received', 6, 12);

ALTER TABLE evidence ENABLE TRIGGER evidence_advances_status;

-- History rows for matters whose status moved after filing.
-- The audit trigger covers later updates. These rows record the path already taken.
INSERT INTO case_status_audit (case_id, old_status, new_status, changed_at, changed_by) VALUES
(1, 'Filed', 'Hearing', '2024-04-12', 'seed'),
(1, 'Hearing', 'Disposed', '2024-09-30', 'seed'),
(2, 'Filed', 'Hearing', '2024-07-01', 'seed'),
(4, 'Filed', 'Hearing', '2024-05-10', 'seed'),
(4, 'Hearing', 'Disposed', '2024-11-01', 'seed'),
(5, 'Filed', 'Hearing', '2025-04-02', 'seed'),
(7, 'Filed', 'Hearing', '2025-07-01', 'seed'),
(8, 'Filed', 'Hearing', '2024-03-01', 'seed'),
(8, 'Hearing', 'Disposed', '2024-06-14', 'seed'),
(10, 'Filed', 'Hearing', '2026-02-11', 'seed');

INSERT INTO users (username, email, hashed_password, full_name, role, is_active) VALUES
('admin', 'admin@example.com', '$2b$12$I/K6QiQ3oV2Z1RF4rdTBOOjY2JLHpA9YTcG8hyCAbn5G55bSz8mSO', 'System Administrator', 'admin', true),
('lawyer1', 'lawyer1@example.com', '$2b$12$WauWxqsMGKK1RsvEQ5OGr.y5lgV.TTij3rQfdHviP.6FpIcIfdfMa', 'Ananya Rao', 'lawyer', true),
('staff1', 'staff1@example.com', '$2b$12$VTcgCeu2CXBuEsEo.ecElONKEOfP6nRGoLp8hFbPJooW3An1Bf/Ce', 'Records Clerk', 'staff', true);

SELECT setval(pg_get_serial_sequence('practice_group', 'group_id'), (SELECT MAX(group_id) FROM practice_group));
SELECT setval(pg_get_serial_sequence('location', 'location_id'), (SELECT MAX(location_id) FROM location));
SELECT setval(pg_get_serial_sequence('court', 'court_id'), (SELECT MAX(court_id) FROM court));
SELECT setval(pg_get_serial_sequence('lawyer', 'lawyer_id'), (SELECT MAX(lawyer_id) FROM lawyer));
SELECT setval(pg_get_serial_sequence('client', 'client_id'), (SELECT MAX(client_id) FROM client));
SELECT setval(pg_get_serial_sequence('opposing_party', 'party_id'), (SELECT MAX(party_id) FROM opposing_party));
SELECT setval(pg_get_serial_sequence('legal_case', 'case_id'), (SELECT MAX(case_id) FROM legal_case));

-- Link the sample lawyer login to its lawyer record.
UPDATE users SET lawyer_id = (SELECT lawyer_id FROM lawyer WHERE fname = 'Ananya' AND lname = 'Rao') WHERE username = 'lawyer1';
