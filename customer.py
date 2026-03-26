class Customer:
    def __init__(self, cust_id, arr_time, is_big, cust_class, route):
        self.id = cust_id
        self.arrivalTime = arr_time
        self.is_big = is_big
        self.spots_needed = 2 if is_big else 1
        self.cust_class = cust_class

        self.route = route
        self.route_index = -1   # important: first advance after Entrance goes to route[0]
        self.current_station = None
        self.finished = False

        self.queue_arrival_times = {}
        self.service_start_times = {}
        self.departure_times = {}

    def next_station(self):
        if self.route_index >= len(self.route):
            return None
        if self.route_index < 0:
            return None
        return self.route[self.route_index]

    def advance_route(self):
        self.route_index += 1