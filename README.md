# Law Firm Case Management

A desktop app for running one litigation firm: matters, lawyers, clients, opposing parties, evidence and analytics. The design, schema and paper notes are in [PROJECT_GUIDE.md](PROJECT_GUIDE.md).

Do not import `database/crime_intelligence_db_backup.sql`. It is the old police schema, kept only for reference.

## Tech stack

| Part | Tools |
|---|---|
| Backend | FastAPI, SQLAlchemy, Pydantic, JWT |
| Database | PostgreSQL. MongoDB is optional and only stores evidence files |
| Frontend | Electron, React, Material UI, Recharts, Axios |
| ML | scikit-learn, statsmodels |

## Running on Linux

Commands are marked:

- **ONE-TIME**: run once per machine.
- **EVERY TIME**: run each time you start the app.
- **OCCASIONAL**: run only when the stated condition applies.

All commands start from the project root unless they show a `cd`.

### Short version

If setup is already done, open two terminals:

```bash
# Terminal 1: backend
docker start law-firm-postgres    # skip if you installed PostgreSQL with apt
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

```bash
# Terminal 2: frontend
cd frontend
npm run electron:start
```

## First-time setup

### 1. Install the prerequisites (ONE-TIME)

You need Python 3.11+ (tested on 3.14), Node.js 18+ (tested on 22), and either Docker or PostgreSQL.

```bash
python3 --version
node -v
docker --version
```

### 2. Create the database and load the schema (ONE-TIME)

Choose **one** option. Both create `law_firm_db` and load its tables, triggers, views, functions and sample data.

> **Warning:** `law_firm_schema.sql` starts by dropping every table. Running it again **deletes all data** and restores the sample firm. Only re-run it if you want that reset.

Replace `YOUR_PASSWORD` with a password of your choice. You will use the same one in step 3.

**Option A: Docker**

Skip the `docker run` if `docker ps -a` already lists `law-firm-postgres`.

```bash
# ONE-TIME: create the container and the empty database
docker run -d --name law-firm-postgres --restart unless-stopped \
  -e POSTGRES_PASSWORD=YOUR_PASSWORD \
  -e POSTGRES_DB=law_firm_db \
  -p 5432:5432 \
  -v law_firm_pgdata:/var/lib/postgresql/data \
  postgres:16

# Wait until this prints "accepting connections"
docker exec law-firm-postgres pg_isready -U postgres

# ONE-TIME: create the tables and load the sample data
docker exec -i law-firm-postgres psql -U postgres -d law_firm_db -v ON_ERROR_STOP=1 < database/law_firm_schema.sql
```

**Option B: PostgreSQL installed with apt**

```bash
# ONE-TIME: install and start PostgreSQL
sudo apt install postgresql
sudo systemctl enable --now postgresql

# ONE-TIME: set the password and create the empty database
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'YOUR_PASSWORD';"
sudo -u postgres createdb law_firm_db

# ONE-TIME: create the tables and load the sample data
psql -h localhost -U postgres -d law_firm_db -v ON_ERROR_STOP=1 -f database/law_firm_schema.sql
```

Use `-h localhost` here. Without it, `psql -U postgres` usually fails with `Peer authentication failed`.

Check that it worked. You should see `12`:

```bash
# Docker
docker exec law-firm-postgres psql -U postgres -d law_firm_db -tc "SELECT count(*) FROM legal_case;"

# apt
psql -h localhost -U postgres -d law_firm_db -tc "SELECT count(*) FROM legal_case;"
```

> Load the schema before relying on database features. If the API starts on an empty database, it creates plain tables and sample data by itself, but **without** the triggers, views and functions.

### 3. Set up the backend (ONE-TIME)

`requirements.txt` is in the project root, not in `backend/`.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
cp .env.example .env
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then edit `backend/.env` and set these two lines:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/law_firm_db
SECRET_KEY=the-key-you-just-generated
```

If the password contains symbols such as `@`, `:` or `$`, URL-encode them in `DATABASE_URL` (`$` becomes `%24`).

### 4. Train the ML models (ONE-TIME)

Trained `.pkl` files are not stored in git, so each machine trains its own. The matter type assistant returns a 503 error until this is done.

Install only the ML packages the app uses. The full `requirements-ml.txt` also pulls in very large packages such as `torch` that the current models don't need.

```bash
cd backend
source venv/bin/activate
pip install pandas numpy scikit-learn joblib statsmodels

# train_models.py does not read .env by itself, so export the database URL first
export "$(grep '^DATABASE_URL=' .env)"
python train_models.py --model all
```

Training takes under a minute. Run it from `backend/`. Each run also writes a `training_results_<timestamp>.json` file there, which you can delete.

