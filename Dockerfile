FROM python:3.10
WORKDIR /stuff
COPY requirements.txt /stuff/
RUN pip install -r requirements.txt
COPY . /stuff
# CMD python main.py
# CMD gunicorn main:app -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
CMD gunicorn main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080