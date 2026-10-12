FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend ./backend
ENV CAMPUSFIX_DATABASE=/data/campusfix.sqlite3
EXPOSE 5000
CMD ["python", "-m", "backend.app"]
