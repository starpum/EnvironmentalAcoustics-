import sounddevice as sd # type: ignore
import numpy as np
from scipy.signal import bilinear, lfilter, butter, sosfilt
import time
import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime
import csv
import struct
from pathlib import Path


CENTRAL_FREQS = np.array([
    20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315,
    400, 500, 630, 800, 1000, 1250, 1600, 2000, 2500, 3150,
    4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000
])

CALIBRATION_CORRECTION_DB = {
    20: -1.80,
    25: -1.25,
    31.5: -0.97,
    40: -0.81,
    50: -0.55,
    63: -0.35,
    80: -0.26,
    100: -0.33,
    125: -0.39,
    160: -0.39,
    200: -0.33,
    250: -0.32,
    315: -0.42,
    400: -0.49,
    500: -0.47,
    630: -0.35,
    800: -0.19,
    1000: -0.03,
    1250: 0.08,
    1600: 0.16,
    2000: 0.22,
    2500: 0.28,
    3150: 0.29,
    4000: 0.28,
    5000: 0.25,
    6300: 0.25,
    8000: 0.38,
    10000: 0.54,
    12500: 0.54,
    16000: 0.04,
    20000: -0.79
}

after_id = None

BUFFER = []
SAMPLERATE = 48000

DUREE_MEMOIRE = 5  
BUFFER_MEMOIRE = []

def audio_callback(indata, frames, time_info, status):
    global BUFFER
    if status:
        print("[Stream audio] Error : ", status)
    BUFFER.extend(indata[:, 0]) 

def record_audio(duree, sample_rate=48000, canal=1):
    audio = sd.rec(int(duree * sample_rate), samplerate=sample_rate, channels=canal)
    sd.wait()
    return audio.flatten()

def pond_tempor(signal, tau, sample_rate=48000):
    alpha = 1 / (tau * sample_rate)
    alpha = min(alpha, 1.0)
    power = signal**2
    output = np.zeros_like(power)
    output[0] = power[0]
    for i in range(1, len(power)):
        output[i] = (1 - alpha) * output[i - 1] + alpha * power[i]
    return np.sqrt(np.mean(output))

def compute_rms(signal):
    return np.sqrt(np.mean(signal**2))

def calibrate_mic(rms_mesure, db_spl_reference=94):
    p_ref = 20e-6
    ref_pressure = p_ref * 10**(db_spl_reference / 20)
    return ref_pressure / rms_mesure

def filter_pond(signal, type="A", sample_rate=48000):
    if type == "A":
        f1, f2, f3, f4 = 20.598997, 107.65265, 737.86223, 12194.217
        A1000 = 1.9997
        nums = [(2*np.pi*f4)**2 * (10**(A1000/20)), 0, 0, 0, 0]
        dens = np.polymul([1, 4*np.pi*f4, (2*np.pi*f4)**2],
                          [1, 4*np.pi*f1, (2*np.pi*f1)**2])
        dens = np.polymul(np.polymul(dens, [1, 2*np.pi*f3]), [1, 2*np.pi*f2])
        b, a = bilinear(nums, dens, sample_rate)
        return lfilter(b, a, signal)
    elif type == "C":
        f1, f4, C1000 = 20.598997, 12194.217, 0.0619
        nums = [(2*np.pi*f4)**2 * (10**(C1000/20)), 0, 0]
        dens = np.polymul([1, 4*np.pi*f4, (2*np.pi*f4)**2],
                          [1, 4*np.pi*f1, (2*np.pi*f1)**2])
        b, a = bilinear(nums, dens, sample_rate)
        return lfilter(b, a, signal)
    elif type == "Z":
        return signal
    else:
        raise ValueError("Ponderation type not recognized")

