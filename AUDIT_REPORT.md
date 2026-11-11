# Audit report: Law Firm Case Management

Audited 22 Oct 2026. The folder is still called `crime_intelligence_platform/`.

**How it was checked.** Every source file in `backend/`, `frontend/src/`, `database/`, the docs and the config files was read. The API was run in a scratch copy against a throwaway SQLite database, so your `law_firm.db` and source files were not touched. Dataset hosts were queried for metadata only; nothing was downloaded.

**Evidence tags.** `[run]` means reproduced by running code. `[read]` means found by reading the code. `[git]` means from the git repository.

**Not covered.** PostgreSQL features (no `psql` on this machine), MongoDB, the Vite/Electron build (no `node_modules`; Electron was not launched), and the ML code itself (scikit-learn, xgboost, statsmodels and prophet are not installed here, so that part is `[read]` plus the pieces that only need pandas or SQLite).

## Overview

The project is half-migrated from a police system to a law-firm system.

- Law-firm: the database schema, the ORM, the seven API routers, and the seven screens.
- Still police: the ML package and its API route, the README body, the launcher, credentials and import notes, the Electron packaging, and a few comments.
- Nothing from the migration is committed: 37 files modified, 7 deleted, 11 untracked, plus 5,761 deleted `node_modules` files. `origin` is still the old public crime repo.

## Status: fixes so far (22 Oct 2026)

Two rounds of fixes are in. Each was re-tested on a scratch copy. The tables further down still describe the state before these fixes.

Round 1: the first six items (132 checks, all passing).

| Audit ID | What changed |
|---|---|
| S1 | `main.py`: every router except `/auth` now carries `dependencies=[Depends(get_current_active_user)]`, including courts, practice groups and the AI routes. No token or a bad token gives 401. CORS preflight and the 401 response still carry the CORS headers, and every URL the desktop app calls still returns 200 with a token. |
| S2 | `routers/auth.py`: `POST /auth/register` needs an admin token (401 without one, 403 for lawyer or staff). With an empty users table the first account is still created as admin. |
| B1 | `routers/evidence.py`: the `status` parameter of `create_evidence` is now `status_value` (the query name is still `status`, through `alias`), so the 404/400 branches work. It also rejects an invalid status with 400, and "Crime case" in two error messages now says "Matter". |
| B3 | `routers/cases.py`: the route is now `/cases/by-number/{case_number:path}`. |
| B5 | `models/models.py`: `Lawyer.assignments` has `cascade="all, delete-orphan"`, matching the `ON DELETE CASCADE` in the SQL. Deleting a lawyer removes their assignment rows; their evidence stays, with `lawyer_id` set to NULL. |
| B6 | `PUT /cases/{id}` checks the date order on the stored plus new values (400). Assignments reject an `end_date` before `assigned_date` (422). `ClientUpdate` and `PartyUpdate` validate `sex` (422). Duplicate phone numbers on client and party create are dropped. |

Round 2: the next batch, checked with a 67-case sweep of the write endpoints (before: 26 returned 500 and 6 corrupted later reads; now: none) plus 126 assertions.

| Audit ID | What changed |
|---|---|
| B4 | `routers/cases.py`: new `PATCH /cases/{id}/status?new_status=...` (400 for an invalid status, 404 for an unknown matter). It is what `casesAPI.updateStatus` already called. |
| B2 | `routers/evidence.py`: `create_evidence` takes `Form(...)` fields, so `evidenceAPI.create(formData)` works, with or without a file. Query-string calls are no longer accepted. |
| B7 | `routers/cases.py`: new `require_ids` helper. Creating a matter returns 404 for an unknown court, location, client, opposing party or lawyer (nothing is half-created), and updating one does the same for court and location. |
| B6 (rest) | Required fields can no longer be set to `null` on update (422): matter title, status and dates; lawyer, client and party names; party `repeat_party`; evidence date and status; user email, role and `is_active`. Before, `status: null` on a matter or evidence made the list endpoints return 500, `repeat_party: null` broke matter detail, and a bad role made `/auth/users` fail. A user's `role` is now validated on update. |
| duplicates | Creating a matter keeps repeated client, party, matter-type and statute values once, returns 400 if a lawyer is listed twice, and accepts `assignments: null`. A duplicate lawyer `bar_id` on create or update (including an empty string), an existing phone number on `.../phones`, and an existing email on user update now return 400 instead of 500. |

Still open:

