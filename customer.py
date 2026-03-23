class Customer:
    
    def __init__(self, arr_time, is_big, spots_needed, cust_class):
        self.arrivalTime = arr_time
        self.is_big = is_big
        self.spots_needed = spots_needed
        self.cust_class = cust_class
        
        self.current_station = 'Entrance Queue'
        self.queue_arrival_times = {}