#!/usr/bin/env python3
import os, sys, obd, logging, time, collections.abc
from prometheus_client import start_http_server, Summary, Gauge, Info

http_port = 8000
poll_interval = 2.5
connection = None
metrics = {}
info_metrics = ["mids_a", "mids_b", "mids_c", "mids_d", "mids_e", "mids_f", "pids_9a", "pids_a", "pids_b", "pids_c"]
ignore_metrics = ["clear_dtc", "calibration_id", "status", "status_drive_cycle", "vin"]
allowed_metrics = [
    "elm_voltage",
    "engine_load",
    "run_time",
    "fuel_type",
    "fuel_level",
    "control_module_voltage",
    "timing_advance",
    "intake_pressure",
    "evap_vapor_pressure",
    "relative_throttle_pos",
    "absolute_load",
    "rpm",
    "fuel_status",
    "throttle_actuator",
    "accelerator_pos_d",
    "intake_temp",
    "throttle_pos_b",
    "cvn",
    "long_fuel_trim_1",
    "throttle_pos",
    "coolant_temp",
    "catalyst_temp_b1s1",
    "distance_w_mil",
    "maf",
    "evaporative_purge",
    "commanded_equiv_ratio",
    "barometric_pressure",
    "speed",
    "obd_compliance",
    "accelerator_pos_e",
    "ambiant_air_temp",
    "elm_version",
    "short_fuel_trim_1",
    "fuel_rail_pressure_abs"
    ]
supported_commands_metric = None

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
        try:
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
                log.warning('Found an array metric {0}. Value was {1}'.format(self.name, self.response.value))
                if self.metric is None:
                    self.metric = Gauge(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, self.unit),['iteration', 'event'])
                for counter, val in enumerate(self.response.value):
                    if val is None:
                        continue
                    # if isinstance(val, collections.abc.Sequence) and not isinstance(val, (str, bytes)):
                    #     for counter2, val2 in enumerate(val):
                    #         if val is None:
                    #             continue
                    #         if isinstance(val2, collections.abc.Sequence) and not isinstance(val2, (str, bytes)):
                    #             self.metric.labels(iteration=counter, iteration2=counter2, event=len(val2)).set(1)
                    #         else:
                    #             self.metric.labels(iteration=counter, iteration2=counter2, event=str(val2)).set(1)
                    # else:
                    self.metric.labels(iteration=counter, event=str(val)).set(1)
            # if isinstance(self.response.value, obd.Unit.Status):
            #     if self.metric is None:
            #         self.metric = Info(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, type(self.response.value)))
            #     self.metric.info({'value': str(self.response.value)})
            else:
                log.warning('Unhandled Metric recording as info metric {0}. Value was {1}'.format(self.name, self.response.value))
                try:
                    if self.metric is None:
                        self.metric = Info(self.metric_prefix + self.name, '{0} ({1})'.format(self.desc, type(self.response.value)))
                    self.metric.info({'value': str(self.response.value)})
                except:
                    log.warning('failed recording unhandled Metric as info {0}. Value was {1}'.format(self.name, self.response.value))
        except:
            log.error('Error recording metric for {0}. Value was {1}'.format(self.name, self.response.value))


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
        if command.name.lower() in ignore_metrics:
            continue

        supported_commands_metric.labels(command=command.name.lower(), desc=command.desc).inc(1)

        if command.name.lower() in allowed_metrics:
            metric = CommandMetric(command)
            metrics[metric.name] = metric

if __name__ == '__main__':
    obd.logger.setLevel(obd.logging.INFO)
    log = logging.getLogger('obd.monitor')

    log.warning('starting prometheus on port %s' % http_port)
    start_http_server(http_port) # prometheus

    supported_commands_metric = Gauge('obd_' + 'supported_commands', 'which commands are supported by the vehicle',['command', 'desc'])

    # Continuously poll the metrics.
    while True:
        first_connection = False if connection else True
        if connect():
            for metric_name in metrics:
                metrics[metric_name].update()

        time.sleep(poll_interval)