- S1: any logged-in user, including `staff`, can still create, edit and delete. Role rules were not added.
- `PUT /evidence/{id}` can move `filed_date` before the matter's cause date (200 on SQLite; the PostgreSQL trigger would reject it, which the API would surface as a 500). Create checks this, update does not.
- B8: status changes through the API are still not audited on SQLite.
- Column length limits are enforced only by PostgreSQL (`phoneno` 15, `case_number` 50, user `full_name` 100 and so on) and several schemas do not mirror them, so over-long input would give 500 there. Not testable here.
- S3, S4, S5 (a password over 72 bytes still gives 500) and everything in sections 3 to 6 are unchanged.

## 1. Security

| # | Finding | Where | Evidence |
|---|---|---|---|
| S1 | **No data route checks a token.** Matters, lawyers, clients, opposing parties, evidence, analytics, courts, practice groups and the AI routes all answer 200 without logging in. The admin/lawyer/staff roles only guard `/auth/users*`. `core/dependencies.py` is empty. Fix: add `dependencies=[Depends(get_current_active_user)]` to the `include_router` calls and `require_role` on writes. | `main.py:77-131`, every router except `auth.py` | `[run]` |
| S2 | **Anyone can register as admin.** `POST /auth/register` is public and takes `role` from the request body. I registered `role=admin`, logged in, and listed all users. Fix: ignore `role` on public registration or require an admin token. | `routers/auth.py:38-89` (role at line 72) | `[run]` |
| S3 | **A hard-coded Postgres password is in a public repo.** Two `__main__` examples contain a full connection URL with a password. It was committed in `5244ccc`, and the GitHub repo `MedhaSanketh/crime_intelligence_platform` reports `private: false`. Rotate that password wherever it is used, read the URL from the environment, and consider scrubbing history. | `ai_models/hotspot_predictor.py:396`, `ai_models/time_series_forecaster.py:440` | `[git]` `[run]` |
| S4 | `credentials/credentials.txt` is tracked in git and lists accounts that no longer exist (`officer1` returns 401, `forensic1` is not seeded). The `.env` `SECRET_KEY` (47 chars) is a readable phrase, not random; use `secrets.token_urlsafe(48)`. The login page prints the admin and lawyer demo passwords. | `credentials/credentials.txt`, `backend/.env`, `Login.jsx:120-130` | `[run]` `[git]` |
| S5 | `UserUpdate.role` is not validated, so an admin can store any string. `get_password_hash` does not guard bcrypt's 72-byte limit: bcrypt 5 raises `ValueError`, while the schema accepts passwords up to 100 characters (register and change-password return 500). | `schemas/auth.py:33-38`, `core/security.py:32`, `schemas/auth.py:30,73` | `[run]` |

## 2. API bugs

