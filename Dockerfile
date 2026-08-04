FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/app ./backend/app
RUN pip install --no-cache-dir ./backend
COPY --from=web /web/dist ./frontend/dist

# ADMIN_PASSWORD 와 GATE_PASSWORD 는 이미지에 굽지 않는다.
# 배포처의 환경변수로 넘긴다 — 둘 다 없으면 서버가 시작을 거부한다.
ENV DB_PATH=/data/schedule.db
ENV FRONTEND_DIST=/srv/frontend/dist
VOLUME ["/data"]
EXPOSE 8000

# 시도 제한 카운터가 프로세스 메모리에 있으므로 워커는 반드시 1개다.
# 앱은 임포트가 아니라 호출 시점에 만들어지므로 --factory 를 쓴다.
#
# Railway·Fly 같은 곳은 들을 포트를 PORT 로 넘긴다. 셸을 거쳐야 ${PORT} 가
# 풀리고, exec 로 넘겨야 uvicorn 이 PID 1 이 되어 종료 신호를 직접 받는다.
CMD ["sh", "-c", "exec uvicorn app.main:create_production_app --factory \
     --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

