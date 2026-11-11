# Law firm case management: project guide

> **Schema additions.** Migrations 0002 to 0004 added `join_request`, `hearing`, `case_note`, `task` and `audit_log`, and new columns on `users`, `lawyer`, `legal_case` and `evidence`. The tables below describe the baseline (`backend/migrations/sql/0001_baseline.sql`). File bytes are now in MongoDB GridFS (bucket `evidence_fs`), and `evidence.mongo_id` is the GridFS file id.

This is the reference for the system as it stands after the domain change. The runnable code is in `crime_intelligence_platform/`. That folder name is historical. The database, API, and screens now describe one litigation firm.

The previous police dump is still at `crime_intelligence_platform/database/crime_intelligence_db_backup.sql`. Leave it as the record of the old schema. Do not import it into `law_firm_db`.

## 1. What the system is

The database is the boundary of one firm. It is not a directory of every court in India, and it is not a police records system with the labels swapped.

A matter is the centre. Around it the system records:

- which lawyers are instructed, and which one is the active lead
- which clients the firm represents
- which opposing parties are adverse
- which court is currently hearing the matter
- where the dispute is located
- which matter types and statutory provisions apply
- how the status has changed
- which evidence files belong to the matter

The file bytes are not stored in PostgreSQL. `evidence.mongo_id` is the pointer into MongoDB. PostgreSQL keeps the metadata.

## 2. Decisions that are now fixed

These were the choices that kept the DBMS work intact.

| Question | Decision |
|---|---|
| What is the firm? | The whole database. There is no one-row `law_firm` table. |
| What replaced department? | `practice_group`: Criminal Litigation, Civil Litigation, Family Law, Corporate Disputes. A lawyer belongs to one group. |
| Is a department a court? | No. A court is where the matter is being heard. |
| What replaced location? | Nothing. `location` is still the place connected to the dispute. `court` is a new table. |
| How many lawyers per matter? | Many. `case_lawyer` is the only assignment store. `legal_case` has no lawyer foreign key. |
| How many clients per matter? | Many, through `case_client`. A client can appear on many matters. |
| Can the same person be client and opponent? | Not in this version. Client means the party the firm represents. Opposing party means the adverse side. A person who switches sides across matters would be stored twice. |
| Does the system remember old courts? | No. `legal_case.court_id` is the current forum. Court-transfer history is out of scope. |
| Are hearings a table? | Yes, since migration 0003: `hearing`, with one row per listing. `case_note` holds remarks. `legal_case.status` plus `case_status_audit` still record overall progress. |
| Which courts are stored? | The forums this sample firm appears before, not every court in India. |

The sample data uses Bengaluru and Karnataka so the rows are concrete. Edit `database/sample_data.sql` and `backend/app/seed.py` if the firm should sit in another city. The table shapes do not depend on that city.

Organisations use the same name columns as people. "Helios Components" / "Pvt Ltd" is a client. A separate organisation entity was not added.

## 3. How to run it

[README.md](README.md) has the Linux commands. PostgreSQL is the database the paper should describe. The schema comes from Alembic migrations in `backend/migrations/`, which create every trigger, view, function and partial index. MongoDB migrations are in `backend/mongo_migrations/`.

Roles are `admin`, `lawyer`, and `staff`, enforced in `backend/app/core/permissions.py`. A login links to its lawyer record through `users.lawyer_id`.

### The loaded sample

Twelve matters, six lawyers, eight clients, eight opposing parties, twelve evidence rows, four courts, four practice groups, six dispute locations, and eight pincodes. All of them are in Bengaluru. Filing dates run from 2 February 2024 to 4 March 2026.

