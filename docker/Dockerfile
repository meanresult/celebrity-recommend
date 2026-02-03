# "어떤 컴퓨터를 만들지" 

FROM apache/airflow:2.10.1
USER airflow
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# 2) Playwright OS 의존성은 root로 설치
USER root
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 \
    libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
    libgtk-3-0 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# 3) 브라우저 설치는 airflow 유저로 (sudo 필요 없음)
USER airflow
RUN playwright install chromium