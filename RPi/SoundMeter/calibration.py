import time
import numpy as np
import sounddevice as sd
from datetime import datetime
import os

def calcul_rms(signal):
    return np.sqrt(np.mean(signal**2))

def calibrer_micro(rms_mesure, db_spl_reference=94):
    p_ref = 20e-6
    pression_reference = p_ref * 10**(db_spl_reference / 20)
    return pression_reference / rms_mesure

def enregistrer_audio(duree, sample_rate=48000, canal=1):
    print(f"Enregistrement de {duree}s...")
    audio = sd.rec(int(duree * sample_rate), samplerate=sample_rate, channels=canal)
    sd.wait()
    return audio.flatten()

def enregistrer_calibration(facteur, fichier="calibration.txt"):
    chemin_fichier = os.path.join(os.path.dirname(__file__), fichier)
    with open(chemin_fichier, "w") as f:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"{facteur}\n{now}")

print("Place le calibrateur sur le micro (94 dB SPL à 1 kHz)")
time.sleep(3)

signal = enregistrer_audio(duree=1)
rms = calcul_rms(signal)
facteur = calibrer_micro(rms)

enregistrer_calibration(facteur)

print(f"Calibration terminée. Facteur de conversion : {facteur:.6f} Pa/unité")