| Case number | Status | Type | Court | Lead |
|---|---|---|---|---|
| OS 112/2024 | Disposed | Civil | City Civil Court | Meera Nair |
| CC 448/2024 | Hearing | Criminal | Chief Metropolitan Magistrate | Ananya Rao |
| MC 77/2025 | Pending | Family | City Civil Court | Farah Khan |
| CP 19/2024 | Disposed | Corporate | Debt Recovery Tribunal | none active |
| CC 902/2025 | Hearing | Criminal | Chief Metropolitan Magistrate | Ananya Rao |
| OS 640/2025 | Filed | Civil | City Civil Court | Meera Nair |
| MC 210/2025 | Hearing | Family | City Civil Court | Farah Khan |
| OS 113/2024 | Disposed | Civil | City Civil Court | Rohan Desai |
| CC 771/2025 | Filed | Criminal | Chief Metropolitan Magistrate | Vikram Iyer |
| CRL.A 55/2026 | Hearing | Criminal | High Court of Karnataka | Ananya Rao |
| G&W 14/2026 | Pending | Family | City Civil Court | Farah Khan |
| OA 88/2026 | Filed | Corporate | Debt Recovery Tribunal | Arjun Menon |

Counts: Filed 3, Hearing 4, Disposed 3, Pending 2. Disposal rate on this sample is 25 percent (3 of 12). Matter types: Civil 3, Criminal 4, Family 3, Corporate 2.

CP 19/2024 is the assignment-history example. Meera Nair was lead until 1 November 2024. Arjun Menon is still an associate, and `end_date` is null on his row. There is no active lead. Workload counts ignore rows whose `end_date` is set.

On PostgreSQL the trigger sets `repeat_party` for Oasis Retail, Prakash George, State Prosecution, and Neelam Joshi, because each is linked to two matters. The SQLite seed writes those four flags directly. The other four opposing parties appear once.

Case 1 cites two provisions, Specific Relief Act 5 and CPC Order VII. Every other sample matter cites one. The criminal rows use BNS 115, BNSS 419, and NI Act 138. There is no IPC section in the sample. The column can store one.

Evidence files in the sample have `mongo_id` null. The twelve rows are metadata only.

## 4. Schema

```text
practice_group
    └── lawyer
            └── case_lawyer ── legal_case ── court ── pincode_area
                    │              │
                    │              ├── location ── pincode_area
                    │              ├── case_client ── client ── client_phone_no
                    │              ├── case_opposing_party ── opposing_party ── opposing_party_phone_no
                    │              ├── matter_type
                    │              ├── statute_section
                    │              ├── evidence ── mongo_id ── MongoDB
                    │              └── case_status_audit
                    └── evidence.lawyer_id
```

### practice_group

| Column | Role |
|---|---|
| group_id | Primary key |
| group_name | Team name |
| description, email, contactno | Group contact details |

### lawyer

| Column | Role |
|---|---|
| lawyer_id | Primary key |
| fname, lname | Name |
| designation | Partner, Senior Associate, Associate |
| phoneno | Phone |
| bar_id | Bar enrolment number, unique |
| group_id | Foreign key to practice_group. A lawyer has one group. |

### pincode_area and location

`pincode_area` holds city, district, and state. `location` holds landmark, street, and pincode. City does not sit on `location`, because city, district, and state are determined by pincode. That is the 3NF example, and it is unchanged.

`court` also references `pincode_area`. A court address and a dispute address can share a pincode master without being the same entity.

### court

| Column | Role |
|---|---|
| court_id | Primary key |
| court_name | Forum name |
| court_type | Free text. The sample uses City Civil Court, Magistrate Court, High Court, and Tribunal. There is no check constraint on this column. |
| pincode | Foreign key to pincode_area |

### legal_case

| Column | Role |
|---|---|
| case_id | Primary key |
| matter_title, matter_description | What the matter is |
| case_number | Unique docket or case number |
| date_cause | Date of the cause of action |
| date_filed | Date of filing. A check requires `date_filed >= date_cause`. A trigger also rejects a future cause date or a future filing date. |
| status | Filed, Hearing, Pending, or Disposed |
| court_id | Current forum. Nullable only so a matter can be opened before the forum is known. |
| location_id | Place connected to the dispute |

There is no `lawyer_id` on this table.

### case_lawyer

| Column | Role |
|---|---|
| case_id, lawyer_id | Composite primary key. One row per lawyer per matter. |
| role | Lead Counsel, Associate, or Research |
| assigned_date | When the instruction started |
| end_date | Null while the instruction is active. Must be on or after `assigned_date`. |

A second stint by the same lawyer on the same matter would collide with the composite key. This version keeps one row per pair and updates it. A full assignment history of repeated instructions would need a surrogate key. That limit is acceptable here.

