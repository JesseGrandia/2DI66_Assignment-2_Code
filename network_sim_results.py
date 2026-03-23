class WRPSimResults:
    
    def __init__(self):
        self.waiting_times = {'Entrance': [], 'Hall': []}
        self.sojourn_times = []
        
    def register_wait(self, station, wait_time):
        self.waiting_times[station].append(wait_time)
        
    def register_sojourn(self, sojourn_time):
        self.sojourn_times.append(sojourn_time)
 
