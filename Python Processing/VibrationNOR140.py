# Vibration NOR140
# Processes vibraiton data measured with NOR140 in EU into graphs and synthetizes the results into a single excel workbook

import tkinter as tk
from tkinter import filedialog
import os
import numpy as np
import pandas as pd
import matplotlib as plt

# logsum function to do logarithm summation
def logsum(L1):   
    temp = 10**(L1/10)
    temp = np.nansum(temp)
    L_sum = 10*np.log10(temp)
    L_sum = round(L_sum, 2)
    return(L_sum)

# Compute angular frequency from a frequency vector
def AngularFrequency(f_vector):
    return(f_vector*2*np.pi)
    
# main script 
def main():
    
    # Output file intialisation
    output_file = "vibration_results.txt"

    # User selection of folder with input data and output write location
    root = tk.Tk()
    root.withdraw()   
    folder = filedialog.askdirectory(title="Select data folder")

    # Variables creation
    n = 0
    freq = np.array([6.3, 8, 10, 12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000])
    w = AngularFrequency(freq)
    
    print(len(w))

    # Grab list of files in folder
    xls_files = [f for f in os.listdir(folder)
                if f.endswith(".xlsx") and os.path.isfile(os.path.join(folder, f))]
    pt_name = [""] * len(xls_files) #Point name for saving

    # Processing of datas
    with open(output_file, "a", encoding="utf-8") as out:
        for f in os.scandir(folder):

            # Read the first file
            path = os.path.join(folder,f)
            VibrationData = pd.read_excel(path)
            
            # Build point name vector
            pt_name[n] = "position " + str([n])
            
            # Get relevant overall datas (5 header rows)
            n_headers = 5 
            acceleration = VibrationData.iloc[n_headers, 8:44]
            DateTime     = VibrationData.iloc[n_headers, 1]
            
            # Compute displacement and velocity 
            displacement = acceleration/w
            velocity = displacement/w
            
            # Output update, row by row, to populate the file with the extracted / computed data 
            rows = []
            for i in range(len(acceleration)):
                formatted_time = pd.to_datetime(DateTime.iloc[i]).strftime("%d/%m/%Y %H:%M:%S")
                row = [pt_name, formatted_time]
                row += [str(val) for val in acceleration.iloc[i, :]]
                row += [str(val) for val in displacement.iloc[i, :]]
                row += [str(val) for val in velocity.iloc[i, :]]
                rows.append('\t'.join(row))
            out.write('\n'.join(rows) + '\n')
            
            # Plot the acceleration and displcament [mm] per frequency 
        

# Code execution 
if __name__ == "__main__":

    main()