import sounddevice as sd
import numpy as np
from scipy.signal import bilinear, lfilter, butter, sosfilt
import time
import tkinter as tk
from tkinter import ttk
import os
from datetime import datetime
import csv
import matplotlib.pyplot as plt
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
        print("[Stream audio] Erreur : ", status)
    BUFFER.extend(indata[:, 0]) 

def enregistrer_audio(duree, sample_rate=48000, canal=1):
    audio = sd.rec(int(duree * sample_rate), samplerate=sample_rate, channels=canal)
    sd.wait()
    return audio.flatten()

def pond_tempor(signal, tau, sample_rate=48000):
    alpha = 1 / (tau * sample_rate)
    alpha = min(alpha, 1.0)
    puissance = signal**2
    sortie = np.zeros_like(puissance)
    sortie[0] = puissance[0]
    for i in range(1, len(puissance)):
        sortie[i] = (1 - alpha) * sortie[i - 1] + alpha * puissance[i]
    return np.sqrt(np.mean(sortie))

def calcul_rms(signal):
    return np.sqrt(np.mean(signal**2))

def calibrer_micro(rms_mesure, db_spl_reference=94):
    p_ref = 20e-6
    pression_reference = p_ref * 10**(db_spl_reference / 20)
    return pression_reference / rms_mesure

def filtre_pond(signal, type="A", sample_rate=48000):
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
        raise ValueError("Type de pondération non reconnu")

def signal_to_db_pond(signal, facteur_conversion, tau, type_pond_freq):
    global BUFFER_MEMOIRE
    BUFFER_MEMOIRE = np.concatenate((BUFFER_MEMOIRE, signal))
    if len(BUFFER_MEMOIRE) > DUREE_MEMOIRE * 48000:
        BUFFER_MEMOIRE = BUFFER_MEMOIRE[-(DUREE_MEMOIRE * 48000):]

    signal_filtre = filtre_pond(BUFFER_MEMOIRE, type=type_pond_freq, sample_rate=48000)
    p_rms_pond = pond_tempor_exponentielle(signal_filtre, tau=tau, sample_rate=48000) * facteur_conversion
    return 20 * np.log10(p_rms_pond / 20e-6)

def signal_to_db_spl(signal, facteur):
    p_rms = calcul_rms(signal) * facteur
    return 20 * np.log10(p_rms / 20e-6)

def bande_octave_filter(f_centre, fs, order=4):
    f_min = f_centre / (2 ** (1/6))
    f_max = f_centre * (2 ** (1/6))
    nyquist = fs / 2
    if f_max >= nyquist:
        f_max = nyquist - 1
    sos = butter(order, [f_min, f_max], btype='bandpass', fs=fs, output='sos')
    return sos

def analyse_par_bande(signal, fs, facteur, table_correction=CALIBRATION_CORRECTION_DB):
    niveaux_spl = []
    nyquist = fs / 2
    for f_centre in CENTRAL_FREQS:
        f_max = f_centre * (2 ** (1/6))
        if f_max < nyquist or f_centre == 20000:
            sos = bande_octave_filter(f_centre, fs)
            signal_filtre = sosfilt(sos, signal)
            spl = signal_to_db_spl(signal_filtre, facteur)
            correction = table_correction.get(f_centre, 0.0)
            niveaux_spl.append(spl - correction)
        else:
            niveaux_spl.append(np.nan)
    return niveaux_spl


