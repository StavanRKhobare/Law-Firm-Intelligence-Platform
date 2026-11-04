#!/bin/bash
echo "========================================"
echo " Crime Intelligence Platform Launcher"
echo "========================================"
echo ""

echo "Starting Backend Server..."
cd backend
source venv/bin/activate
uvicorn app.main:app --reload &

sleep 5

echo "Starting Frontend..."
cd ../frontend
npm run electron:start
```

---

## Step 5: Package Everything for Rohith

Create this folder structure to send:
```
CRIME_INTELLIGENCE_PLATFORM_COMPLETE/
│
├── 📁 source_code/
│   ├── backend/
│   ├── frontend/
│   ├── README.md
│   ├── .gitignore
│   └── START_PROJECT.bat
│
├── 📁 database/
│   ├── crime_intelligence_db_backup.sql
│   └── HOW_TO_IMPORT.txt
│
├── 📁 credentials/
│   └── CREDENTIALS.txt
│
└── 📄 SETUP_INSTRUCTIONS.txt
```

### Create `database/HOW_TO_IMPORT.txt`:
```
DATABASE IMPORT INSTRUCTIONS
============================

1. Open pgAdmin or psql

2. Create database:
   CREATE DATABASE crime_intelligence_db;

3. Import the backup:
   psql -U postgres -d crime_intelligence_db -f crime_intelligence_db_backup.sql

4. Verify:
   psql -U postgres -d crime_intelligence_db
   \dt
   SELECT COUNT(*) FROM users;

That's it! Database is ready.
```

### Create `credentials/CREDENTIALS.txt`:
```
LOGIN CREDENTIALS
=================

Admin:
  Username: admin
  Password: admin123

Officer:
  Username: officer1
  Password: officer123

Forensic:
  Username: forensic1  
  Password: forensic123

PostgreSQL:
  You'll need to create database with your own password
  Update in backend/.env file

IMPORTANT: Don't share these publicly!