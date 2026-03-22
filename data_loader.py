import os

import pandas as pd

class DataLoader: 
    def __init__(self, config):
        self.input_file_path = config['data']['raw_data']
        self.arrival_service_file = config['exports']['service_arrival_data']
        self.customer_file = config['exports']['customer_data']
        
        self.arrival_service_data = None
        self.customer_data = None
        
        
    def load_data(self):
        '''Read the raw data file'''
        self.arrival_service_data = pd.read_excel(
            self.input_file_path, 
            sheet_name='Arrival and service processes'
            )
        self.customer_data = pd.read_excel(
            self.input_file_path, 
            sheet_name='Customer classes and routing'
            )
        
    def export_cleaned_data(self):
        """Exports the cleaned DataFrames to CSV for manual verification."""
        self.arrival_service_data.to_csv(
            self.arrival_service_file, index=False
            )
        self.customer_data.to_csv(self.customer_file, index=False)

    def run(self):
        self.load_data()
        self.export_cleaned_data()
        
    


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    config = {
        "data": {
            "raw_data": os.path.join(
                base_dir, "data", "Data Lodewijkstraat.xlsx"
                )
            },
        "exports": {
            "service_arrival_data": os.path.join(
                base_dir, "exports", "service_arrival_data.csv"
                ),
            "customer_data": os.path.join(
                base_dir, "exports", "customer_data.csv"
                )
            }
        }
    
    loader = DataLoader(config)
    loader.run()
    