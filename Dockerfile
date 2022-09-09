FROM python:3.10-alpine3.16

RUN apk update && \
    apk add usbutils bash wget

RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir hanazeder_server

ENTRYPOINT ["python", "-m", "hanazeder_server.mqtt"]