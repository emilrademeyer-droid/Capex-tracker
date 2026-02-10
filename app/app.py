services:
  - type: web
    name: capex-ui
    env: python
    plan: free               # change to starter later if needed
    branch: main
    buildCommand: pip install --no-cache-dir -r app/requirements.txt
    startCommand: streamlit run app/app.py --server.port $PORT --server.headless true
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.3
      - key: DATABASE_URL
        fromDatabase:
          name: capex-db
          property: connectionString

  - type: cron
    name: capex-daily-search
    env: python
    plan: free
    branch: main
    buildCommand: pip install --no-cache-dir -r agent/requirements.txt
    startCommand: python agent/daily_runner.py
    schedule: "0 0 * * *"          # every day at 00:00 UTC
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.3
      - key: DATABASE_URL
        fromDatabase:
          name: capex-db
          property: connectionString

  - type: pserv
    name: capex-db
    plan: starter-0_25GB           # ~$7/mo – smallest paid Postgres
    database:
      databaseName: capex_tracker
      user: capex