PostgreSQL also has:

```sql
CREATE UNIQUE INDEX one_active_lead_per_case
    ON case_lawyer (case_id)
    WHERE role = 'Lead Counsel' AND end_date IS NULL;
```

That partial unique index is the rule "one active lead counsel". It is not created by SQLAlchemy on SQLite, because a plain unique index on `case_id` would wrongly allow only one lawyer per matter. `assign_lawyer_to_case` and `POST /api/v1/cases/{id}/lawyers` end the previous active lead before inserting a new one. The index is what still rejects a bad insert that bypasses the API.

The SQL function sets the previous lead's `end_date` to the new assignment date. That date has to fall on or after the previous lead's `assigned_date`, or the date check rejects the update. The API route uses the later of the two dates, so an earlier new date still leaves a valid row.

### Parties

`client` and `opposing_party` share the shape fname, lname, email, address, sex. Sex is M, F, or O.

`client.notes` replaces the old injury description.

`opposing_party.repeat_party` is set by the trigger `mark_repeat_opposing_party` when that party is linked to more than one matter. On SQLite the seed sets the flag directly, because the trigger is not installed.

Phone numbers are separate tables, `client_phone_no` and `opposing_party_phone_no`, each with a composite primary key of person plus number. A phone number is multi-valued, so it does not sit as repeating columns on the person.

`case_client` and `case_opposing_party` are composite-key junction tables. They do not carry a role column. The side of the case is implied by which table the row is in.

### matter_type and statute_section

Both are composite primary keys of `(case_id, value)`. A matter can be tagged with more than one type or provision, and the same value is not stored twice on the same matter. The sample uses one type per matter: Civil, Criminal, Family, or Corporate.

`statute_section` is act-agnostic. The sample contains provisions such as NI Act 138, BNS 115, CPC Order VII, and Companies Act 241. It can also store an IPC section. The column name is not `ipc_section` because the firm is not limited to the Penal Code.

### evidence

| Column | Role |
|---|---|
| evidence_id | Primary key |
| description | What the item is |
| filed_date | When it was filed or received. Cannot precede `date_cause`. |
| mongo_id | MongoDB document id. Null when no file has been uploaded. |
| status | Received, Under Review, Filed, or Produced |
| lawyer_id | Who filed it. This stays many-to-one. It is not part of `case_lawyer`. |
| case_id | The matter. Deleting the matter deletes its evidence rows. |

### case_status_audit

| Column | Role |
|---|---|
| audit_id | Primary key |
| case_id | The matter |
| old_status, new_status | The change |
| changed_at | Timestamp |
| changed_by | Database user by default |

`legal_case.status` is only the current value. The audit table is the history. Do not add a second history table.

### users

Login accounts are separate from `lawyer`. A login can be an admin or a records clerk who is not counsel. `lawyer1` is an application user, not a foreign key to `lawyer`. Linking a login to a lawyer row was left out so authentication stays independent of the matter schema.

## 5. Relationships to use in the paper

| Relationship | Cardinality | Where it lives |
|---|---|---|
| Practice group to lawyer | One to many | `lawyer.group_id` |
| Lawyer to matter | Many to many | `case_lawyer` |
| Client to matter | Many to many | `case_client` |
| Opposing party to matter | Many to many | `case_opposing_party` |
| Matter to court | Many to one | `legal_case.court_id` |
| Matter to location | Many to one | `legal_case.location_id` |
| Location or court to pincode | Many to one | `pincode` |
| Pincode to city, district, state | Functional dependency | `pincode_area` |
| Matter to evidence | One to many | `evidence.case_id` |
| Matter to status history | One to many | `case_status_audit` |
| Matter to matter type | One to many, composite key | `matter_type` |
| Matter to statute | One to many, composite key | `statute_section` |
| Evidence metadata to file | One to one pointer | `mongo_id` |

## 6. Normalization you can still defend

**1NF.** Phone numbers, matter types, and statute sections are not repeating groups. Each is its own row. Names are atomic at the level this schema needs: one given name and one surname. Organisation names are forced into those two columns, which is a modelling compromise, not a repeating group.

