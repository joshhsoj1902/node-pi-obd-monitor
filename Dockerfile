FROM python:slim-bookworm

USER root

RUN apt-get update && apt-get install --no-install-recommends -y \
      python3-pip \
      python3-serial && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pip install --upgrade setuptools wheel
RUN pip install --upgrade prometheus_client pyserial
RUN pip install --upgrade obd

RUN pip install --upgrade ELM327-emulator

COPY obd-monitor.py /usr/bin/obd-monitor.py
RUN chmod +x /usr/bin/obd-monitor.py
CMD /usr/bin/obd-monitor.py

EXPOSE 8000
