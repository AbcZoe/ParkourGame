# Dockerfile for NetGame
# 使用官方 Python 映像
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY app.py ./
COPY chat_events.py ./
COPY db_config.py ./
COPY user_service.py ./
COPY static ./static
COPY templates ./templates
COPY information ./information
COPY docker/requirements.txt ./requirements.txt

# 安裝依賴
RUN pip install --no-cache-dir -r requirements.txt

# 開放 Flask 預設埠
EXPOSE 5000

# 啟動應用程式
CMD ["python", "app.py"]