**2NF.** On `case_lawyer`, role and dates describe the pair `(case_id, lawyer_id)`, not one half of the key. On `matter_type` and `statute_section` the value is part of the key, so there is no non-key attribute that could depend on only one part. On `client_phone_no` the same is true.

**3NF.** City, district, and state depend on pincode, not on location id and not on court id. They live in `pincode_area`. Court name and court type depend on court id, so they live on `court` rather than being copied onto every matter. Lawyer designation and bar number depend on lawyer id, so they are not copied onto `case_lawyer`.

**The redundancy that was rejected.** Keeping a `lead_lawyer_id` on `legal_case` as well as a lead row in `case_lawyer` would store the same fact twice. The view `active_matters_view` and the function `get_complete_case_details` read the active lead from `case_lawyer` instead.

## 7. Integrity objects

These are created by `0001_baseline.sql`.

**Checks.** Status values, evidence status, assignment role, sex, filing date against cause of action, and assignment end date against start date.

**Triggers.**

| Trigger | Effect |
|---|---|
| `validate_case_dates` | Rejects a filing before the cause of action, or a future cause or filing date. |
| `validate_evidence_filed_date` | Rejects evidence dated before the cause of action or in the future. |
| `case_status_audit` | On a real status change, inserts `old_status` and `new_status`. |
| `evidence_advances_status` | The first evidence insert moves a Filed matter to Hearing. |
| `mark_repeat_party` | Sets `repeat_party` when an opposing party is linked to a second matter. |

The sample evidence rows are inserted with `evidence_advances_status` disabled, then the trigger is turned back on. Otherwise every Filed sample matter that has an evidence row would be forced to Hearing.

**Functions.**

| Function | Effect |
|---|---|
| `assign_lawyer_to_case(case_id, lawyer_id, role, assigned_date)` | Validates both ids, ends any other active lead, then inserts or updates `case_lawyer`. |
| `dispose_case(case_id, lawyer_id)` | Sets status to Disposed and warns if the matter has no evidence. |
| `practice_group_report(group_id)` | Workload for the lawyers in one group. |
| `get_complete_case_details(case_id)` | One row with lead, court, parties, types, provisions, and evidence count. |
| `get_opposing_party_history(party_id)` | Matters linked to one adverse party. |
| `search_cases(start, end, city, status)` | Filter on cause date, city, and status. |

**Views.**

| View | Contents |
|---|---|
| `active_matters_view` | Filed, Hearing, and Pending matters, with lead counsel and current court |
| `locality_caseload_view` | Matter counts by dispute location |
| `monthly_matter_stats` | Filings and disposal rate by month of `date_filed` |
| `lawyer_performance_view` | Active instructions only (`end_date` is null) |
| `opposing_party_profile_view` | Party, repeat flag, and matter list |

**Indexes.** Status, court, filing date, and location on `legal_case`. Lawyer id on `case_lawyer`. Case id and `mongo_id` on `evidence`. Plus the partial unique index on the active lead.

## 8. What changed from the police schema

| Before | After | Kind of change |
|---|---|---|
| department | practice_group | Rename. Same one-to-many shape. |
| officer | lawyer | Rename. `rank` became `designation`. `bar_id` was added. |
| crime_case.officer_id | removed | The structural change. |
| — | case_lawyer | New junction table. |
| — | court | New master table. `legal_case.court_id` points at it. |
| crime_case | legal_case | Rename. `fir_no` became `case_number`. `date_occ` became `date_cause`. `date_rep` became `date_filed`. |
| victim | client | Rename. `injury_details` became `notes`. |
| is_victim | case_client | Rename of the existing junction. |
| suspect | opposing_party | Rename. `hascriminalrec` became `repeat_party`. |
| is_suspect | case_opposing_party | Rename of the existing junction. |
| crime_type | matter_type | Same composite key. |
| ipc_section | statute_section | Same composite key. |
| evidence | evidence | `collection_date` became `filed_date`. `officer_id` became `lawyer_id`. Status values changed. `mongo_id` stayed. |
| case_status_audit | case_status_audit | Kept. It already was the history table. |
| location, pincode_area | unchanged in structure | Still the dispute place and the 3NF geography table. |
| users | users | Roles are admin, lawyer, staff. |

