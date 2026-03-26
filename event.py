class Event:
    ARRIVAL = 0
    DEPARTURE = 1

    def __init__(self, typ, time, customer, station=None, external=False):
        self.type = typ
        self.time = time
        self.customer = customer
        self.station = station
        self.external = external

    def __lt__(self, other):
        return self.time < other.time

    def __repr__(self):
        s = ('Arrival', 'Departure')
        st = f", station={self.station}" if self.station is not None else ""
        ext = ", external=True" if self.external else ""
        return f"{s[self.type]} at t={self.time:.2f}{st}{ext}"
    