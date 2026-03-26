from collections import deque
import random
import numpy as np

from event import Event
from customer import Customer
from FES import FES
from station import Station
from sim_results import SimResults
from config import OPEN_TIME, CLOSE_TIME, ARRIVALS, FRACTION_BIG, STATIONS, CUSTOMER_CLASSES


class WRPSimulation:
    """
    Discrete-event simulation for the Eindhoven WRP.
    Keeps close to the lecture event-scheduling setup.
    """

    def __init__(self, seed=None, arrival_multiplier=1.0):
        self.rng = random.Random(seed)
        self.arrival_multiplier = arrival_multiplier

        self.t = OPEN_TIME
        self.fes = FES()
        self.customer_id = 0

        self.stations = {
            "Entrance": Station(
                "Entrance",
                STATIONS["Entrance"].mean_service,
                STATIONS["Entrance"].std_service,
                STATIONS["Entrance"].parking_spaces,
                STATIONS["Entrance"].max_queue,
            ),
            "Hall": Station(
                "Hall",
                STATIONS["Hall Small Cars"].mean_service,
                STATIONS["Hall Small Cars"].std_service,
                STATIONS["Hall Small Cars"].parking_spaces,
                STATIONS["Hall Small Cars"].max_queue,
            ),
            "Overflow": Station(
                "Overflow",
                STATIONS["Overflow"].mean_service,
                STATIONS["Overflow"].std_service,
                STATIONS["Overflow"].parking_spaces,
                STATIONS["Overflow"].max_queue,
            ),
            "DcDd": Station(
                "DcDd",
                STATIONS["DcDd"].mean_service,
                STATIONS["DcDd"].std_service,
                STATIONS["DcDd"].parking_spaces,
                STATIONS["DcDd"].max_queue,
            ),
            "Green": Station(
                "Green",
                STATIONS["Green"].mean_service,
                STATIONS["Green"].std_service,
                STATIONS["Green"].parking_spaces,
                STATIONS["Green"].max_queue,
            ),
            "Rest": Station(
                "Rest",
                STATIONS["Rest"].mean_service,
                STATIONS["Rest"].std_service,
                STATIONS["Rest"].parking_spaces,
                STATIONS["Rest"].max_queue,
            ),
        }

        self.completed_system_times = []
        self.entrance_queue_blocked_time = 0.0
        self.last_global_time = OPEN_TIME
        self.total_customers = 0

    # ------------------------------------------------------------------
    # Main public method
    # ------------------------------------------------------------------

    def run(self):
        first_arrival = self.sample_next_external_arrival(self.t)
        if first_arrival is not None:
            self.fes.add(Event(Event.ARRIVAL, first_arrival, customer=None, station="Entrance", external=True))

        while not self.fes.isEmpty():
            e = self.fes.next()
            self.advance_time(e.time)

            if e.type == Event.ARRIVAL:
                self.handle_arrival(e)
            elif e.type == Event.DEPARTURE:
                self.handle_departure(e)
            else:
                raise ValueError("Unknown event type.")

        return self.collect_results()

    # ------------------------------------------------------------------
    # Time updates
    # ------------------------------------------------------------------

    def advance_time(self, new_t):
        if new_t < self.t:
            raise ValueError("Event time moved backwards.")

        blocked = self.is_road_blocked()
        dt = new_t - self.t
        if blocked:
            self.entrance_queue_blocked_time += dt

        for station in self.stations.values():
            station.update_time_stats(new_t)

        self.t = new_t

    def is_road_blocked(self):
        entrance_station = self.stations["Entrance"]
        return entrance_station.queue_length_sce() > 4

    # ------------------------------------------------------------------
    # External arrivals
    # ------------------------------------------------------------------

    def sample_next_external_arrival(self, current_time):
        t = current_time

        while t < CLOSE_TIME:
            rate_per_hour = self.get_arrival_rate(t) * self.arrival_multiplier
            if rate_per_hour <= 0:
                t = self.next_breakpoint_after(t)
                if t is None:
                    return None
                continue

            rate_per_sec = rate_per_hour / 3600.0
            dt = self.rng.expovariate(rate_per_sec)
            candidate = t + dt

            next_break = self.next_breakpoint_after(t)
            if next_break is not None and candidate >= next_break:
                t = next_break
                continue

            return candidate

        return None

    def get_arrival_rate(self, t):
        current_rate = 0.0
        for start, rate in ARRIVALS:
            if t >= start:
                current_rate = rate
            else:
                break
        return current_rate

    def next_breakpoint_after(self, t):
        for start, _ in ARRIVALS:
            if start > t:
                return start
        return None

    def sample_customer_class(self):
        probs = [cc.fraction for cc in CUSTOMER_CLASSES]
        idx = self.weighted_choice(probs)
        return CUSTOMER_CLASSES[idx]

    def weighted_choice(self, probs):
        u = self.rng.random()
        s = 0.0
        for i, p in enumerate(probs):
            s += p
            if u <= s:
                return i
        return len(probs) - 1

    def create_customer(self, arr_time):
        cust_class = self.sample_customer_class()
        is_big = self.rng.random() < FRACTION_BIG
        route = self.sample_legal_route(cust_class, is_big)

        c = Customer(
            cust_id=self.customer_id,
            arr_time=arr_time,
            is_big=is_big,
            cust_class=cust_class.name,
            route=route,
        )
        self.customer_id += 1
        self.total_customers += 1
        return c

    # ------------------------------------------------------------------
    # Routing logic
    # ------------------------------------------------------------------

    def sample_legal_route(self, cust_class, is_big):
        """
        Convert 2012 raw class data into a legal 2026 route.

        Legal routes:
        A: Entrance -> Green -> Rest? -> Exit
        B: Entrance -> Hall/Overflow? -> DcDd? -> Rest? -> Exit

        We preserve realism by sampling from the given routing matrix, but
        suppress all Green if the customer enters the B-side, and suppress
        Hall/DcDd if the customer enters Green.
        """
        M = cust_class.routing_matrix

        # states in matrix:
        # 0 Hall/Ovfl, 1 DcDd, 2 Green, 3 Rest, 4 Exit

        first = self.weighted_choice(M[0])
        route = []

        if first == 2:
            # Type A
            route.append("Green")
            second = self.weighted_choice(M[3])
            if second == 3:
                route.append("Rest")
            return route

        elif first in (0, 1, 3):
            # Type B or direct to DcDd/Rest from entrance
            if first == 0:
                if is_big:
                    route.append("Hall")
                else:
                    # small cars prefer overflow if they intend Hall/Ovfl
                    route.append("Overflow")
                next_state = self.weighted_choice(M[1])
            elif first == 1:
                route.append("DcDd")
                next_state = self.weighted_choice(M[2])
            else:
                route.append("Rest")
                return route

            # After entering B side, Green is forbidden.
            if next_state == 1 and "DcDd" not in route:
                route.append("DcDd")
                next_state = self.weighted_choice(M[2])

            if next_state == 3 and "Rest" not in route:
                route.append("Rest")

            return route

        return []

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_arrival(self, event):
        if event.external:
            customer = self.create_customer(event.time)

            next_arrival = self.sample_next_external_arrival(event.time)
            if next_arrival is not None:
                self.fes.add(Event(Event.ARRIVAL, next_arrival, customer=None, station="Entrance", external=True))

            self.send_customer_to_station(customer, "Entrance")
            return

        # internal arrival
        customer = event.customer
        self.send_customer_to_station(customer, event.station)

    def handle_departure(self, event):
        customer = event.customer
        station_name = event.station
        station = self.stations[station_name]

        station.complete_service(customer, self.t)

        # after customer leaves, start next one there if possible
        self.try_start_waiting_customer(station_name)

        # move customer to next station
        customer.advance_route()
        next_station = customer.next_station()

        if next_station is None:
            customer.finished = True
            self.completed_system_times.append(self.t - customer.arrivalTime)
        else:
            self.send_customer_to_station(customer, next_station)

        # release upstream blocking by retrying all stations
        self.try_release_network_blocking()

    # ------------------------------------------------------------------
    # Station entry / blocking / service start
    # ------------------------------------------------------------------

    def send_customer_to_station(self, customer, station_name):
        if station_name == "Entrance":
            station = self.stations["Entrance"]
            station.add_to_queue(customer, self.t)
            self.try_start_waiting_customer("Entrance")
            return

        if station_name == "Overflow" and customer.is_big:
            station_name = "Hall"

        if station_name == "Overflow" and self.stations["Overflow"].free_space() < customer.spots_needed:
            station_name = "Hall"

        station = self.stations[station_name]
        station.add_to_queue(customer, self.t)
        self.try_start_waiting_customer(station_name)

    def try_start_waiting_customer(self, station_name):
        station = self.stations[station_name]

        while True:
            customer = station.pop_next_startable()
            if customer is None:
                break

            service_time = station.start_service(customer, self.t, self.rng)
            dep_time = self.t + service_time
            self.fes.add(Event(Event.DEPARTURE, dep_time, customer, station=station_name))

    def try_release_network_blocking(self):
        # Simple global retry policy; crude but robust.
        changed = True
        while changed:
            changed = False
            for name in ["Entrance", "Hall", "Overflow", "DcDd", "Green", "Rest"]:
                before = len(self.stations[name].in_service)
                self.try_start_waiting_customer(name)
                after = len(self.stations[name].in_service)
                if after > before:
                    changed = True

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def collect_results(self):
        res = SimResults()
        res.total_customers = self.total_customers
        res.completed_customers = len(self.completed_system_times)

        if self.completed_system_times:
            res.mean_system_time = float(np.mean(self.completed_system_times))

        entrance_waits = self.stations["Entrance"].waiting_times
        if entrance_waits:
            res.mean_entrance_wait = float(np.mean(entrance_waits))

        total_time = self.t - OPEN_TIME
        if total_time > 0:
            res.fraction_road_blocked = self.entrance_queue_blocked_time / total_time

        for name, st in self.stations.items():
            horizon = max(st.last_event_time - OPEN_TIME, 1e-12)
            res.station_mean_queue[name] = st.area_queue / horizon
            res.station_mean_occupancy[name] = st.area_occupancy / horizon
            res.station_mean_wait[name] = float(np.mean(st.waiting_times)) if st.waiting_times else 0.0
            res.station_nr_arrivals[name] = st.nr_arrivals

        return res