**OCCASIONAL:** retrain when the data changes. Use `--model classifier`, `--model hotspot` or `--model forecaster` to train just one. `--model classifier` needs no database.

### 5. Set up the frontend (ONE-TIME)

```bash
cd frontend
npm install
```

## Starting the app (EVERY TIME)

**1. Make sure the database is running.**

```bash
# Docker
docker start law-firm-postgres

# apt: normally already running after a reboot
sudo systemctl start postgresql
```

**2. Start the backend in one terminal, and leave it running.**

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

The API is at http://localhost:8000 and its interactive docs are at http://localhost:8000/docs.

**3. Start the frontend in a second terminal.**

```bash
cd frontend
npm run electron:start
```

To stop, press `Ctrl+C` in both terminals. The Docker container keeps running until you run `docker stop law-firm-postgres`.

### Demo logins

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `lawyer1` | `lawyer123` | lawyer |
| `staff1` | `staff123` | staff |

## Occasional commands

**Reset the database to the sample firm.** This deletes all data.

```bash
# Docker
docker exec -i law-firm-postgres psql -U postgres -d law_firm_db -v ON_ERROR_STOP=1 < database/law_firm_schema.sql

# apt
psql -h localhost -U postgres -d law_firm_db -v ON_ERROR_STOP=1 -f database/law_firm_schema.sql
```

**After pulling changes that update dependencies:**

```bash
(cd backend && source venv/bin/activate && pip install -r ../requirements.txt)
(cd frontend && npm install)
```

**Rebuild the classifier's training data.** You normally don't need this, because `backend/ml_data/matter_types.csv` is already in git. See the notes at the top of `backend/ml_data/build_matter_dataset.py`.

**Build a Linux package:**

```bash
cd frontend
npm run electron:build-linux
```

## Troubleshooting

**Port 8000 or 5173 is already in use**

```bash
ss -ltnp | grep -E ':8000|:5173'
kill <PID>
```

**Backend can't connect to the database**

```bash
docker ps                                  # Docker: is law-firm-postgres up?
systemctl status postgresql                # apt: is the service active?
grep '^DATABASE_URL=' backend/.env         # does the password match?
```

**`No module named ...`**: the virtual environment isn't active. Run `source venv/bin/activate` from `backend/`.

**`Matter classifier not trained`**: run the training step in section 4.

**Training can't connect to the database**: you skipped the `export` line in section 4. It only lasts for the current terminal.

**"Login failed" in the app**: check that the backend is running, and that `ALLOWED_ORIGINS` in `backend/.env` includes `http://localhost:5173`.

**Evidence file upload fails**: file storage needs MongoDB. Everything else works without it.

**Electron says it failed to install, or the app won't open**

```bash
cd frontend
node node_modules/electron/install.js
```

If it reports a sandbox error (`chrome-sandbox` or `setuid`), start it with the sandbox off. Use this for local development only:

```bash
npm run dev                                                # terminal 1
npx wait-on http://localhost:5173 && NODE_ENV=development npx electron . --no-sandbox   # terminal 2
```

**Blank window**: run `npm run dev` and `npm run electron` in separate terminals to see which one reports the error.

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # App entry point
│   │   ├── config.py          # Settings loaded from .env
│   │   ├── database.py        # Database connection
│   │   ├── seed.py            # Sample data for an empty database
│   │   ├── ai_models/         # Classifier, locality model, forecaster
│   │   ├── core/              # JWT and password security
│   │   ├── models/            # Database models
│   │   ├── schemas/           # Request and response schemas
│   │   └── routers/           # API endpoints
│   ├── ml_data/               # Classifier training data and its build script
│   ├── train_models.py        # Trains the ML models
│   └── .env.example           # Settings template
├── frontend/
│   ├── electron/main.js       # Electron main process
│   └── src/
│       ├── theme.js           # Colors, fonts, component styles
│       ├── components/        # Layout, status chip, matter type assistant
│       ├── context/           # Login state
│       ├── pages/             # Screens
│       └── services/api.js    # API client
├── database/
│   └── law_firm_schema.sql    # Tables, triggers, views, functions, sample data
├── requirements.txt           # Backend packages
├── requirements-ml.txt        # Every optional ML package (very large)
└── PROJECT_GUIDE.md           # Design and schema reference
```

## Creating users

**Using the API docs:** open http://localhost:8000/docs, click **Authorize**, and log in as an admin. Then open `POST /api/v1/auth/register`, click **Try it out**, and send:

```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "full_name": "New User Name",
  "role": "lawyer"
}
```

Roles are `admin`, `lawyer` and `staff`.

## Contributing

```bash
git pull origin main
git checkout -b feature/your-feature-name
git add <files>
git commit -m "Add: your feature description"
git push origin feature/your-feature-name
```

Then open a pull request.