def sauvegarder_csv_complet(niveaux_et_pond, fichier_csv):
    try:
        date_heure = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ligne = [date_heure] + niveaux_et_pond

        if not os.path.exists(fichier_csv):
            with open(fichier_csv, mode='w', newline='') as f:
                writer = csv.writer(f)
                header = ['DateHeure'] + [f"{int(f)}Hz" for f in CENTRAL_FREQS] + ['SPL_A', 'SPL_C', 'SPL_Z']
                writer.writerow(header)

        with open(fichier_csv, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(ligne)

    except Exception as e:
        print(f"Erreur lors de la sauvegarde : {e}")


def enregistrer_calibration(facteur, fichier="calibration.txt"):
    chemin_fichier = os.path.join(os.path.dirname(__file__), fichier)
    with open(chemin_fichier, "w") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{facteur}\n{now}")

def charger_calibration(fichier="calibration.txt"):
    chemin_fichier = os.path.join(os.path.dirname(__file__), fichier)
    if os.path.exists(chemin_fichier):
        with open(chemin_fichier, "r") as f:
            lignes = f.readlines()
            if len(lignes) >= 2:
                facteur = float(lignes[0].strip())
                date = lignes[1].strip()
                return facteur, date
    return None, None

def pond_tempor_exponentielle(signal, tau, sample_rate=48000):
    n = len(signal)
    if n == 0:
        return 0.0
    t = np.arange(n)[::-1] / sample_rate
    poids = np.exp(-t / tau)
    puissance = signal**2
    return np.sqrt(np.sum(poids * puissance) / np.sum(poids))

def lancer_mesure(type_temp="Fast", recalibrer=True, plage="normale", enregistrer=True):
    if type_temp == "Fast":
        tau = 0.125
    elif type_temp == "Slow":
        tau = 1.0
    elif type_temp == "Impulse": # Pas encore au point
        tau = 0.035

    if recalibrer:
        print("Place le calibrateur sur le micro (94 dB SPL à 1 kHz)")
        time.sleep(3)
        signal_calibration = enregistrer_audio(1)
        rms_calibration = calcul_rms(signal_calibration)
        facteur = calibrer_micro(rms_calibration)
        enregistrer_calibration(facteur)
        print(f"Facteur de conversion calibré : {facteur:.6f} Pa/unité")
    else:
        facteur, _ = charger_calibration()
        print("Ancienne calibration chargée")
        if facteur is None:
            print("Aucune calibration trouvée. Calibration nécessaire.")
            return
        
    def nouveaux_fichiers():
        horodatage = datetime.now().strftime("%Y-%m-%d_%H")   
        base = Path(__file__).with_suffix("")                
        csv_path = base.parent / f"mesures_{horodatage}.csv"
        bin_path = base.parent / f"mesures_{horodatage}.bin"
        return str(csv_path), str(bin_path), horodatage

    fichier_csv, fichier_bin, heure_courante = nouveaux_fichiers()

    if plage == "low":
        ymin, ymax = 25, 120
    elif plage == "high" : 
        ymin, ymax = 35, 140
    else :
        ymin, ymax = 25, 140

    stream = sd.InputStream(samplerate=SAMPLERATE, channels=1, callback=audio_callback)
    stream.start()
    
    root = tk.Tk()
    root.title(f"Niveaux SPL pondérés ({type_temp})")
    root.geometry("600x300")
    root.configure(bg="white")

    valeur_var = tk.StringVar()
    valeur_label = tk.Label(root, textvariable=valeur_var, font=("Helvetica", 24), bg="white", fg="black")
    valeur_label.pack(pady=20)

    stats_var = tk.StringVar()
    stats_label = tk.Label(root, textvariable=stats_var, font=("Helvetica", 16), bg="white", fg="gray")
    stats_label.pack(pady=5)

    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar([str(int(f)) for f in CENTRAL_FREQS], [0]*len(CENTRAL_FREQS), width=0.8)
    ax.set_ylim(ymin, ymax)
    ax.set_title("Analyse SPL par bande 1/3 d’octave")
    ax.set_xlabel("Fréquence centrale (Hz)")
    ax.set_ylabel("Niveau SPL (dB)")
    plt.xticks(rotation=45)
    plt.grid(True, which='both', axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()

    valeurs_spl_A = []  
    temps_spl_A = []   
    

    fig2, ax2 = plt.subplots(figsize=(12, 4))
    line_spl_A, = ax2.plot([], [], color='blue')
    ax2.set_ylim(ymin, ymax)
    ax2.set_xlim(0, 60)
    ax2.set_title("Historique SPL pondéré A (60 s)")
    ax2.set_xlabel("Temps (s)")
    ax2.set_ylabel("SPL A (dB)")
    plt.tight_layout()


    def mise_a_jour_affichage():
        global  after_id

        if not root.winfo_exists():
            return  

        start_time = time.time()
        
        nonlocal fichier_csv, fichier_bin, heure_courante
        horloge = datetime.now().strftime("%Y-%m-%d_%H")
        if horloge != heure_courante:
            fichier_csv, fichier_bin, heure_courante = nouveaux_fichiers()

        global BUFFER
        if len(BUFFER) >= SAMPLERATE:
            signal_mesure = np.array(BUFFER[:SAMPLERATE])
            BUFFER = BUFFER[SAMPLERATE:]
        else:
            print("[AVERTISSEMENT] Pas assez de données, attente...")
            after_id = root.after(100, mise_a_jour_affichage)
            return

        spl_A = signal_to_db_pond(signal_mesure, facteur, tau, type_pond_freq="A")
        spl_C = signal_to_db_pond(signal_mesure, facteur, tau, type_pond_freq="C")
        spl_Z = signal_to_db_pond(signal_mesure, facteur, tau, type_pond_freq="Z")

        valeurs_spl_A.append(spl_A)
        temps_spl_A.append(time.time())

        min_A = min(valeurs_spl_A)
        max_A = max(valeurs_spl_A)
        moy_A = sum(valeurs_spl_A) / len(valeurs_spl_A)
        stats_var.set(f"Min A: {min_A:.1f} dB | Moy: {moy_A:.1f} dB | Max A: {max_A:.1f} dB")

        while temps_spl_A and (temps_spl_A[-1] - temps_spl_A[0]) > 60:
            valeurs_spl_A.pop(0)
            temps_spl_A.pop(0)

        t0 = temps_spl_A[0] if temps_spl_A else time.time()
        t_norm = [t - t0 for t in temps_spl_A]

        line_spl_A.set_data(t_norm, valeurs_spl_A)
        ax2.set_xlim(0, 60)
        fig2.canvas.draw()
        fig2.canvas.flush_events()

        valeur_var.set(f"A: {spl_A:.2f} dB | C: {spl_C:.2f} dB | Z: {spl_Z:.2f} dB")

        niveaux_par_bande = analyse_par_bande(signal_mesure, 48000, facteur)

        for bar, val in zip(bars, niveaux_par_bande):
            bar.set_height(val if not np.isnan(val) else 0)
        fig.canvas.draw()
        fig.canvas.flush_events()

        ligne = niveaux_par_bande + [spl_A, spl_C, spl_Z]
        if enregistrer:
            sauvegarder_csv_complet(ligne, fichier_csv)
            valeurs_entieres = np.round(np.array(ligne) * 10).astype(np.int16)
            horodatage = np.asarray([time.time()], dtype=np.float64)
            with open(fichier_bin, "ab") as fbin:
                fbin.write(horodatage.tobytes())
                fbin.write(valeurs_entieres.tobytes())

        elapsed = time.time() - start_time
        attente = max(0, int(1000 - elapsed * 1000))  

        if root.winfo_exists():
            try:
                after_id = root.after(attente, mise_a_jour_affichage)
            except tk.TclError:
                print("[ERREUR] Problème lors du rappel Tkinter (fenêtre fermée ?)")


    def quitter_proprement():
        global  after_id
        if after_id is not None:
            try:
                root.after_cancel(after_id)
            except Exception as e:
                print("[WARNING] after_cancel échoué :", e)
        stream.stop()
        stream.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", quitter_proprement)


    root.after(1000, mise_a_jour_affichage)
    root.mainloop()

def config_initiale():
    config = tk.Tk()
    config.title("Configuration de départ")
    config.geometry("500x400")
    config.configure(bg="white")

    temp_var = tk.StringVar(value="Fast")
    recalib_var = tk.BooleanVar(value=True)
    plage_var = tk.StringVar(value="medium")
    log_var = tk.BooleanVar(value=True)

    facteur, date_calib = charger_calibration()

    tk.Label(config, text="Pondération temporelle :", bg="white").pack(pady=10)
    ttk.Combobox(config, textvariable=temp_var, values=["Fast", "Slow", "Impulse"], state="readonly").pack()

    tk.Label(config, text = "Plage de mesure :", bg="white").pack(pady=5)
    ttk.Combobox(config, textvariable=plage_var, values=["low", "medium", "high"], state="readonly").pack()

    tk.Checkbutton(config, text="Refaire la calibration", variable=recalib_var, bg="white").pack(pady=20)

    if date_calib:
        tk.Label(config, text=f"Dernière calibration : {date_calib}", bg="white", fg="gray").pack()
        tk.Label(config, text=f"Facteur sauvgardé : {facteur}", bg="white", fg="gray").pack()
    else :
        print("Pas d'ancienne calibration. Calibration necessaire")

    tk.Checkbutton(config, text="Enregistrer les mesures", variable=log_var, bg="white").pack(pady=10)
    
    def valider():
        config.destroy()
        lancer_mesure(type_temp=temp_var.get(), recalibrer=recalib_var.get(), plage=plage_var.get(), enregistrer=log_var.get())

    tk.Button(config, text="Valider", command=valider).pack(pady=20)
    config.mainloop()

config_initiale()

