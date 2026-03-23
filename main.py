import os

from config import ARRIVALS
from config import STATIONS
from config import CUSTOMER_CLASSES

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base_dir, "exports"), exist_ok=True)
    
    file_config = {
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
    print(CUSTOMER_CLASSES)
    print('\n')
    print('-'*79)
    print(ARRIVALS)
    print('\n')
    print('-'*79)
    print(STATIONS)
    
    


if __name__ == "__main__":
    main()
    