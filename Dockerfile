FROM python:3.8-buster
COPY . /code
WORKDIR /code
RUN apt-get -y update
RUN apt-get install -y logrotate
RUN mv prod.config.py config.py
RUN mkdir /var/log/fb-events-syncer
RUN mv logrotate /etc/logrotate.d/fb-events-syncer
RUN chmod 644 /etc/logrotate.d/fb-events-syncer
RUN pip install -r requirements.txt
CMD ["python3", "start.py"]
