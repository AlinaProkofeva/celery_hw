FROM python:3.11

COPY . code

WORKDIR code

RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

RUN pip install -r requirements.txt


ENV PYTHONUNBUFFERED=True