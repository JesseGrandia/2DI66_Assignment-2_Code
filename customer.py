class Customer:
    def __init__(self, cust_id, arr_time, is_big, cust_class, route, customer_type):
        self.id = cust_id
        self.arrivalTime = arr_time
        self.is_big = is_big
        self.spots_needed = 2 if is_big else 1
        self.cust_class = cust_class
        self.customer_type = customer_type  # "A" or "B"

        # Route uses config state names:
        # "HallOvfl", "DcDd", "Green", "Rest"
        self.route = route
        self.route_index = -1

        self.current_station = None
        self.finished = False
        self.blocked_after_service = False

        self.queue_arrival_times = {}
        self.service_start_times = {}
        self.departure_times = {}

    def current_route_state(self):
        if 0 <= self.route_index < len(self.route):
            return self.route[self.route_index]
        return None

    def peek_next_route_state(self):
        idx = self.route_index + 1
        if 0 <= idx < len(self.route):
            return self.route[idx]
        return None

    def advance_to_next_route_state(self):
        self.route_index += 1
        return self.current_route_state()