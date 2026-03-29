import numpy as np
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------

@dataclass
class StationParams:
    name:           str
    mean_service:   float    # seconds
    std_service:    float    # seconds
    parking_spaces: int      # in small-car equivalents
    max_queue:      float    # np.inf means unbounded


@dataclass
class CustomerClass:
    name:           str
    fraction:       float
    routing_matrix: np.ndarray   


# ---------------------------------------------------------------------------
# General settings
# ---------------------------------------------------------------------------

OPEN_TIME  = 10.0 * 3600   # seconds since midnight (10:00)
CLOSE_TIME = 17.0 * 3600   # seconds since midnight (17:00)

FRACTION_BIG = 0.47        # fraction of arriving vehicles that are big

# ---------------------------------------------------------------------------
# Arrival process
# Piecewise-constant rate; each tuple is (start_time_seconds, cars_per_hour).
# The rate applies from start_time until the next breakpoint.
# ---------------------------------------------------------------------------

ARRIVALS = [
    ( 9.50 * 3600,  11.876),
    (10.00 * 3600, 118.76),
    (10.75 * 3600,  47.504),
    (11.50 * 3600, 118.76),
    (13.00 * 3600, 118.76),
    (15.00 * 3600,  95.008),
    (16.50 * 3600,  59.38),
    (17.00 * 3600,   0),
]

# ---------------------------------------------------------------------------
# Station parameters
# parking_spaces is in small-car equivalents (big car occupies 2 spaces).
# max_queue is the maximum queue length (small-car equivalents) before
# cars are blocked at the entrance. np.inf = no limit.
# ---------------------------------------------------------------------------

STATIONS = {
    'Entrance':        StationParams('Entrance',        mean_service=30,  std_service=12,  parking_spaces=1,  max_queue=np.inf),
    'Hall Big Cars':   StationParams('Hall Big Cars',   mean_service=423, std_service=270, parking_spaces=6,  max_queue=7),
    'Hall Small Cars': StationParams('Hall Small Cars', mean_service=240, std_service=150, parking_spaces=12, max_queue=14),
    'Overflow':        StationParams('Overflow',        mean_service=180, std_service=150, parking_spaces=10, max_queue=0),
    'DcDd':            StationParams('DcDd',            mean_service=331, std_service=300, parking_spaces=7,  max_queue=0),
    'Green':           StationParams('Green',           mean_service=341, std_service=260, parking_spaces=5,  max_queue=0),
    'Rest':            StationParams('Rest',            mean_service=141, std_service=36,  parking_spaces=5,  max_queue=0),
}

# ---------------------------------------------------------------------------
# Customer classes
# ---------------------------------------------------------------------------

CUSTOMER_CLASSES = [

    CustomerClass(
        name     = 'Hall, Debris',
        fraction = 0.1010,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.130000, 0.000000, 0.000000, 0.870000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris, Rest 1',
        fraction = 0.0674,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.260000, 0.000000, 0.100000, 0.640000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris, Rest 2',
        fraction = 0.0589,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.370000, 0.000000, 0.060000, 0.570000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris, Rest 3',
        fraction = 0.0337,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.200000, 0.000000, 0.400000, 0.400000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 1.000000, 0.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Debris, Green, Rest',
        fraction = 0.1853,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [0.000000, 0.160000, 0.370000, 0.470000, 0.000000],  # FROM Entrance
            [0.000000, 0.220000, 0.000000, 0.000000, 0.780000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.030000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris, Rest 4',
        fraction = 0.1853,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.220000, 0.000000, 0.060000, 0.720000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris, Rest 1',
        fraction = 0.0253,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.170000, 0.000000, 0.330000, 0.500000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.400000, 0.600000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris 1',
        fraction = 0.0337,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [0.820000, 0.180000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 1.000000, 0.000000, 0.000000, 0.000000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris, Rest 2',
        fraction = 0.0084,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 1.000000, 0.000000, 0.000000, 0.000000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.500000, 0.500000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Debris 2',
        fraction = 0.1010,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [1.000000, 0.000000, 0.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.150000, 0.000000, 0.000000, 0.850000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

    CustomerClass(
        name     = 'Hall, Green, Rest',
        fraction = 0.0421,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [0.150000, 0.000000, 0.850000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),
    CustomerClass(
        name     = 'Green, Rest',
        fraction = 0.1579,
        routing_matrix = np.array([
      # TO:  Hall/Ovfl   DcDd      Green     Rest      Exit
            [0.000000, 0.000000, 1.000000, 0.000000, 0.000000],  # FROM Entrance
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Hall/Ovfl
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM DcDd
            [0.000000, 0.000000, 0.000000, 0.095000, 0.905000],  # FROM Green
            [0.000000, 0.000000, 0.000000, 0.000000, 1.000000],  # FROM Rest
        ]),
    ),

]