Status vocabulary, changed everywhere it is checked:

| Before | After |
|---|---|
| Open | Filed |
| Under Investigation | Hearing |
| Pending | Pending |
| Closed | Disposed |

Evidence status vocabulary:

| Before | After |
|---|---|
| Collected | Received |
| Analyzed | Under Review |
| In Storage | Filed |
| Presented in Court | Produced |

The API paths changed with the names: `/api/v1/lawyers`, `/clients`, `/opposing-parties`, `/cases`, `/courts`, `/practice-groups`, `/evidence`. Analytics paths are `/analytics/dashboard`, `/analytics/cases/by-status`, `/analytics/cases/by-month`, `/analytics/cases/by-matter-type`, `/analytics/cases/trend`, `/analytics/locations/caseload`, `/analytics/lawyers/performance`, `/analytics/practice-groups/statistics`, `/analytics/opposing-parties/repeat`, `/analytics/clients/statistics`, and `/analytics/evidence/statistics`.

The sidebar labels are Dashboard, Cases, Lawyers, Opposing parties, Clients, Evidence, and Analytics. The Cases page heading is Matters. The React files are still named `Officers.jsx`, `Suspects.jsx`, and `Victims.jsx`. The routes those files serve are `/lawyers`, `/opposing-parties`, and `/clients`.

## 9. What was left out on purpose

- A `law_firm` table with one row.
- A unified `party` supertype.
- `case_court` history of transfers.
- A `hearing` table.
- A document-version table.
- A cached `lead_lawyer_id` on the matter.
- Modelling every court in India.
- Retraining inside this change. The pipeline is pointed at the new tables. The fitted files from the crime data are not valid for it.

Hearings are the feature that would describe "how the case is going" more precisely than a four-value status. They were left out because they would be a new module across the database, the API, and the UI. Status plus `case_status_audit` is the progress mechanism in this version.

## 10. Documents

PostgreSQL row: description, dates, status, lawyer, matter, `mongo_id`.

MongoDB database name: `law_firm_documents`. Collection: `evidence_files`. Each document stores `filename`, `content_type`, `size`, `upload_date`, `file_data`, `evidence_description`, and `case_id`. The bytes sit in `file_data`. This is a normal MongoDB document, not GridFS. A single document cannot exceed MongoDB's 16 MB limit, so a larger scan will fail on upload. GridFS would be a later change if the firm needs bigger files.

A create request with no file stores the PostgreSQL row and leaves `mongo_id` null. That is how the sample rows are stored. A create request with a file writes MongoDB first. If that write fails, the API returns an error and does not insert the PostgreSQL row. If MongoDB succeeds and the PostgreSQL commit then fails, the file is left with no metadata row. There is no distributed transaction across the two databases. The paper should describe that split as it is: PostgreSQL is the system of record for which file belongs to which matter, and MongoDB holds the bytes.

## 11. Learning models

Three models already exist. Their algorithms were not replaced.

| Model | Code | What it should mean now |
|---|---|---|
| Matter-type classifier | Random Forest and XGBoost in `crime_classifier.py` | Predict Civil, Criminal, Family, or Corporate from the description, dates, city, district, filing delay, evidence count, and party counts. |
| Locality concentration | `hotspot_predictor.py` | Which dispute locations account for more of the firm's matters. It does not use coordinates. Do not call it spatial prediction. |
| Intake forecast | ARIMA in `time_series_forecaster.py` | Count of matters by `date_filed`. |

The extractor in `data_extractor.py` reads the new tables and still returns the old column names (`crime_case_id`, `date_occ`, `crime_types`, `suspect_count`, `victim_count`) so the feature code did not have to change. In that frame, `suspect_count` is the opposing-party count and `victim_count` is the client count. For the classifier and the locality model, `date_occ` is `date_cause`. For the forecaster, `date_occ` is `date_filed`.

The Python classes are still `CrimeDataExtractor`, `CrimeTypeClassifier`, `CrimeHotspotPredictor`, and `CrimeTimeSeriesForecaster`. Saved classifier files are still named `crime_classifier_random_forest.pkl` and `crime_classifier_xgboost.pkl`. The AI routes are still under `/api/v1/ai`, and several of their response fields still say `crime`. The desktop app does not call those routes. Treat the names as the old pipeline, retargeted.

