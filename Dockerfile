# Python 3.12.6 이미지 사용
FROM python:3.12.6-slim

# 환경 변수 설정
# PYTHONUNBUFFERED=1: Python 출력 버퍼링 비활성화
# PYTHONDONTWRITEBYTECODE=1: .pyc 파일 생성 방지
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 시스템 의존성 패키지 설치 (PostgreSQL 클라이언트 라이브러리 포함)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# uv 패키지 매니저 설치
RUN pip install uv

# 의존성 파일 복사
COPY pyproject.toml uv.lock ./

# 의존성 설치 (frozen 옵션으로 lock 파일 기준으로 정확히 설치)
RUN uv sync --frozen

# 소스 코드 복사
COPY . .

# 정적 파일 수집을 위한 디렉토리 생성
RUN mkdir -p staticfiles

# 8000 포트 노출
EXPOSE 8000

# Gunicorn으로 Django 애플리케이션 실행
CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]