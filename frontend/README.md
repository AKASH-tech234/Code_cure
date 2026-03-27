# Frontend (Next.js)

## Run Frontend Only

```powershell
cd C:\Users\akash\iit_bhu\techsta\frontend
npm install
npm run dev
```

Open:

- http://localhost:3000

## Run Full Stack (from project root)

Start each service in a separate terminal.

### Agent Note

- No separate agent server startup is required.
- The backend executes agent logic in-process for `POST /query`.
- Keep `backend`, `ml-service`, and `rag-service` running for chat/agent flows.

### Terminal 1: Backend Gateway

```powershell
cd C:\Users\akash\iit_bhu\techsta\backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: ML Service

```powershell
cd C:\Users\akash\iit_bhu\techsta\ml-service
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### Terminal 3: RAG Service

```powershell
cd C:\Users\akash\iit_bhu\techsta\rag-service
uvicorn app.main:app --host 127.0.0.1 --port 8003 --reload
```

### Terminal 4: Frontend

```powershell
cd C:\Users\akash\iit_bhu\techsta\frontend
npm run dev
```

## Health Checks

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8001/health -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8003/docs -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3000 -UseBasicParsing
```
