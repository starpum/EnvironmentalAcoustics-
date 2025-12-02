# Vibration NOR140
# Processes vibraiton data measured with NOR140 in EU into graphs and synthetizes the results into a single excel workbook

import tkinter as tk
from tkinter import filedialog
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def load_overview_nor140(path, w):
    """Load NOR140 overview Excel file
    Input  : measurement of vibrations made with E.U. 
    Return : formatted datetimes, acceleration, displacement, velocity."""
    
    df = pd.read_excel(path, engine="openpyxl", header=None)
    data = df.iloc[4:].reset_index(drop=True)  # skip header rows
    dt = pd.to_datetime(data[1].astype(str).str.strip("() "), format="%Y/%m/%d %H:%M:%S.%f", errors="raise")
    fmt = dt.dt.strftime("%d/%m/%Y %H:%M:%S.%f")
    acc_dB = data.iloc[:, 7:33].astype(float).to_numpy()  # 26 bands up to 2 kHz
    acc = 2*10**(-5)*10**(acc_dB/20)
    vel = (acc / w) 
    disp = (vel / (w**2)) * 1000 #conversion to mm
    return fmt, acc, disp, vel
    
def main():  
    # User selection of folder with input data and output write location
    root = tk.Tk()
    root.withdraw()   
    input_folder = filedialog.askdirectory(title="Select data folder")

    # Output folder = parent of input folder
    output_folder = os.path.dirname(input_folder)
    plots_folder = os.path.join(output_folder, "plots")
    os.makedirs(plots_folder, exist_ok=True)

    # Frequencies and angular frequency
    #all_freq = np.array([6.3, 8, 10, 12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000])
    freq = np.array([6.3, 8, 10, 12.5, 16, 20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000])
    freq_corr = np.arange(8, 8 + (len(freq)-1) + 1) 
    real_freq = 10**(freq_corr/10)
    w = 2 * np.pi * real_freq

    # Prepare CSV output
    output_csv = os.path.join(output_folder, "vibration_results.csv")
    header_line1 = ["Position", "Date&Time"] + ["Acceleration [m/s-1]"] * len(freq) + ["Displacement [mm]"] * len(freq) + ["Velocity [mm/s]"] * len(freq)
    header_line2 = [" ", " "] + [f"{f}Hz" for f in freq] * 3

    rows = []
    xls_files = [f for f in os.listdir(input_folder) if f.endswith(".xlsx")]

    #Data processings and ploting 
    for n, fname in enumerate(xls_files):
        path = os.path.join(input_folder, fname)
        fmt, acc, disp, vel = load_overview_nor140(path, w)

        for i in range(len(fmt)):

            pt = f"Pump {n+1} - location {i+1}"
            print(f"Proccesing {pt}")
            
            row = [pt, fmt.iloc[i]]
            row += [*map(str, acc[i])]
            row += [*map(str, disp[i])]
            row += [*map(str, vel[i])]
            rows.append(row)

            # Acceleration plot
            plt.figure(figsize=(8, 6))
            plt.semilogx(freq, acc[i], marker='o', label='Acceleration [m/s-2]')
            plt.title(f'{pt} - {fmt.iloc[i]}')
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Amplitude')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plot_file = os.path.join(plots_folder, f'Acceleration_{pt}.png')
            plt.savefig(plot_file)
            plt.close()
            
            # Displacement plot
            plt.figure(figsize=(8, 6))
            plt.loglog(freq, disp[i], marker='s', label='Displacement [mm]')
            plt.title(f'{pt} - {fmt.iloc[i]}')
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Amplitude')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plot_file = os.path.join(plots_folder, f'Displacement_{pt}.png')
            plt.savefig(plot_file)
            plt.close()
            
            # Velocity plot
            plt.figure(figsize=(8, 6))
            plt.semilogx(freq, vel[i], marker='^', label='Velocity [mm/s]')
            plt.title(f'{pt} - {fmt.iloc[i]}')
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Amplitude')
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plot_file = os.path.join(plots_folder, f'Velocity_{pt}.png')
            plt.savefig(plot_file)
            plt.close()
                        
    # Write combined CSV
    with open(output_csv, "w", encoding="utf-8") as f:
        f.write(",".join(header_line1) + "\n")
        f.write(",".join(header_line2) + "\n")
        for row in rows:
            f.write(",".join(row) + "\n")

# Code execution 
if __name__ == "__main__":
    main()