| # | Finding | Where | Evidence |
|---|---|---|---|
| B1 | **Evidence create returns 500 instead of 404/400.** The parameter `status` shadows `fastapi.status`, so every error branch raises `AttributeError: 'str' object has no attribute 'HTTP_404_NOT_FOUND'`. This covers a missing matter, a missing lawyer, a date before the cause date, and a MongoDB failure. Rename the parameter. | `routers/evidence.py:71` vs `91, 100, 107, 137` | `[run]` |
| B2 | **`evidenceAPI.create` cannot work.** It sends multipart `FormData`, but the endpoint reads `description`, `filed_date`, `status`, `lawyer_id` and `case_id` as query parameters. Result: 422 "Field required: query.filed_date, query.case_id". No screen calls it yet. Use `Form(...)` parameters. | `services/api.js:90`, `evidence.py:68-76` | `[run]` |
| B3 | **`GET /cases/by-number/{case_number}` can never match.** Every sample case number contains `/` (`OS 112/2024`). It returns 404 even when URL-encoded. Use `{case_number:path}`. | `routers/cases.py:148` | `[run]` |
| B4 | `casesAPI.updateStatus` calls `PATCH /cases/{id}/status`, which does not exist (404). Only evidence has that endpoint. | `services/api.js:55` | `[run]` |
| B5 | **Deleting a lawyer who has assignments returns 500** (`AssertionError: ... blank-out primary key column 'case_lawyer.lawyer_id'`). The relationship has no cascade or `passive_deletes`. | `models/models.py:76` | `[run]` |
| B6 | **Update/create schemas skip checks the database enforces, so bad input returns 500 instead of 422/400.** Cases: `PUT` with `date_filed` before `date_cause`. Clients and parties: `sex="X"` on update. Assignments: `end_date` before `assigned_date`. Clients and parties: duplicate phone numbers on create. | `schemas/legal_case.py:72-86`, `client.py:26-32`, `opposing_party.py:26-32`, `AssignmentCreate`, `routers/clients.py:31` | `[run]` |
| B7 | **No existence checks for `court_id`, `location_id`, `client_ids` or `party_ids`.** SQLite runs with `PRAGMA foreign_keys = 0`, so creating a case with `court_id: 999` and `client_ids: [999]` returned 201 and left an orphan `case_client` row. On PostgreSQL the same call would be a 500. Enable the pragma on connect and validate ids. | `routers/cases.py:57-87`, `database.py` | `[run]` |
| B8 | **Status changes are not audited on SQLite.** After a status change the audit table stayed at 2 rows, and no endpoint exposes `case_status_audit` at all. The history only exists on PostgreSQL (trigger). | `routers/cases.py:179-186` | `[run]` |
| B9 | After creation a matter cannot get new matter types, statute sections, clients or opposing parties, and an assignment cannot be removed. `PUT /cases/{id}` ignores them. | `routers/cases.py:179` | `[read]` |
| B10 | Upload rules are declared but never enforced: `MAX_FILE_SIZE` (10 MB), `ALLOWED_FILE_TYPES` (no Word or text files) and `UPLOAD_DIR`. The guide says the limit is 16 MB. `upload-file` deletes the old Mongo document before inserting the new one, so a failed insert leaves the row pointing at nothing. `get_file_from_mongo` turns its own 404 into a 400 "Invalid MongoDB ID", and `get_evidence` uses a bare `except: pass`. | `config.py:33-40`, `evidence.py:43-60, 271-272, 376-390` | `[read]` |
| B11 | Two evidence-statistics endpoints with different shapes (`/evidence/statistics/summary` uses snake_case keys; `/analytics/evidence/statistics` uses label keys). All handlers are `async def` over blocking SQLAlchemy sessions, and the list endpoints run one extra query per row. | `evidence.py:575`, `analytics.py:274` | `[run]` |
| B12 | `/analytics/cases/trend` accepts `period` but ignores it. The window ends today, so the sample data (last filing 4 Mar 2026) gives an all-zero series. | `analytics.py:109-137` | `[run]` |

## 3. Frontend and Electron

| # | Finding | Where | Evidence |
|---|---|---|---|
| F1 | **A packaged Electron build will almost certainly show a blank window.** It loads `dist/index.html` over `file://`, but Vite has no `base: './'` (the built HTML references `/assets/...`), the app uses `BrowserRouter` (needs `HashRouter`), the 401 handler does `window.location.href = '/login'`, and the CORS list has no file origin. `public/icon.png` is referenced and missing. Dev mode (`npm run electron:start`) is not affected. | `electron/main.js:12,21`, `vite.config.js`, `App.jsx:2`, `api.js:34`, `package.json` build block | `[read]` (not launched) |
| F2 | The existing `frontend/dist/` is a build of the police app: the bundle contains "Crime Intelligence", "Officers", "Suspects", "Victims" and no "lawyer" or "opposing". Rebuild or delete it. | `frontend/dist/` | `[run]` |
| F3 | Stale branding: package name `crime-intelligence-platform`, description "Crime Intelligence and Predictive Investigation Platform", `appId com.crimeintelligence.app`, `productName "Crime Intelligence Platform"`, HTML `<title>frontend</title>`, and `frontend/README.md` is the Vite template. | `frontend/package.json:2,4,19,20`, `index.html` | `[read]` |
| F4 | `strictPort: false`: if 5173 is busy Vite moves to 5174, but Electron is hard-coded to 5173. | `vite.config.js:9` | `[read]` |
| F5 | **The UI is read-only.** Seven list/dashboard pages plus a file download; no create, edit, delete or upload anywhere. Every write function in `api.js` is unused. The README promises "case management". | `src/pages/*` | `[read]` |
| F6 | Evidence download always saves as `evidence_<id>.file` instead of the real name. The opposing-parties filter says "Repeat party" but its options read "Has Record / No Record" (variable `criminalRecordFilter`). `Dashboard.jsx` imports an unused `Cancel`. | `Evidence.jsx:70`, `Suspects.jsx:92-98` | `[read]` |
| F7 | A stray root `package.json` pins MUI 7.3.6 while the frontend uses MUI 5.18 (the code uses the v5 `Grid item` API). The root `node_modules/` was committed: 5,761 tracked files, all deleted in the working tree. | `package.json`, `package-lock.json` | `[git]` |

