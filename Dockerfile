FROM python:3.6.2-alpine3.6
RUN apk update
RUN apk add  git gcc musl-dev linux-headers libxslt-dev libxml2-dev --no-cache
RUN pip install streamlink bs4 lxml gevent
RUN git clone https://github.com/bzsklb/ChaturbateRecorder /root/ChaturbateRecorder
RUN apk del git gcc musl-dev --no-cache
RUN rm -Rf /tmp/*
CMD cd /root/ChaturbateRecorder && python ChaturbateRecorder.py
