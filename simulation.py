from collections import deque
import numpy as np
import random

from event import Event
from customer import Customer
from FES import FES
from station import Station
from sim_results import SimResults
from config import OPEN_TIME, CLOSE_TIME, ARRIVALS, FRACTION_BIG, STATIONS, CUSTOMER_CLASSES


STATE_NAMES = ["HallOvfl", "DcDd", "Green", "Rest", "Exit"]
STATE_ROW = {"HallOvfl": 1, "DcDd": 2, "Green": 3, "Rest": 4}


class WRPSimulation:
    """
    Discrete-event simulation for the Eindhoven WRP.

    Implemented modelling choices:
    - Routes are sampled directly from config.py.
    - Type B customers always pass through the hall-front queue.
    - Hall-front queue length is enforced in small-car equivalents using max_queue.
    - Entrance remains blocked when a car cannot leave the gate.
    - A current parking spot is only released after the next move is feasible.
    - Hall uses big-car vs small-car service parameters from config.py.
    - Stations with max_queue = 0 do not admit an internal waiting queue.
    """

    def __init__(self, seed=None, arrival_multiplier=1.0):
        self.rng = random.Random(seed)
        self.arrival_multiplier = arrival_multiplier

        self.t = OPEN_TIME
        self.fes = FES()
        self.customer_id = 0
        self.total_customers = 0

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
                0,
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
            "HallFront": Station(
                "HallFront",
                mean_service=0.0,
                std_service=0.0,
                capacity=0,
                max_queue=STATIONS["Hall Small Cars"].max_queue,
            ),
        }

        # Customers that finished service but cannot move yet.
        self.blocked_after_service = {name: deque() for name in self.stations}

        self.completed_system_times = []
        self.entrance_queue_blocked_time = 0.0

    # ------------------------------------------------------------------
    # Main method
    # ------------------------------------------------------------------

    def run(self):
        first_arrival = self.sample_next_external_arrival(self.t)
        if first_arrival is not None:
            self.fes.add(
                Event(
                    Event.ARRIVAL,
                    first_arrival,
                    customer=None,
                    station="Entrance",
                    external=True,
                )
            )

        while not self.fes.isEmpty():
            e = self.fes.next()
            self.advance_time(e.time)

            if e.type == Event.ARRIVAL:
                self.handle_arrival(e)
            elif e.type == Event.DEPARTURE:
                self.handle_departure(e)

        return self.collect_results()

    # ------------------------------------------------------------------
    # Time updates
    # ------------------------------------------------------------------

    def advance_time(self, new_t):
        dt = new_t - self.t

        if self.is_road_blocked():
            self.entrance_queue_blocked_time += dt

        for station in self.stations.values():
            station.update_time_stats(new_t)

        self.t = new_t

    def entrance_vehicles_waiting_for_access(self):
        waiting = self.stations["Entrance"].queue_length_sce()
        blocked_gate = len(self.blocked_after_service["Entrance"])
        return waiting + blocked_gate

    def is_road_blocked(self):
        return self.entrance_vehicles_waiting_for_access() > 4

    def hall_front_queue_length_sce(self):
        return self.stations["HallFront"].queue_length_sce()

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

    # ------------------------------------------------------------------
    # Sampling customers and routes
    # ------------------------------------------------------------------

    def weighted_choice(self, probs):
        u = self.rng.random()
        s = 0.0
        for i, p in enumerate(probs):
            s += p
            if u <= s:
                return i
        return len(probs) - 1

    def sample_customer_class(self):
        probs = [cc.fraction for cc in CUSTOMER_CLASSES]
        idx = self.weighted_choice(probs)
        return CUSTOMER_CLASSES[idx]

    def sample_route_from_config(self, cust_class):
        matrix = cust_class.routing_matrix
        route = []

        state_idx = self.weighted_choice(matrix[0])
        while STATE_NAMES[state_idx] != "Exit":
            state_name = STATE_NAMES[state_idx]
            route.append(state_name)
            row_idx = STATE_ROW[state_name]
            state_idx = self.weighted_choice(matrix[row_idx])

        return route

    def create_customer(self, arr_time):
        cust_class = self.sample_customer_class()
        is_big = self.rng.random() < FRACTION_BIG
        route = self.sample_route_from_config(cust_class)

        if route and route[0] == "Green":
            customer_type = "A"
        else:
            customer_type = "B"

        customer = Customer(
            cust_id=self.customer_id,
            arr_time=arr_time,
            is_big=is_big,
            cust_class=cust_class.name,
            route=route,
            customer_type=customer_type,
        )
        self.customer_id += 1
        self.total_customers += 1
        return customer

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def handle_arrival(self, event):
        customer = self.create_customer(event.time)

        next_arrival = self.sample_next_external_arrival(event.time)
        if next_arrival is not None:
            self.fes.add(
                Event(
                    Event.ARRIVAL,
                    next_arrival,
                    customer=None,
                    station="Entrance",
                    external=True,
                )
            )

        self.enqueue_entrance(customer)
        self.try_release_network_blocking()

    def handle_departure(self, event):
        customer = event.customer
        origin = event.station

        moved = self.try_move_customer(customer, origin, from_blocked=False)
        if not moved:
            self.block_customer_at_origin(customer, origin)

        self.try_release_network_blocking()

    # ------------------------------------------------------------------
    # Basic entrance logic
    # ------------------------------------------------------------------

    def enqueue_entrance(self, customer):
        entrance = self.stations["Entrance"]
        entrance.add_to_queue(customer, self.t)
        self.try_start_waiting_customer("Entrance")

    def try_start_waiting_customer(self, station_name):
        station = self.stations[station_name]

        while True:
            customer = station.pop_next_startable()
            if customer is None:
                break

            service_time = station.sample_service_time(self.rng)
            station.start_service(customer, self.t, service_time)
            dep_time = self.t + service_time
            self.fes.add(Event(Event.DEPARTURE, dep_time, customer, station=station_name))

    # ------------------------------------------------------------------
    # Hall / overflow routing logic
    # ------------------------------------------------------------------

    def choose_b_side_station(self, customer):
        """
        Resolve the actual HallOvfl state into Hall or Overflow.

        Rules:
        - Large cars always go to Hall.
        - Overflow only for small cars.
        - Small cars prefer Overflow; if Overflow is full, then Hall.
        - If neither can accept the car right now, return None.
        """
        if customer.is_big:
            if self.can_enter_station_immediately(customer, "Hall"):
                return "Hall"
            return None

        if self.can_enter_station_immediately(customer, "Overflow"):
            return "Overflow"

        if self.can_enter_station_immediately(customer, "Hall"):
            return "Hall"

        return None

    def enqueue_hall_front(self, customer):
        self.stations["HallFront"].add_to_queue(customer, self.t)

    def can_join_hall_front(self, customer):
        return self.stations["HallFront"].can_join_waiting_queue(customer)

    def try_release_hall_front(self):
        progress = False
        hf_station = self.stations["HallFront"]

        while hf_station.waiting:
            customer = hf_station.waiting[0]
            
            next_state = customer.peek_next_route_state()

            if next_state == "Exit":
                hf_station.waiting.popleft()
                customer.finished = True
                self.completed_system_times.append(self.t - customer.arrivalTime)
                progress = True
                continue

            if next_state == "HallOvfl":
                target_station = self.choose_b_side_station(customer)
                if target_station is None:
                    break
            else:
                target_station = next_state
                if not self.can_enter_station_immediately(customer, target_station):
                    break

            hf_station.waiting.popleft()

            # Record their wait time directly into the Station object
            wait = self.t - customer.queue_arrival_times["HallFront"]
            hf_station.waiting_times.append(wait)

            customer.advance_to_next_route_state()
            self.start_customer_at_station(customer, target_station)
            progress = True

        return progress
    
    # ------------------------------------------------------------------
    # Movement / blocking logic
    # ------------------------------------------------------------------

    def can_enter_station_immediately(self, customer, station_name):
        station = self.stations[station_name]
        return station.can_start_customer(customer)

    def start_customer_at_station(self, customer, station_name):
        station = self.stations[station_name]

        station.nr_arrivals += 1
        customer.queue_arrival_times[station_name] = self.t

        service_time = self.sample_service_time_for_station(customer, station_name)
        station.start_service(customer, self.t, service_time)

        dep_time = self.t + service_time
        self.fes.add(Event(Event.DEPARTURE, dep_time, customer, station=station_name))

    def sample_service_time_for_station(self, customer, station_name):
        if station_name == "Hall":
            if customer.is_big:
                return self.stations["Hall"].sample_service_time(
                    self.rng,
                    mean_service=STATIONS["Hall Big Cars"].mean_service,
                    std_service=STATIONS["Hall Big Cars"].std_service,
                )
            return self.stations["Hall"].sample_service_time(
                self.rng,
                mean_service=STATIONS["Hall Small Cars"].mean_service,
                std_service=STATIONS["Hall Small Cars"].std_service,
            )

        return self.stations[station_name].sample_service_time(self.rng)

    def block_customer_at_origin(self, customer, origin):
        if customer not in self.blocked_after_service[origin]:
            self.blocked_after_service[origin].append(customer)
        customer.blocked_after_service = True

    def unblock_customer_at_origin(self, customer, origin):
        if customer in self.blocked_after_service[origin]:
            self.blocked_after_service[origin].remove(customer)
        customer.blocked_after_service = False

    def try_move_customer(self, customer, origin, from_blocked=False):
        """
        Attempts to move a customer away from their current occupied origin.
        The origin spot is only released if the next move is legally feasible.
        """
        next_state = customer.peek_next_route_state()

        if next_state == "Exit":
            self.finalize_departure_from_origin(customer, origin, from_blocked)
            customer.finished = True
            self.completed_system_times.append(self.t - customer.arrivalTime)
            return True

        if origin == "Entrance" and next_state == "HallOvfl":
            if not self.can_join_hall_front(customer):
                return False  # Blocked at the entrance gate
                
            self.finalize_departure_from_origin(customer, origin, from_blocked)
            self.enqueue_hall_front(customer)
            self.try_release_hall_front()
            return True

        # Resolve exactly which station they need parking for
        if next_state == "HallOvfl":
            target_station = self.choose_b_side_station(customer)
        else:
            target_station = next_state

        # Check if they are allowed to enter
        if target_station is None or not self.can_enter_station_immediately(customer, target_station):
            return False  # Blocked, stay at current origin

        self.finalize_departure_from_origin(customer, origin, from_blocked)
        customer.advance_to_next_route_state()
        self.start_customer_at_station(customer, target_station)
        return True

    
    def finalize_departure_from_origin(self, customer, origin, from_blocked):
        station = self.stations[origin]

        if from_blocked:
            self.unblock_customer_at_origin(customer, origin)

        station.complete_service(customer, self.t)

        if origin == "Entrance":
            self.try_start_waiting_customer("Entrance")

    def try_release_blocked_from_origin(self, origin):
        progress = False

        while self.blocked_after_service[origin]:
            customer = self.blocked_after_service[origin][0]

            moved = self.try_move_customer(customer, origin, from_blocked=True)
            if not moved:
                break

            progress = True

        return progress

    def try_release_network_blocking(self):
        changed = True
        while changed:
            changed = False

            if self.try_release_hall_front():
                changed = True

            if self.try_release_blocked_from_origin("Entrance"):
                changed = True

            for origin in ["Hall", "Overflow", "DcDd", "Green", "Rest"]:
                if self.try_release_blocked_from_origin(origin):
                    changed = True

            # If the entrance server is free after some releases, start next check.
            before = len(self.stations["Entrance"].in_service)
            self.try_start_waiting_customer("Entrance")
            after = len(self.stations["Entrance"].in_service)
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