## 4. Database and SQL

| # | Finding | Where | Evidence |
|---|---|---|---|
| D1 | **`lawyer_performance_view` multiplies active/disposed counts by the lawyer's evidence rows.** On the seed: Ananya Rao has 4 matters and shows 8 active; Farah Khan has 3 and shows 9; Rohan Desai has 3 matters and shows 4 disposed. The API (`/analytics/lawyers/performance`) returns 4/3/3, so the view and the app disagree. Use `count(DISTINCT CASE ... lc.case_id END)` as `practice_group_report` already does. | `law_firm_schema.sql:641-661` | `[run]` (SELECT body on SQLite seed) |
| D2 | `locality_caseload_view` and `get_location_crime_counts` count `lc.case_id` after joining `matter_type`, so a matter with two types is counted twice. Giving matter 2 a second type changed location 1 from 2 to 3. Latent today (one type per sample matter), but the schema allows many. | `law_firm_schema.sql:607-626`, `data_extractor.py:119-141` | `[run]` |
| D3 | **`law_firm_schema.sql` and `seed.py` have drifted** even though the guide says they must match. Phones: 4+3 rows vs 2+1. Status audit: 10 rows vs 6 (the SQL has Filed to Hearing for matters 5, 7, 8, 10; the seed goes straight from Filed to Disposed for matter 8). Client notes, all 12 matter descriptions, and several evidence descriptions use different text. The descriptions are the classifier's input, so the two backends train on different text. | `law_firm_schema.sql:725-878` vs `seed.py:62-181` | `[run]` `[read]` |
| D4 | Sample realism: CP 19/2024 (oppression and mismanagement, Companies Act s.241) is assigned to the Debt Recovery Tribunal. That petition goes to the NCLT; the DRT hears recovery under the RDDBFI Act (like OA 88/2026). | `seed.py:89`, SQL line 769 | `[read]` |
| D5 | ORM and SQL differ in small ways: `case_status_audit.changed_at/changed_by` and `case_lawyer.assigned_date` have defaults only in SQL; the `users.role` CHECK exists only in SQL. `evidence.case_id` is nullable in both although the guide says every item belongs to a matter. | `models/models.py`, `models/user.py` | `[read]` |
| D6 | SQLite *can* enforce "one active lead": `Index("one_active_lead_per_case", "case_id", unique=True, sqlite_where=..., postgresql_where=...)` in the ORM gives the same rule on both. The guide treats the gap as inherent. | `models/models.py:150-173` | `[read]` |
| D7 | Guide section 4 names the trigger `mark_repeat_opposing_party`; that is the function. The trigger is `mark_repeat_party`. | `PROJECT_GUIDE.md`, `law_firm_schema.sql:566` | `[read]` |
| D8 | Verified OK: the bcrypt hashes in the SQL file match `admin123`, `lawyer123` and `staff123`; the sample counts, statuses, matter types, repeat-party flags and the CP 19/2024 assignment history in the guide match both the SQL and `seed.py`. | | `[run]` `[read]` |

## 5. ML pipeline