def signal_to_db_pond(signal, conversion_factor, tau, type_pond_freq):
    global BUFFER_MEMOIRE
    BUFFER_MEMOIRE = np.concatenate((BUFFER_MEMOIRE, signal))
    if len(BUFFER_MEMOIRE) > DUREE_MEMOIRE * 48000:
        BUFFER_MEMOIRE = BUFFER_MEMOIRE[-(DUREE_MEMOIRE * 48000):]

    filtered_signal = filter_pond(BUFFER_MEMOIRE, type=type_pond_freq, sample_rate=48000)
    p_rms_pond = exponential_time_pondertaion(filtered_signal, tau=tau, sample_rate=48000) * conversion_factor
    return 20 * np.log10(p_rms_pond / 20e-6)


def signal_to_db_spl(signal, factor):
    p_rms = compute_rms(signal) * factor
    return 20 * np.log10(p_rms / 20e-6)

def octave_band_filter(f_center, fs, order=4):
    f_min = f_center / (2 ** (1/6))
    f_max = f_center * (2 ** (1/6))
    nyquist = fs / 2
    if f_max >= nyquist:
        f_max = nyquist - 1
    sos = butter(order, [f_min, f_max], btype='bandpass', fs=fs, output='sos')
    return sos

def band_analysis(signal, fs, factor, correction_table=CALIBRATION_CORRECTION_DB):
    SPL_levels = []
    nyquist = fs / 2
    for f_center in CENTRAL_FREQS:
        f_max = f_center * (2 ** (1/6))
        if f_max < nyquist or f_center == 20000:
            sos = octave_band_filter(f_center, fs)
            filtered_signal = sosfilt(sos, signal)
            spl = signal_to_db_spl(filtered_signal, factor)
            correction = correction_table.get(f_center, 0.0)
            SPL_levels.append(spl - correction)
        else:
            SPL_levels.append(np.nan)
    return SPL_levels


