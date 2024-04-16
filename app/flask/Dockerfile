FROM python:latest

ENV CELERY_BROKER_URL redis://redis:6379/0
ENV CELERY_RESULT_BACKEND redis://redis:6379/0
ENV C_FORCE_ROOT true

WORKDIR /app

ADD requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt
    
CMD ["uwsgi", "app.ini"]
