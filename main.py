import os

from config import ARRIVALS
from config import STATIONS
from config import CUSTOMER_CLASSES

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base_dir, "exports"), exist_ok=True)
    
    config = {
        "data": {
            "raw_data": os.path.join(
                base_dir, "data", "Data Lodewijkstraat.xlsx"
                )
            },
        "exports": {
            "processed_data": os.path.join(
                base_dir, "exports", "processed_data.csv"
                )
            }
        }
    
    print('-'*79)
    # Name, %, np.Matrix
    print(CUSTOMER_CLASSES)
    
    print('\n')
    print('-'*79)
    # Arrival rates (Secs na 00:00, rate)
    print(ARRIVALS)
    
    print('\n')
    print('-'*79)
    # Service rates {Station: ALLE STATS, ...}
    print(STATIONS)
    
    


if __name__ == "__main__":
    main()
    