| # | Finding | Where | Evidence |
|---|---|---|---|
| M1 | **`POST /ai/classify/crime-type` can never succeed.** It calls `classifier.predict_with_confidence(...)`, which does not exist. It also calls `load_model()` with no path although `load_model(self, filepath)` requires one; the bare `except` then retrains and re-saves the model on every request. | `routers/ai_analytics.py:209,251`, `ai_models/crime_classifier.py:246` | `[read]` |
| M2 | The same endpoint ignores `crime_description` (TF-IDF columns are zero-filled), hard-codes city, district, status and filing delay to 0, and uses today's day of month. The `city` and `district` encoders are fitted inside `prepare_features` and never saved, so inference cannot reproduce them. | `ai_analytics.py:219-248`, `crime_classifier.py:60-63` | `[read]` |
| M3 | Training hygiene: TF-IDF and encoders are fitted on all rows before the train/test split; `hour` is always 0 (`date_cause` is a date); city and district are constant on the sample. The numbers in `training_results_20260118_154607.json` (RF 0.375, XGB 0.75) belong to the old crime data. | `crime_classifier.py:44-106` | `[read]` |
| M4 | Hotspot "risk model" predicts `recent_crimes_30d` while `recent_crimes_30d` and `recency_score` are among its features, so it learns the identity function. `historical_crimes` and `recent_crimes` in the API are normalized 0-100 scores cast to int, not counts. `load_models()` reads a `'scaler'` key that `save_models()` never writes. `/ai/hotspots` ignores `top_n`. | `hotspot_predictor.py:110-115, 275-276, 358`, `ai_analytics.py:114` | `[read]` |
| M5 | **pandas 3 removed the `'M'` alias.** `resample('M')` and `date_range(freq='M')` raise `ValueError` on the installed pandas 3.0.5, so every monthly series breaks. `requirements-ml.txt` says `pandas>=2.2` with no upper bound. Use `'ME'`. | `data_extractor.py:198-199`, `time_series_forecaster.py:69-70, 253` | `[run]` |
| M6 | **Import coupling.** `ai_models/__init__.py` imports all four modules, and `time_series_forecaster.py` imports `prophet` at module level even though only ARIMA is used. Training or using only the classifier therefore needs prophet, statsmodels and xgboost; if prophet is missing, `ML_AVAILABLE` is false and every AI route returns 503. `pmdarima` (used for `auto_order=True`) is not in `requirements-ml.txt`, so auto order always falls back to (5,1,0). | `ai_models/__init__.py:6-9`, `time_series_forecaster.py:11,126,172`, `ai_analytics.py:15-25` | `[read]` |
| M7 | The guide says the extractor needs PostgreSQL. In fact 4 of its 5 queries fail on SQLite 3.49 (`STRING_AGG(DISTINCT ...)`, `::timestamp`), but `get_crime_cases_with_location` (the only one the classifier and `train_models.py --model classifier` use) runs fine (12 rows). | `data_extractor.py` | `[run]` |
| M8 | `train_models.py` prints the DB URL including the password, ignores `.env`, writes models and the results JSON relative to the current directory, and stores a failure under `crime_classifier` while success is stored as `rf_classifier`/`xgb_classifier`. | `train_models.py:262`, `train_models.py:172-178` | `[read]` |

## 6. Docs, config and leftovers

| # | Finding | Where | Evidence |
|---|---|---|---|
| L1 | **The README is half old, half new.** DB setup was updated; the features list ("Officers", "Suspects", "Victims", "70 API Endpoints"), tech notes, structure diagram, `git clone .../crime-intelligence-platform`, the startup banner and `"role": "officer"` were not. Real `/api/v1` count is 72 (including 6 AI routes): Suspects 10 is now 8, Victims 11 is now 8, Evidence 12 is now 11. The guide (section 14) says only the body is stale; the two documents disagree. | `README.md:28-47, 77-78, 177, 341, 359` | `[run]` `[read]` |
| L2 | **Broken references.** The README top links to `../PROJECT_GUIDE.md` (the file is in the same folder). It tells you to `pip install -r requirements.txt` from `backend/`, but `requirements.txt` is in the repo root (the guide says `../requirements.txt`). `backend/requirements.txt`, `backend/create_tables.py` and `database/schema_diagram.png` do not exist. | `README.md:3, 106, 139, 167, 245, 299-320` | `[read]` |
| L3 | `database/HOW_TO_IMPORT.txt` tells you to create `crime_intelligence_db` and import the police dump, which contradicts the README and guide ("do not import"). `START_PROJECT.sh` has the police banner, a Linux-only `venv/bin/activate`, and from line 17 on contains pasted chat text ("Step 5: Package Everything for Rohith", old credentials, markdown fences). | `HOW_TO_IMPORT.txt`, `START_PROJECT.sh:17-85` | `[read]` |
| L4 | Dead files: empty `models/crime_case.py`, `officer.py`, `suspect.py`, `victim.py`; empty `services/case_service.py`, `utils/helpers.py`, `core/dependencies.py`; `tests/test_cases.py` is 0 bytes, so there are **zero tests**. Also `backend/crime_intelligence.db` (old schema, one user), the tracked `training_results_20260118_154607.json`, and stale `__pycache__` for deleted modules. | `backend/` | `[read]` |
| L5 | `requirements.txt` lists packages nothing imports (`alembic`, `motor`, `aiofiles`, `python-dateutil`, `tqdm`, `requests`, `python-dotenv`, `typing-extensions`) and mixes dev tools in (`black`, `isort`, `flake8`, `ipython`, `pytest-asyncio`). It caps `fastapi<0.143` while 0.159.1 is installed here. It claims "Python 3.14 compatible" while the README says 3.11+. | `requirements.txt` | `[run]` |
| L6 | Leftover wording: "Crime case with ID" in error messages, "officer" in comments, the old status list in an endpoint docstring, `__author__ = 'Crime Intelligence Team'`. The Python class names, `.pkl` names and `/ai` response fields are documented in guide section 11. | `evidence.py:92,95,303,525,557`, `ai_models/__init__.py:2,19` | `[read]` |
| L7 | `backend/.env` points at SQLite and its comments call PostgreSQL "the production DB per README". The guide calls `.env` "checked-in", but it is gitignored and was never committed (good). `.gitignore` lists `node_modules` four times and has no trailing newline. | `backend/.env`, `.gitignore` | `[git]` |
| L8 | The project folder is inside OneDrive. A SQLite file and `node_modules` in a synced folder can be locked or duplicated by sync. | | `[read]` |

