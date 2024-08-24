#!/usr/bin/env python3
import os, sys, obd, logging, time, collections.abc
from prometheus_client import start_http_server, Summary, Gauge, Info

http_port = 8000
poll_interval = 1.0
connection = None
metrics = {}
info_metrics = ["pids_9a", "pids_a", "pids_b", "pids_c", "calibration_id"]
ignore_metrics = ["calibration_id", "status", "status_drive_cycle"]

"""
Monitor a single OBDII command as a Prometheus metric.
"""
class CommandMetric():
    def __init__(self, command, metric_prefix = 'obd_'):
        self.command = command
        self.response = None
        self.metric = None
        self.unit = None
        self.desc = command.desc
        self.name = command.name.lower()
        self.metric_prefix = metric_prefix
        self.log = logging.getLogger('obd.monitor.' + self.name)
        self.log.info('metric initialized')

    def update(self):
        self.response = connection.query(self.command)
        if self.response.unit:
            if not self.unit:
                self.unit = self.response.unit
            elif self.unit != self.response.unit:
                raise Exception('{0} unit changed from {1} to {2}'.format(
                    self.name, self.unit, self.response.unit))

        if self.response.value is None:
            return

        if isinstance(self.response.value, obd.Unit.Quantity):
            if self.metric is None:
                self.metric = Gauge(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, self.unit))
            self.metric.set(self.response.value.magnitude)
        elif isinstance(self.response.value, str) or self.name in info_metrics:
            if self.metric is None:
                self.metric = Info(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, type(self.response.value)))
            self.metric.info({'value': str(self.response.value)})
        elif isinstance(self.response.value, bool):
            if self.metric is None:
                self.metric = Gauge(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, self.unit))
            self.metric.set(1 if self.response.value else 0)
        elif isinstance(self.response.value, collections.abc.Sequence) and not isinstance(self.response.value, (str, bytes)):
            if self.metric is None:
                self.metric = Gauge(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, self.unit))
            for i in self.response.value:
                self.metric.labels(event=i).set(1)
        # if isinstance(self.response.value, obd.Unit.Status):
        #     if self.metric is None:
        #         self.metric = Info(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, type(self.response.value)))
        #     self.metric.info({'value': str(self.response.value)})
        else:
            log.warning('skipping recording metric {0}. Value was {1}'.format(self.name, self.response.value))

"""
Ensure that the `connection` global is actually connected, and instatiate `metric` objects.
"""
def connect():
    global connection, metrics
    if connection and connection.status() == obd.utils.OBDStatus.CAR_CONNECTED:
        return True
    log.info('connecting to car...')
    connection = obd.OBD()
    if connection.status() != obd.utils.OBDStatus.CAR_CONNECTED:
        return False
    metrics = {}
    for command in connection.supported_commands:
        if command.name in ignore_metrics:
            continue
        metric = CommandMetric(command)
        metrics[metric.name] = metric

if __name__ == '__main__':
    obd.logger.setLevel(obd.logging.INFO)
    log = logging.getLogger('obd.monitor')

    log.warning('starting prometheus on port %s' % http_port)
    start_http_server(http_port) # prometheus

    # Continuously poll the metrics.
    while True:
        first_connection = False if connection else True
        if connect():
            for metric_name in metrics:
                metrics[metric_name].update()

        time.sleep(poll_interval)
