import math
import numpy as np

class SimResults:
    def __init__(self):
        self.mean_system_time = math.nan
        self.mean_entrance_wait = math.nan
        self.fraction_road_blocked = math.nan

        self.station_mean_queue = {}
        self.station_mean_occupancy = {}
        self.station_mean_wait = {}
        self.station_nr_arrivals = {}

        self.completed_customers = 0
        self.total_customers = 0

    @staticmethod
    def from_replications(values):
        arr = np.asarray(values, dtype=float)
        mean = np.mean(arr)
        std = np.std(arr, ddof=1) if len(arr) > 1 else 0.0
        halfwidth = 1.96 * std / np.sqrt(len(arr)) if len(arr) > 1 else 0.0
        return mean, halfwidth