## 7. Dataset access check

The checks were run from this machine. `huggingface.co`, `zenodo.org`, `github.com` and `pypi.org` all answered 200. Only metadata and tiny samples were fetched; **no dataset was downloaded and nothing was trained**.

| Source | Access | Licence | Size / notes |
|---|---|---|---|
| IL-TUR (Hugging Face) | **Blocked.** Gated with manual approval; the dataset card and viewer return 401 | CC BY-NC-SA 4.0 (the guide does not mention the SA part or the gating) | Configs lsi, cjpe, bail, pcr, rr, lner, summ, lmt. You need a Hugging Face account, an approved access request and a token |
| ILDC / CJPE (GitHub) | Repo is public, but its `Data/` folder holds only READMEs that point to Hugging Face (IL-TUR), so the data is behind the same gate | CC BY-NC, academic use only | Same material as the `cjpe` config inside IL-TUR |
| LexGLUE (Hugging Face) | Open | CC BY-4.0 | 7 configs; SCOTUS has 5,000 / 1,400 / 1,400 rows. US law, long opinions (~20K chars each) |
| AILA 2019 (Zenodo 4063986) | Open | CC BY 4.0 | One file, `AILA_2019_dataset.zip`, 20.7 MB. No matter-type labels |
| LeSICiN data (Zenodo 6053791) | Open | CC BY 4.0 | `train.jsonl` 320 MB, `dev` 85 MB, `test` 106 MB, embeddings 2.2 GB. Too big for a small model |
| InLegalBERT (Hugging Face) | Open | MIT | 534 MB of weights; not needed for TF-IDF |
| Other open Indian-law corpora (not in the guide) | Open | CC BY 4.0, Apache-2.0, MIT | `labofsahil/Indian-Supreme-Court-Judgments` (42,846 judgments, ~130 GB repo, metadata has no case type); `KanoonGPT/indian-case-laws` (17M High Court records; docket numbers like `CRL OP`, `WP(C)`, `RPFC` carry a case-type code, but in my sample the text field was ~400 characters and headnotes were empty, so full text is unconfirmed); `Shreyasrao/Indian-law-supreme-court-judgements-2016` (589 judgments; the text preview starts with the appeal number, e.g. "Civil Appeal No. 2140 of 2016", which would allow a civil/criminal label) |
| NJDG, data.gov.in | Reachable | Government open data | Aggregates only; context, not training data |

None of these is labelled Civil / Criminal / Family / Corporate (the guide already says so).

**Machine:** AMD Ryzen 9 7940HS (8 cores), 15 GB RAM, 640 GB free. Python 3.12.10 with pandas 3.0.5 and torch 2.6; scikit-learn, xgboost, statsmodels and prophet are not installed. A TF-IDF plus logistic-regression model needs only scikit-learn and trains in seconds on the CPU.

## 8. Suggested order of fixes

1. Rotate the leaked Postgres password (S3) and decide whether to scrub git history.
2. Close the auth holes (S1, S2), then fix B1, B3, B5 and B6.
3. Fix the ML endpoint contract before training anything (M1, M2, M5, M6), or replace the classifier with a small `Pipeline(TfidfVectorizer -> LogisticRegression)` that saves one file and has one `predict` path.
4. Fix `lawyer_performance_view` (D1) and sync `seed.py` with the SQL (D3).
5. Clean up the docs and leftovers (L1-L4), rebuild or delete `dist/` (F2), and fix the Electron packaging only if you plan to ship an installer (F1).
6. Commit the migration on a new branch, and point `origin` at a new repo if the old one should stay a crime project.
