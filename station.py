from collections import deque
import math
import random


class Station:
    def __init__(self, name, mean_service, std_service, capacity, max_queue=math.inf):
        self.name = name
        self.mean_service = mean_service
        self.std_service = std_service
        self.capacity = capacity                  # in small-car equivalents
        self.max_queue = max_queue                # queue limit in small-car equivalents

        self.waiting = deque()
        self.in_service = []

        self.busy_space = 0

        # time-average statistics
        self.area_queue = 0.0
        self.area_occupancy = 0.0
        self.last_event_time = 0.0

        # customer-based statistics
        self.waiting_times = []
        self.service_times = []
        self.nr_arrivals = 0

    def _required_capacity(self, customer):
        """
        Entrance is a single checking server:
        one customer at a time, regardless of vehicle size.
        Everywhere else, capacity is in small-car equivalents.
        """
        if self.name == "Entrance":
            return 1
        return customer.spots_needed

    def update_time_stats(self, t):
        dt = t - self.last_event_time
        if dt < 0:
            raise ValueError("Negative time step encountered.")
        self.area_queue += dt * self.queue_length_sce()
        self.area_occupancy += dt * self.busy_space
        self.last_event_time = t

    def queue_length_sce(self):
        if self.name == "Entrance":
            return len(self.waiting)
        return sum(c.spots_needed for c in self.waiting)

    def free_space(self):
        return self.capacity - self.busy_space

    def can_start_customer(self, customer):
        return self.free_space() >= self._required_capacity(customer)

    def add_to_queue(self, customer, t):
        self.nr_arrivals += 1
        customer.queue_arrival_times[self.name] = t
        self.waiting.append(customer)

    def pop_next_startable(self):
        if not self.waiting:
            return None
        first = self.waiting[0]
        if self.can_start_customer(first):
            return self.waiting.popleft()
        return None

    def start_service(self, customer, t, rng):
        self.busy_space += self._required_capacity(customer)
        self.in_service.append(customer)

        q_arrival = customer.queue_arrival_times[self.name]
        wait = t - q_arrival
        self.waiting_times.append(wait)
        customer.service_start_times[self.name] = t

        service_time = self.sample_service_time(rng)
        self.service_times.append(service_time)
        customer.current_station = self.name
        return service_time

    def complete_service(self, customer, t):
        self.busy_space -= self._required_capacity(customer)
        self.in_service.remove(customer)
        customer.departure_times[self.name] = t
        customer.current_station = None

    def sample_service_time(self, rng):
        x = rng.normalvariate(self.mean_service, self.std_service)
        return max(1.0, x)