The classifier label is the first value in `matter_type` for that matter. The sample has one type per matter, so the first value is the only value. Features are TF-IDF on `matter_description` (100 terms), plus hour, day of week, day of month, month, quarter, weekend flag, encoded city, encoded district, evidence count, opposing-party count, client count, filing delay, and status. Status encoding is Filed = 0, Hearing = 1, Disposed = 2, Pending = 3.

`date_cause` is a date, not a timestamp. The hour feature is therefore always 0. It will not help the model. City and district are also constant on the Bengaluru sample, so those two encoded features are constant until you load matters from more than one city.

The locality model counts a matter as open only when `status` is Filed. Hearing and Pending are not in that count. Its "recent 30 days" window uses `date_cause`, not `date_filed`. The clustering step is still named spatial clustering. Its inputs are counts and rates. There is no latitude or longitude.

You do have to retrain. The files produced on 18 January 2026 were fit on crime narratives and crime-type labels. Those numbers (Random Forest accuracy 0.375, XGBoost 0.75, 12 locations, 0 locations marked high risk) belong to the old dataset. Do not put them in the law-firm paper. Delete or ignore the old `.pkl` files under `backend/models/` and `backend/training_results_20260118_154607.json`.

Train from `crime_intelligence_platform/backend` against PostgreSQL. The extractor uses `STRING_AGG` and `EXTRACT`, which SQLite will not run.

```bash
python train_models.py --db-url "postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/law_firm_db"
```

The 12 sample matters are enough to prove the pipeline runs. They are not enough for a stable classifier or a meaningful forecast. Daily resampling from 2 February 2024 to 4 March 2026 produces more than 30 points, so the forecaster's length check passes. Almost every day in that series is a zero. The model will mostly memorise a toy set. Report that sample size if you publish those metrics. For a result you are willing to discuss, load a larger corpus using the mapping below, or label a few hundred of the firm's own matters.

The optional ML packages are in `requirements-ml.txt`. Without them the API still serves matters, and the AI routes stay off.

## 12. Datasets

No public dataset is shaped exactly like this schema. Each link below is a real corpus, and each one fills a different column. Read the licence before you train. Several Indian legal corpora are academic-only.

### Matter type (the current classifier)

The matching training table is your own `legal_case` plus `matter_type`, once it has more than the 12 sample rows. Features come from `matter_description`, `date_cause`, `date_filed`, the pincode's city and district, evidence counts, and party counts. The label is `matter_type`.

There is no public Indian corpus labelled Civil / Criminal / Family / Corporate in those four words.

Use these as sources of text, then assign `matter_type` yourself:

