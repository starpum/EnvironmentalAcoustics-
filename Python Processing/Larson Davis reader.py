# LD processing 
# Processes files from Larson Davis soundmeters into graphs and synthetizes the results into a single excel workbook

import tkinter as tk
from tkinter import filedialog
import openpyxl
from openpyxl import Workbook
import os
import numpy as np
import matplotlib as plt

# main script 
def main():
    root = tk.Tk()
    root.withdraw()

    # Select folder with msm datas
    folder = filedialog.askdirectory()

    ## Variables creation
    n = 0
    f_11 = ["Hz", 8, 16, 31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    f_13 = ["Hz", 6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 31.5, 40.0, 50.0, 63.0, 80.0, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000]

    #Output workbook 
    wb_out = Workbook()         
    ws_out = wb_out.active
    ws_out.title = 'Summary'
    headers = ["Point name", "LAeq", "LA50", "LA90", "LA95"]
    ws_out.append(headers)

    #grab list of files in folder
    xls_files = [f for f in os.listdir(folder)
                if f.lower().endswith(".xlsx") and os.path.isfile(os.path.join(folder, f))]
    pt_name = [""] * len(xls_files) #Point name for saving

    ## Processing of datas
    for f in os.listdir(folder):
        #Open the worksheet
        path = os.path.join(folder,f)
        wb = openpyxl.load_workbook(path)
        
        #Ask for point name 
        print(f"Measurement point name for '{f}':")
        pt_name[n] = input("> ")
        
        # Get relevant overall datas from the "Summary" sheet
        ws = wb["Summary"]

        pt = pt_name[n]
        LAeq = ws['B73'].value
        LA50 = ws['B91'].value
        LA90 = ws['B92'].value
        LA95 = ws['B93'].value
        output_data = [pt, LAeq, LA50, LA90, LA95]
        ws_out.append(output_data)
            
        #Get spectral data from the "OBA" sheet
        ws = wb["OBA"]
        ws_out_spectra = wb_out.create_sheet(pt_name[n])
        
        s_11 = [ws.cell(row= 3,column=i).value for i in range(2,14)]
        s_13 = [ws.cell(row= 9,column=i).value for i in range(2,38)]
        
        ws_out_spectra.append(f_11)
        ws_out_spectra['A2'] = pt_name[n]
        for i in range(2,14) :
            ws_out_spectra.cell(row= 2,column=i).value = s_11[i-2]
        
        ws_out_spectra.append(f_13)
        ws_out_spectra.move_range("A3:AK3",rows=1)
        ws_out_spectra['A5'] = pt_name[n]
        for i in range(2,38) :
            ws_out_spectra.cell(row= 5,column=i).value = s_13[i-2]
    
        
        # #Plot LAeq from "Time history" sheet
        # ws = wb["Time History"]
        # for r in range(2,ws.max_row):
        #     col = 2
        #     v = ws[f"{col}{r}"].value
        #     if v is not None and str(v).strip() != "":
        #         last = r
        
        n = n+1
        
        wb_out.save('Results.xlsx')
        
        
# Code execution 
if __name__ == "__main__":

    main()