def save_csv(SPL_and_pond, output_csv):
    try:
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = [date_time] + SPL_and_pond

        if not os.path.exists(output_csv):
            with open(output_csv, mode='w', newline='') as f:
                writer = csv.writer(f)
                header = ['Date&Time'] + ['LAeq'] + [f"{int(f)}Hz" for f in CENTRAL_FREQS] + ['SPL_A', 'SPL_C', 'SPL_Z']
                writer.writerow(header)

        with open(output_csv, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(line)

    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")


def record_calibration(factor, fichier="calibration.txt"):
    chemin_fichier = os.path.join(os.path.dirname(__file__), fichier)
    with open(chemin_fichier, "w") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{factor}\n{now}")

def load_calibration(fichier="calibration.txt"):
    chemin_fichier = os.path.join(os.path.dirname(__file__), fichier)
    if os.path.exists(chemin_fichier):
        with open(chemin_fichier, "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                factor = float(lines[0].strip())
                date = lines[1].strip()
                return factor, date
    return None, None

def exponential_time_pondertaion(signal, tau, sample_rate=48000):
    n = len(signal)
    if n == 0:
        return 0.0
    t = np.arange(n)[::-1] / sample_rate
    poids = np.exp(-t / tau)
    power = signal**2
    return np.sqrt(np.sum(poids * power) / np.sum(poids))


def compute_LAeq_1s(signal, factor, sample_rate=48000):
    
    """
    Compute LAeq,1s (A-weighted equivalent continuous sound level over 1 second).
    
    Parameters:
        signal (numpy.ndarray): 1-second audio signal (raw samples).
        facteur (float): Calibration factor (Pa per unit).
        sample_rate (int): Sampling rate in Hz (default: 48000).
    
    Returns:
        float: LAeq,1s in dB(A).
    """
    # Apply A-weighting filter
    signal_A = filter_pond(signal, type="A", sample_rate=sample_rate)
    # Convert to physical pressure using calibration factor
    signal_A_pa = signal_A * factor
    # Compute RMS over the entire 1-second window
    p_rms_A = np.sqrt(np.mean(signal_A_pa ** 2))
    # Convert to dB(A)
    LAeq_1s = 20 * np.log10(p_rms_A / 20e-6)

    return LAeq_1s

def launch_measure(type_temp="Fast", recalibrate=True, plage="normale", record=True):
    if type_temp == "Fast":
        tau = 0.125
    elif type_temp == "Slow":
        tau = 1.0
    elif type_temp == "Impulse": # Pas encore au point
        tau = 0.035

    if recalibrate:
        print("Place calibrator on mic (94 dB SPL @ 1 kHz)")
        time.sleep(10)
        signal_calibration = record_audio(1)
        rms_calibration = compute_rms(signal_calibration)
        factor = calibrate_mic(rms_calibration)
        record_calibration(factor)
        print(f"Calibrated conversion factor : {factor:.6f} Pa/unit")
    else:
        factor, _ = load_calibration()
        print("Previous calibration uploaded")
        if factor is None:
            print("No previous calibration found. Please recalibrate.")
            return
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_csv = os.path.join(os.path.dirname(__file__), f"mesures_{timestamp}.csv")
    fichier_bin = os.path.join(os.path.dirname(__file__), f"mesures_{timestamp}.bin")

    if plage == "low":
        ymin, ymax = 25, 120
    elif plage == "high" : 
        ymin, ymax = 35, 140
    else :
        ymin, ymax = 25, 140
        
    def new_files():
        horodatage = datetime.now().strftime("%Y-%m-%d_%H")   
        base = Path(__file__).with_suffix("")                
        csv_path = base.parent / f"mesures_{horodatage}.csv"
        bin_path = base.parent / f"mesures_{horodatage}.bin"
        return str(csv_path), str(bin_path), horodatage

    output_csv, fichier_bin, heure_courante = new_files()
    
    stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=audio_callback)
    stream.start()
    global BUFFER_MEMOIRE
    BUFFER_MEMOIRE = np.array([], dtype=np.float32)

    start_time = time.monotonic()
    i = 0

    try:
        while True:
            target_time = start_time + i
            now = time.monotonic()
            horloge = datetime.now().strftime("%Y-%m-%d_%H")
            if horloge != heure_courante:
                output_csv, fichier_bin, heure_courante = new_files()
                print(f" New time : generating {Path(output_csv).name}")

            sleep_time = target_time - now
            if sleep_time > 0:
                time.sleep(sleep_time)

            if len(BUFFER) >= SAMPLERATE:
                signal_mesure = np.array(BUFFER[:SAMPLERATE])
                BUFFER[:] = BUFFER[SAMPLERATE:]
                
                LAeq  = round(compute_LAeq_1s(signal_mesure, factor),1)
                spl_A = round(signal_to_db_pond(signal_mesure, factor, tau, type_pond_freq="A"), 1)
                spl_C = round(signal_to_db_pond(signal_mesure, factor, tau, type_pond_freq="C"), 1)
                spl_Z = round(signal_to_db_pond(signal_mesure, factor, tau, type_pond_freq="Z"), 1)
                
                # print(f"{datetime.now().strftime('%H:%M:%S')} | LAeq: {LAeq:.1f} dB(A) | A: {spl_A:.1f} dB(A) | C: {spl_C:.1f} dB(C) | Z: {spl_Z:.1f} dB")

                niveaux_par_bande = band_analysis(signal_mesure, 48000, factor)
                niveaux_arrondis = [round(val, 1) for val in niveaux_par_bande]
                line = [LAeq] + niveaux_arrondis + [spl_A, spl_C, spl_Z]

                if record:
                    save_csv(line, output_csv)
                    valeurs_entieres = np.round(np.array(line) * 10).astype(np.int16)
                    timestamp = np.asarray([time.time()], dtype=np.float64)
                    with open(fichier_bin, "ab") as fbin:
                        fbin.write(timestamp.tobytes())
                        fbin.write(valeurs_entieres.tobytes())

            else:
                print("Not enought datas")

            i += 1

    except KeyboardInterrupt:
        print("\n Measurement stopped.")
        stream.stop()
        stream.close()


if __name__ == "__main__":
    launch_measure(
        type_temp="Fast",        
        recalibrate=False,        
        plage="medium",          
        record=True         
    )