- [IL-TUR, Legal Statute Identification](https://huggingface.co/datasets/Exploration-Lab/IL-TUR). Task card: [LSI](https://exploration-lab.github.io/IL-TUR/docs/tasks/legal-statute-identification-lsi/). About 65,000 Indian Supreme Court and High Court fact passages, each labelled with IPC sections from a set of 100. Load the `LSI` config. Map every row to matter type Criminal, because the statutes are penal. That gives you a large Criminal class and no Family or Corporate class. It is useful as criminal text, not as a four-way matter-type benchmark.
- [LexGLUE, SCOTUS](https://huggingface.co/datasets/coastalcph/lex_glue). Issue-area classification of US Supreme Court opinions. This is the closest public task to "predict the kind of case", and it is not Indian law. Use it only as a method check, and say the jurisdiction is different. Code and paper: [coastalcph/lex-glue](https://github.com/coastalcph/lex-glue).

A practical labelling rule if you import statute tags yourself:

| If the provisions are mainly under | Set matter_type |
|---|---|
| IPC, BNS, NI Act, BNSS | Criminal |
| Hindu Marriage Act, guardianship, maintenance | Family |
| Companies Act, insolvency, DRT statutes | Corporate |
| Contract Act, Specific Relief Act, CPC | Civil |

That rule is a heuristic. A civil matter can cite a penal section. Review a sample before you trust the label.

### Statute sections (a better legal task, if you extend the model)

The current model predicts one matter type. Predicting the provisions in `statute_section` is a multi-label task. These corpora match that task. They do not drop straight into the current Random Forest without a new label format.

- [IL-TUR LSI](https://huggingface.co/datasets/Exploration-Lab/IL-TUR) and the task page above. Labels are IPC section ids.
- [LeSICiN](https://github.com/Law-AI/LeSICiN). Facts from Indian courts, IPC sections, and a citation graph. AAAI 2022 dataset.
- [AILA 2019](https://github.com/Law-AI/aila-2019-dataset). Download: [Zenodo 4063986](https://zenodo.org/records/4063986). About 3,000 Supreme Court documents, 197 statutes, and 50 situation queries. Task 2 is statute retrieval. Track page: [FIRE 2019 AILA](https://sites.google.com/view/fire-2019-aila/).

### Judgment text, and why not to use it as matter type

- [ILDC / CJPE](https://github.com/Exploration-Lab/CJPE). Paper: [ACL 2021](https://aclanthology.org/2021.acl-long.313/). About 35,000 Indian Supreme Court documents. The same material is the CJPE task inside [IL-TUR](https://huggingface.co/datasets/Exploration-Lab/IL-TUR).
- Licence: CC BY-NC 4.0. Academic use, with citation. Not for a commercial product.
- The label is appeal accepted or rejected. That is an outcome, not a matter type. Do not train the current classifier on that label and then describe the result as matter-type accuracy.
- You can use the text as `matter_description`. The case id often starts with a year (`1951_10`), which is enough for a coarse yearly filing count, not for a daily `date_filed` series.

### Locality concentration

Train this model on your own `location` and `pincode_area` tables. Public judgment corpora do not include the firm's dispute landmarks and pincodes.

For context in the paper, not as a training file:

- [National Judicial Data Grid](https://njdg.ecourts.gov.in/njdgnew/index.php). Court-wise pendency for Indian district and subordinate courts.
- [data.gov.in](https://www.data.gov.in/). Search for pending cases in district and subordinate courts. Those releases are state or district aggregates. They do not join to `location_id`.

### Intake forecast

The series the forecaster expects is a count by `date_filed`. Build it from `legal_case` after you have a real filing history. ILDC can supply a yearly count. NJDG can supply a picture of court pendency. Neither is a drop-in daily series for this firm.

### Optional language model

[InLegalBERT](https://huggingface.co/law-ai/InLegalBERT) is a pretrained model on Indian legal text. The current pipeline uses TF-IDF, not this model. Cite it only if you later replace the text features. Swapping it in is a different experiment from retraining the existing forest and boosting models.

### How a downloaded row becomes a database row

| Corpus field | Schema column |
|---|---|
| Facts or judgment text | `legal_case.matter_description` |
| Your Civil / Criminal / Family / Corporate label | `matter_type.matter_type` |
| IPC or other section ids | `statute_section.statute_section` |
| Case identifier | `legal_case.case_number` |
| Decision date or year, if that is all you have | `legal_case.date_filed`, and set `date_cause` on or before it |
| Court name, if present | `court.court_name`, then `legal_case.court_id` |

Leave client, opposing party, and lawyer empty unless the source actually names them. Do not invent parties in order to make the classifier look more complete. The classifier does not need those names. It uses counts.

## 13. Novelty and industry relevance

### What is not new

Normalization through third normal form is not a contribution of this project. Partial unique indexes, triggers, junction tables, and storing files outside the relational database are established tools. Commercial practice-management products already keep matters, lawyers, clients, documents, and court dates. Clio is one international example of that product category. Provakil is one Indian example. Manupatra and SCC Online are research libraries, not the same kind of system. eCourts and the National Judicial Data Grid already publish how cases sit in Indian courts.

A paper that says this schema invented case management, or invented a hybrid SQL and document store, will not survive a reviewer who has seen those systems.

### What is actually there to defend

The work is a design and evaluation of a relational schema for one litigation firm, with a narrow document store beside it.

The design choices that are worth the paper are these:

1. Counsel is a constrained many-to-many relationship. Several lawyers can be on one matter. One of them is the active lead, enforced by a partial unique index rather than by a second foreign key that would duplicate the fact.
2. The court and the dispute location are different entities. Both use the same pincode master, so the third-normal-form split survives the domain change. Replacing location with court would have made the geography example false and would have turned the locality model into a count of court buildings.
3. Current status and status history are separated. The history is written by a trigger, so an application that forgets to log a change still leaves a row when it updates `legal_case.status`.
4. Evidence metadata stays under relational integrity, including "this item belongs to this matter" and "this date is not before the cause of action". The bytes live in MongoDB under `mongo_id`. The paper can evaluate that split honestly, including the missing cross-database transaction.

The learning section is an application of that schema. The classifier reads the normalized matter, location, and party-count tables. The locality model aggregates by `location_id`. The forecaster aggregates `date_filed`. None of those queries needs a denormalized case blob. That is the connection between the DBMS half and the learning half. It is not a new learning method.

### Why a firm still needs this record

eCourts can tell you that a case number exists in a court. It does not tell this firm which associate is responsible, which client is being represented, which opposing party has appeared before, which version of a filing was uploaded, or how the firm's own status moved from Filed to Hearing. Those facts are the firm's operational record. They are also the facts a conflict check and a workload report need: the same client on two matters, the same opposing party on two matters, and the count of active leads per lawyer.

BNS and BNSS matter to the statute column because new criminal filings are no longer only IPC and CrPC citations. The column was named `statute_section` so both generations fit without another migration. The sample cites BNS 115 and BNSS 419. It does not cite IPC or CrPC. Older special statutes in the sample include the NI Act, the Companies Act, and the CPC.

### A paper shape that matches the system

Title direction: a normalized relational schema, with a document-store pointer, for a single firm's litigation matters.

A usable question: how should counsel, clients, the current court, dispute location, status history, and evidence files be represented so that a firm can enforce one active lead, keep a status history, and still query locality and matter type without denormalizing the case?

Suggested sections:

1. Requirements of one litigation firm, and the requirements that were declared out of scope.
2. ER model and the cardinalities in section 5.
3. Relational mapping and functional dependencies.
4. Normalization, using pincode, matter type, statute section, and the rejected lead-lawyer foreign key as the examples.
5. Integrity: checks, triggers, the partial unique index, and the assignment procedure.
6. Document storage and the consistency limit.
7. Queries the schema answers: active lead, lawyer workload, repeat opposing party, caseload by locality.
8. Learning models as consumers of those tables, with the training corpus, the sample size, and the licence stated.
9. What the evaluation does not show: no claim of a new normal form, no claim that 12 rows establish predictive performance, no claim that SQLite demonstrates the triggers.

## 14. Limits to state, not hide

- The database is one firm. A lawyer who also works outside the firm is not modelled.
- Client and opposing party are fixed sides. There is no global person who changes role per matter.
- One lawyer has at most one row on a matter. A later re-instruction overwrites that row's dates.
- Court history is the current court only.
- Hearings, cause lists, and limitation dates are not stored. Status is a four-value summary.
- Organisations share the person name columns.
- Login users are not foreign keys to lawyers.
- SQLite runs the API and the sample data. It does not run the triggers, views, functions, or the partial unique index.
- The learning extractor targets PostgreSQL.
- The January 2026 model metrics are from the crime dataset.
- ILDC and several Law-AI corpora are CC BY-NC or otherwise research-licensed. Check the dataset card you actually download.
- Writing MongoDB and then PostgreSQL is not an atomic commit.
- File bytes are stored in the `evidence_files` collection. A file larger than 16 MB will not upload.
- The hour feature in the classifier is always 0, because `date_cause` has no time.
- The locality model treats only Filed as the open status, and its recent window uses `date_cause`.
- Python class names, pickle filenames, and the `/api/v1/ai` field names still use the crime vocabulary. The tables they read do not.
- The body of `crime_intelligence_platform/README.md` still describes the police API. Use this guide for the current system. The top of that README points here.

## 15. If you change the sample city

Update both copies of the sample, or they will drift:

- `crime_intelligence_platform/backend/migrations/sql/0001_baseline.sql`
- `crime_intelligence_platform/backend/app/seed.py`

`seed.py` runs only when `legal_case` is empty. After the SQL script has loaded rows, the API will not insert a second copy.
