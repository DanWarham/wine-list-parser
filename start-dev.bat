@echo off
REM Start MinIO server (adjust path and data directory as needed)
start cmd /k "cd /d C:\Users\Dan\minio-data\wine-lists && C:\Users\Dan\Downloads\minio.exe server . --console-address :9001"

REM Start frontend
start cmd /k "cd /d C:\Users\Dan\Projects\wine-list-parser\frontend && npm run dev"

REM Start backend
start cmd /k "cd /d C:\Users\Dan\Projects\wine-list-parser\backend && uvicorn main:app --reload --host 127.0.0.1 --port 8000"