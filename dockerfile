FROM python:3.11-slim

WORKDIR /

COPY requirements.txt requirements.txt
COPY templates templates
COPY *.py ./

RUN pip install -r requirements.txt

RUN set FLASK_ENV=production

EXPOSE 8000

# CMD ["flask", "run", "--host", "0.0.0.0", "--port", "8000"]
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000"]