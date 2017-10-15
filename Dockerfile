FROM python:3-alpine
RUN apk update
RUN apk add  git gcc musl-dev linux-headers libxslt-dev libxml2-dev --no-cache
RUN pip install streamlink bs4 lxml gevent
RUN git clone https://github.com/bzsklb/ChaturbateRecorder /cr
RUN apk del git gcc musl-dev --no-cache
RUN rm -Rf /tmp/*
CMD cd /cr && python ChaturbateRecorder.py
