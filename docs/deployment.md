# Deployment Notes

## Current: Local Development

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
streamlit run frontend/app.py --server.port 8501
```

## Production Checklist

1. **Database**: Migrate to PostgreSQL + PostGIS
   ```bash
   DATABASE_URL=postgresql://user:pass@host/db alembic upgrade head
   ```
2. **Secrets**: Use proper secret manager, not `.env`
3. **HTTPS**: Terminate TLS at reverse proxy (nginx/Caddy)
4. **Workers**: `uvicorn --workers 4` or gunicorn
5. **Monitoring**: Add Prometheus metrics, structured logs to ELK/Loki
6. **Frontend**: Build React + Vite bundle, serve via nginx
7. **Alerts**: Configure real SMS (Twilio) / Push (Firebase) providers
8. **Backups**: Automated PG dumps + point-in-time recovery

## Docker (Future)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY . .
EXPOSE 8000 8501
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```