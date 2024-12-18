FROM python:3.9-slim
RUN useradd -m myuser
USER myuser
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY ./cookies/cookies.txt /app/cookies.txt

EXPOSE 8080

CMD ["python", "app.py"]
