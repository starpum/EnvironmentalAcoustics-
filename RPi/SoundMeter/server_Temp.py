import os
import subprocess
import json
from flask import Flask, send_from_directory, abort, redirect, url_for
import struct

app = Flask(__name__)
DOSSIER = "/home/acoustic/Documents/Mesures"
SCRIPT_MESURE = "/home/acoustic/Documents/Mesures/mesure.py"
SCRIPT_TEMPERATURE = "/home/acoustic/Documents/Mesures/ReadTempHumid.py"
PID_FILE = "/home/acoustic/Documents/Mesures/mesure.pid"
SCRIPT_CALIB = "/home/acoustic/Documents/Mesures/calibration_seule.py"

@app.route("/")
def index():
    calib_path = os.path.join(DOSSIER, "calibration.txt")
    calibration_info = "<p><strong>No calibration file found.</strong></p>"
    if os.path.exists(calib_path):
        try:
            with open(calib_path, "r") as f:
                lines = f.readlines()
            if len(lines) >= 2:
                factor = lines[0].strip()
                date = lines[1].strip()
                calibration_info = f"""
                <h2>Current Calibration</h2>
                <p>Factor: {factor}<br>
                Date: {date}</p>
                <hr>
                """
        except Exception as e:
            calibration_info = f"<p>Error reading calibration file: {e}</p>"
        
    # Environment dynamic display
    env_line = """
        <p id="envline"><strong>Environment:</strong>
            <span id="temp">--</span> °C,
            <span id="humid">--</span> %
        </p>
        <script>
        async function updateEnv() {
            try {
                const resp = await fetch('/env', {cache: 'no-store'});
                const j = await resp.json();
                document.getElementById('temp').textContent = (j.temperature_c ?? 'N.A.');
                document.getElementById('humid').textContent = (j.humidity_pct ?? 'N.A.');
            } catch {
                document.getElementById('temp').textContent = 'N.A.';
                document.getElementById('humid').textContent = 'N.A.';
            }
        }
        updateEnv();
        setInterval(updateEnv, 3000);
        </script>
    """
    
    # Grad SPL data from the CSV / bin files
    try:
        fichiers = os.listdir(DOSSIER)
        fichiers_bin = [f for f in fichiers if f.endswith(".bin") and os.path.isfile(os.path.join(DOSSIER, f))]
        fichiers_csv = [f for f in fichiers if f.endswith(".csv") and os.path.isfile(os.path.join(DOSSIER, f))]
        fichiers = fichiers_bin + fichiers_csv

    except Exception as e:
        return f"<h2>Error reading directory : {e}</h2>", 500
    
    valeur_spl = "<p><strong>Last measurement unavailable.</strong></p>"
    if fichiers:
        dernier_bin = sorted(fichiers_bin)[-1]  
        try:
            chemin_bin = os.path.join(DOSSIER, dernier_bin)
            taille_entree = 1 + 31 + 3  
            taille_bytes = taille_entree * 2  
            with open(chemin_bin, "rb") as f:
                f.seek(0, os.SEEK_END)
                taille_fichier = f.tell()
                if taille_fichier >= taille_bytes:
                    f.seek(-taille_bytes, os.SEEK_END)
                    bloc = f.read(taille_bytes)
                    valeurs = struct.unpack(f"{taille_entree}h", bloc) 
                    spl_brut = valeurs[32]  
                    spl = round(spl_brut / 10, 1)  
                    valeur_spl = f"<p><strong>Current value :</strong> {spl} dB(A)</p>"

                else:
                    valeur_spl = "<p><strong>File too short to extract SPL.</strong></p>"
        except Exception as e:
            valeur_spl = f"<p>Error reading SPL from binary file {e}</p>"

    if os.path.exists(PID_FILE):
        status_html = '<p style="color: green; font-weight: bold;">🟢 Measurement running</p>'
    else:
        status_html = '<p style="color: red; font-weight: bold;">🔴 Measurement stopped</p>'

    buttons = f"""
        {env_line}
        {valeur_spl}
        {status_html}
        <h2>Remote Control</h2>
        <form action="/start" method="get">
            <button type="submit">Start Measurement</button>
        </form>
        <form action="/stop" method="get">
            <button type="submit">Stop Measurement</button>
        </form>
        <form action="/calibrate" method="get">
            <button type="submit">Recalibrate Microphone</button>
        </form>
        <hr>
        <h2>Available Files</h2>
    """


    if not fichiers:
        return calibration_info + buttons + "<p>Aucun fichier trouvé</p>"

    liens = [f'<a href="/fichiers/{f}">{f}</a>' for f in fichiers]
    return calibration_info + buttons + "<br>".join(liens) 

@app.route("/fichiers/<path:filename>")
def telecharger(filename):
    try:
        return send_from_directory(DOSSIER, filename)
    except Exception:
        abort(404)

@app.route("/start")
def start_script():
    if os.path.exists(PID_FILE):
        return redirect(url_for('index'))

    p = subprocess.Popen(["python3", SCRIPT_MESURE])
    with open(PID_FILE, "w") as f:
        f.write(str(p.pid))
    return redirect(url_for('index'))

@app.route("/stop")
def stop_script():
    if not os.path.exists(PID_FILE):
        return redirect(url_for('index'))

    with open(PID_FILE, "r") as f:
        pid = int(f.read())
    try:
        os.kill(pid, 9)
    except ProcessLookupError:
        pass
    os.remove(PID_FILE)
    return redirect(url_for('index'))

@app.route("/calibrate")
def recalibrate():
    subprocess.Popen(["python3", SCRIPT_CALIB])
    return redirect(url_for('index'))

@app.route("/env")
def env():
    try:
        with open("/tmp/env.json", "r") as f:
            return json.load(f)
    except Exception:
        return {"temperature_c": None, "humidity_pct": None}
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)



