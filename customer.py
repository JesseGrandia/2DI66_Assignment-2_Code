class Customer :

    def __init__(self, arrivalTime, serviceTime, endPatienceTime):
        self.arrivalTime = arrivalTime
        self.serviceTime = serviceTime
        self.systemArrivalTime = arrivalTime
        self.endPatienceTime = endPatienceTime
        self.location = 0
        
    def moveTo(self, location, time, newServiceTime):
        self.location = location
        self.arrivalTime = time
        self.serviceTime = newServiceTime
        
    def leaveSystem(self):
        self.location = -1
        self.serviceTime = -1
        
    