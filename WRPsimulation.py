import numpy as np
from collections import deque

from event import Event
from FES import FES
from customer import Customer 
from network_sim_results import WRPSimResults
import config 


class WRPSimulation:
    def __init__(self, config_module):
        self.config = config_module
        
        # Available parking spots (in small-car equivalents)
        self.available_spots = {
            'Entrance': 1, # The operator checking city passes
            'Hall': self.config.STATIONS['Hall Small Cars'].parking_spaces, # 12
            'Overflow': self.config.STATIONS['Overflow'].parking_spaces,    # 10
            'DcDd': self.config.STATIONS['DcDd'].parking_spaces,            # 7
            'Green': self.config.STATIONS['Green'].parking_spaces,          # 5
            'Rest': self.config.STATIONS['Rest'].parking_spaces             # 5
        }
        
        # Queues explicitly mentioned in the PDF
        self.queues = {
            'Entrance': deque(), # Cars outside on the road
            'Hall': deque()      # Cars between entrance and Hall/Overflow
        }
        self.hall_queue_len = 0  # In small-car equivalents
        
        # Dictionary to track customers who finished service but are blocked
        self.blocked_at = {station: deque() for station in self.available_spots.keys()}
        
        self.fes = FES()
        self.res = WRPSimResults()
        
    # --- Helper Methods ---

    def generate_next_arrival(self, current_time):
        """Generates the next arrival using the Thinning Algorithm for non-stationary Poisson processes."""
        max_rate = max([rate for _, rate in self.config.ARRIVALS]) / 3600.0 # max cars per second
        t = current_time
        while True:
            u1 = np.random.exponential(1.0 / max_rate)
            t += u1
            if t >= self.config.CLOSE_TIME:
                return float('inf')
            
            # Find current rate
            current_rate = 0
            for i in range(len(self.config.ARRIVALS) - 1):
                if self.config.ARRIVALS[i][0] <= t < self.config.ARRIVALS[i+1][0]:
                    current_rate = self.config.ARRIVALS[i][1] / 3600.0
                    break
            
            if np.random.rand() < (current_rate / max_rate):
                return t

    def get_service_time(self, station_name):
        """Generates a non-negative service time using a Gamma distribution."""
        # Map generic 'Hall' back to specific config data
        if station_name == 'Hall':
            station_name = 'Hall Big Cars' if np.random.rand() < self.config.FRACTION_BIG else 'Hall Small Cars'
        
        params = self.config.STATIONS[station_name]
        if params.std_service == 0: return params.mean_service
        
        # Gamma dist parameters: shape = (mean/std)^2, scale = var/mean
        shape = (params.mean_service / params.std_service) ** 2
        scale = (params.std_service ** 2) / params.mean_service
        return np.random.gamma(shape, scale)

    def get_next_destination(self, customer, current_station):
        """Determines the next step from the customer's routing matrix."""
        stations_order = ['Entrance', 'Hall/Ovfl', 'DcDd', 'Green', 'Rest']
        destinations = ['Hall/Ovfl', 'DcDd', 'Green', 'Rest', 'Exit']
        
        # If they are in Hall or Overflow, they look at the 'Hall/Ovfl' row
        if current_station in ['Hall', 'Overflow']:
            current_station = 'Hall/Ovfl'
            
        row_idx = stations_order.index(current_station)
        probs = customer.cust_class.routing_matrix[row_idx]
        probs = probs / np.sum(probs) # Normalize to avoid float rounding errors
        
        return np.random.choice(destinations, p=probs)

    def resolve_hall_overflow_routing(self, customer):
        """Rules: Big cars -> Hall. Small cars -> Overflow -> Hall."""
        if customer.is_big:
            return 'Hall'
        else:
            if self.available_spots['Overflow'] >= 1:
                return 'Overflow'
            return 'Hall'

    # --- Core Simulation Engine ---

    def simulate(self):
        t = self.config.OPEN_TIME
        first_arr = self.generate_next_arrival(t)
        
        if first_arr < self.config.CLOSE_TIME:
            is_big = np.random.rand() < self.config.FRACTION_BIG
            spots = 2 if is_big else 1
            cust_class = np.random.choice(self.config.CUSTOMER_CLASSES, 
                                          p=[c.fraction for c in self.config.CUSTOMER_CLASSES])
            
            c0 = Customer(first_arr, is_big, spots, cust_class)
            self.fes.add(Event(Event.ARRIVAL, first_arr, c0))

        while not self.fes.isEmpty():
            e = self.fes.next()
            t = e.time
            c = e.customer

            if e.type == Event.ARRIVAL:
                self.handle_arrival(t, c)
            elif e.type == Event.DEPARTURE:
                self.handle_departure(t, c)

        return self.res

    def handle_arrival(self, t, customer):
        # 1. Add to external entrance queue
        customer.queue_arrival_times['Entrance'] = t
        self.queues['Entrance'].append(customer)
        
        # 2. Try to process queues
        self.process_queues_and_blocks(t)

        # 3. Schedule next external arrival
        next_arr = self.generate_next_arrival(t)
        if next_arr < self.config.CLOSE_TIME:
            is_big = np.random.rand() < self.config.FRACTION_BIG
            spots = 2 if is_big else 1
            cust_class = np.random.choice(self.config.CUSTOMER_CLASSES, 
                                          p=[c.fraction for c in self.config.CUSTOMER_CLASSES])
            next_c = Customer(next_arr, is_big, spots, cust_class)
            self.fes.add(Event(Event.ARRIVAL, next_arr, next_c))

    def handle_departure(self, t, customer):
        current_station = customer.current_station
        next_station = self.get_next_destination(customer, current_station)

        if next_station == 'Exit':
            self.available_spots[current_station] += customer.spots_needed
            self.res.register_sojourn(t - customer.arrivalTime)
            self.process_queues_and_blocks(t) # Freed up space, trigger movements!
        else:
            # They want to move to another station inside the WRP.
            # They are now blocked at their current parking spot until space opens.
            self.blocked_at[current_station].append((customer, next_station))
            self.process_queues_and_blocks(t)

    def process_queues_and_blocks(self, t):
        """
        This cascading logic handles all movements. Whenever a space frees up, 
        we check if blocked cars can move, then if Hall queued cars can park, 
        then if the Entrance Operator can process a car.
        """
        progress = True
        while progress:
            progress = False

            # 1. Unblock parked cars that finished service but had nowhere to go
            for station in list(self.available_spots.keys()):
                if self.blocked_at[station]:
                    cust, next_dest = self.blocked_at[station][0]
                    
                    if next_dest == 'Hall/Ovfl':
                        actual_dest = self.resolve_hall_overflow_routing(cust)
                    else:
                        actual_dest = next_dest
                        
                    if self.available_spots[actual_dest] >= cust.spots_needed:
                        self.blocked_at[station].popleft()
                        self.available_spots[station] += cust.spots_needed # Free old spot
                        self.available_spots[actual_dest] -= cust.spots_needed # Take new spot
                        
                        cust.current_station = actual_dest
                        serv_time = self.get_service_time(actual_dest)
                        self.fes.add(Event(Event.DEPARTURE, t + serv_time, cust))
                        progress = True
                        continue # Restart loop to re-evaluate cascaded spaces

            # 2. Check the Hall Queue (Cars inside WRP waiting to park in Hall/Overflow)
            if self.queues['Hall']:
                cust = self.queues['Hall'][0]
                actual_dest = self.resolve_hall_overflow_routing(cust)
                if self.available_spots[actual_dest] >= cust.spots_needed:
                    self.queues['Hall'].popleft()
                    self.hall_queue_len -= cust.spots_needed
                    self.available_spots[actual_dest] -= cust.spots_needed
                    
                    cust.current_station = actual_dest
                    self.res.register_wait('Hall', t - cust.queue_arrival_times['Hall'])
                    serv_time = self.get_service_time(actual_dest)
                    self.fes.add(Event(Event.DEPARTURE, t + serv_time, cust))
                    progress = True

            # 3. Check the Entrance Operator (Cars that just showed their city pass)
            if self.blocked_at['Entrance']:
                cust, next_dest = self.blocked_at['Entrance'][0]
                
                if next_dest == 'Hall/Ovfl':
                    # Can they join the Hall queue? (Max 14 small car equivalents)
                    if self.hall_queue_len + cust.spots_needed <= 14:
                        self.blocked_at['Entrance'].popleft()
                        self.available_spots['Entrance'] += 1 # Operator is free
                        
                        # Join Hall Queue
                        cust.queue_arrival_times['Hall'] = t
                        self.queues['Hall'].append(cust)
                        self.hall_queue_len += cust.spots_needed
                        progress = True
                else:
                    # Going directly to Green/Rest
                    if self.available_spots[next_dest] >= cust.spots_needed:
                        self.blocked_at['Entrance'].popleft()
                        self.available_spots['Entrance'] += 1 # Operator is free
                        self.available_spots[next_dest] -= cust.spots_needed
                        
                        cust.current_station = next_dest
                        serv_time = self.get_service_time(next_dest)
                        self.fes.add(Event(Event.DEPARTURE, t + serv_time, cust))
                        progress = True

            # 4. Check the External Road Queue (Move to Entrance Operator)
            if self.queues['Entrance'] and self.available_spots['Entrance'] == 1:
                cust = self.queues['Entrance'].popleft()
                self.available_spots['Entrance'] -= 1
                cust.current_station = 'Entrance'
                
                self.res.register_wait('Entrance', t - cust.queue_arrival_times['Entrance'])
                serv_time = self.get_service_time('Entrance')
                self.fes.add(Event(Event.DEPARTURE, t + serv_time, cust))
                progress = True

# ==============================================================================
# Run execution
# ==============================================================================
if __name__ == '__main__':
    sim = WRPSimulation(config)
    results = sim.simulate()
    
    print(f"Simulation Complete. Processed {len(results.sojourn_times)} customers.")
    print(f"Average Wait at Entrance: {np.mean(results.waiting_times['Entrance']):.2f} seconds")
    if results.waiting_times['Hall']:
        print(f"Average Wait in Hall Queue: {np.mean(results.waiting_times['Hall']):.2f} seconds")
    print(f"Average Total Time in System: {np.mean(results.sojourn_times):.2f} seconds")