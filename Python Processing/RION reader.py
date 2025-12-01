# RION processing 
# Processes files from Rion soundmeters and converts them the svan TERTs format 

import tkinter as tk
from tkinter import filedialog
import os
import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt

# logsum function to do logarithm summation
def logsum(L1):   
    temp = 10**(L1/10)
    temp = np.nansum(temp)
    L_sum = 10*np.log10(temp)
    L_sum = round(L_sum, 2)
    return(L_sum)

# acorr function to apply a correction
def acorr(f):
    R = (12194**2*f**4)/((f**2+20.6**2)*np.sqrt((f**2+107.7**2)*(f**2+737.9**2))*(f**2+12194**2))
    A = 20*np.log10(R)+2
    return(A)

# ccorr function to apply C-weighting correction
def ccorr(f):
    R = (12194**2*f**2)/((f**2+20.6**2)*(f**2+12194**2))
    C = 20*np.log10(R)+0.06
    return C

def plotFFT(x, t, NFFT, Fs):
    fig, (ax1, ax2) = plt.subplots(nrows=2,sharex=True)
    ax1.plot(t, x)
    ax1.set_ylabel('Measured signal LAeq')
    
    Pxx, freqs, bins, im = ax2.specgram(x, NFFT=NFFT, Fs=Fs)
    # The `specgram` method returns 4 objects. They are:
    # - Pxx: the periodogram
    # - freqs: the frequency vector
    # - bins: the centers of the time bins
    # - im: the .image.AxesImage instance representing the data in the plot
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Frequency (Hz)')
    ax2.set_xlim(0, 3600)
    
    return(Pxx, freqs, bins, im)


# main script 
def main():
    t0 = time.time() 

    # Locate then load first 5 lines from the sample SVAN file
    samplefile_dir = os.path.dirname(os.path.abspath(__file__))
    samplefile_path = os.path.join(samplefile_dir, 'samplefile.txt')
    
    header_lines = []
    with open(samplefile_path, "r", encoding="utf-8") as f:
        for _ in range(5):
            header_lines.append(f.readline().strip())
             
    # Output file intialisation
    output_file = "dagfile.txt"
        
    # Write header lines
    with open(output_file, "w", encoding="utf-8") as out:
        for line in header_lines:
            out.write(line + '\n')

    ## User selection of folder with input data and output write location
    root = tk.Tk()
    root.withdraw()   
    folder = filedialog.askdirectory(title="Select data folder")

    # Frequencies
    freq = np.array([20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000])
            
    ## Processing of datas
    with open(output_file, "a", encoding="utf-8") as out:
        for f in os.scandir(folder):
                
            # Read the first file
            path = os.path.join(folder,f)
            NoiseData = pd.read_csv(path)
            
            print("Processing file ",f)
                    
            # Assign SVAN variables to the correct index in the DataFrame 
            Num = NoiseData["Address"]
            DateTime = NoiseData["Start Time"]
            LAeq = NoiseData['Leq(Main)']
            LzFreq = NoiseData.loc[:,"20Hz":"20kHz"]
            LaFreq = LzFreq + acorr(freq)
            LcFreq = LzFreq + ccorr(freq)
                
            # Variable initialisation 
            TotalZ = np.zeros((len(Num),1))
            TotalA = np.zeros((len(Num),1))
            TotalC = np.zeros((len(Num),1))
                    
            # Compute the totals in A, C and Z 
            TotalZ = LzFreq.apply(logsum, axis=1)
            TotalA = LaFreq.apply(logsum, axis=1)
            TotalC = LcFreq.apply(logsum, axis=1)
            
            # Format time axis
            #formatted_time = pd.to_datetime(DateTime).strftime("%d/%m/%Y %H:%M:%S")
            
            # Output update, row by row, to populate the file with the extracted / computed data 
            rows = []
            for i in range(len(Num)):
                formatted_time = pd.to_datetime(DateTime.iloc[i]).strftime("%d/%m/%Y %H:%M:%S")
                row = [str(Num.iloc[i]), formatted_time, str(LAeq.iloc[i])]
                row += [str(val) for val in LzFreq.iloc[i, :]]
                row += [str(TotalA.iloc[i]), str(TotalC.iloc[i]), str(TotalZ.iloc[i])]
                rows.append('\t'.join(row))
            out.write('\n'.join(rows) + '\n')
            
            # Create and plot spectrogram
            #plotFFT(TotalA)                          
        
        # Tik tok on the clock but the party won't stop 
        t1 = time.time()
        total = t1 - t0 
        print("The scirpt took",round(total,2), " seconds to complete")     

# Code execution 
if __name__ == "__main__":

    main()