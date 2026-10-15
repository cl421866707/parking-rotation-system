# Python 3.11 runtime for parking-rotation-system
# Base image via DaoCloud mirror (China-accessible Docker Hub proxy)
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.11-slim-bookworm-linuxarm64

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --trusted-host pypi.tuna.tsinghua.edu.cn

COPY app.py settings.json ./
COPY lottery/ lottery/
COPY static/ static/
COPY data/ data/

EXPOSE 5000

CMD ["python", "app.py"]
