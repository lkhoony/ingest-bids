FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src

# 실행 시 --args 로 옵션만 덧붙일 수 있도록 ENTRYPOINT 사용 (예: --sources,scsbid_list_sttus)
ENTRYPOINT ["python", "-m", "src.main"]
