import os
import subprocess
from flask import Flask, send_from_directory, abort, redirect, url_for
import struct
import json 
import time 

app = Flask(__name__)
DOSSIER = "/home/acoustic/Documents/Mesures"
MEASURES = "/home/acoustic/Documents/Mesures/measurements"
SCRIPT_MESURE = "/home/acoustic/Documents/Mesures/measure.py"
SCRIPT_TEMPERATURE = "/home/acoustic/Documents/Mesures/ReadTempHumid.py"
PID_FILE = "/home/acoustic/Documents/Mesures/mesure.pid"
SCRIPT_CALIB = "/home/acoustic/Documents/Mesures/calibration_seule.py"

@app.route("/")
def index():
    # Grab calibration file and display its properties 
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

    # Temperature and humidity (updates every 5 minutes)
    env_line = """
        <p id="envline"><strong>Environment:</strong>
            <span id="temp">--</span> °C,
            <span id="humid">--</span> %
        </p>
        <script>
        async function updateEnv() {
            try {
                const resp = await fetch('/envi', {cache: 'no-store'});
                const j = await resp.json();
                document.getElementById('temp').textContent = (j.temperature_c ?? 'N.A.');
                document.getElementById('humid').textContent = (j.humidity_pct ?? 'N.A.');
            } catch {
                document.getElementById('temp').textContent = 'N.A.';
                document.getElementById('humid').textContent = 'N.A.';
            }
        }
        updateEnv();
        setInterval(updateEnv, 300000);
        </script>
    """

    #Display LAeq results
    try:
        files = os.listdir(MEASURES)
        bin_files = [f for f in files if f.endswith(".bin") and os.path.isfile(os.path.join(MEASURES, f))]
        csv_files = [f for f in files if f.endswith(".csv") and os.path.isfile(os.path.join(MEASURES, f))]
        files = bin_files + csv_files


    except Exception as e:
        return f"<h2>Error reading folder : {e}</h2>", 500
    
    spl_value = "<p><strong>Last measurement unavailable.</strong></p>"
    if bin_files:
        try:
            spl_value = "<p><strong>Current LAeq,1s :</strong> <span id='spl'>--</span> dB(A)</p>"
        except Exception as e:
            spl_value = f"<p>Error reading LAeq from binary : {e}</p>"

    spl_script = """
    <script>
    async function updateSPL() {
        try {
            const resp = await fetch('/spl', {cache: 'no-store'});
            const j = await resp.json();
            if (j.spl !== null) {
                document.getElementById('spl').textContent = j.spl.toFixed(1);
            } else {
                document.getElementById('spl').textContent = 'N.A.';
            }
        } catch {
            document.getElementById('spl').textContent = 'N.A.';
        }
    }
    updateSPL();
    setInterval(updateSPL, 3000);
    </script>
    """

    if os.path.exists(PID_FILE):
        status_html = '<p style="color: green; font-weight: bold;">🟢 Measurement running</p>'
    else:
        status_html = '<p style="color: red; font-weight: bold;">🔴 Measurement stopped</p>'

    buttons = f"""
        {env_line}
        {spl_value}
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


    if not files:
        return calibration_info + buttons + "<p>No files found...</p>" + spl_script

    file_links = [f'<a href="/files/{f}">{f}</a>' for f in files]
    return calibration_info + buttons + "<br>".join(file_links) + spl_script

@app.route("/files/<path:filename>")
def download(filename):
    try:
        return send_from_directory(MEASURES, filename)
    except Exception:
        abort(404)

@app.route("/envi")
def envi():
    try:
        enve_file = "/tmp/envi.json"
        # Refresh only if stale (>5s old)
        if not os.path.exists(enve_file) or \
            (time.time() - os.path.getmtime(enve_file)) > 5:
            subprocess.Popen(["python3", SCRIPT_TEMPERATURE])
        with open(enve_file, "r") as f:
            return json.load(f)
    except Exception:
        return {"temperature_c": None, "humidity_pct": None}

@app.route("/spl")
def spl():
    try:
        files = os.listdir(MEASURES)
        bin_files = [f for f in files if f.endswith(".bin")]
        if not bin_files:
            return {"spl": None, "message": "Last measurement unavailable."}

        latest_bin = max(bin_files, key=lambda f: os.path.getmtime(os.path.join(MEASURES, f)))
        bin_path = os.path.join(MEASURES, latest_bin)

        input_size = 1 + 31 + 3
        bytes_size = input_size * 2

        os.sync()
        with open(bin_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            if file_size < bytes_size:
                return {"spl": None, "message": "File too short to extract LAeq."}

            f.seek(-bytes_size, os.SEEK_END)
            bloc = f.read(bytes_size)
            values = struct.unpack(f"{input_size}h", bloc)

        LAeq_brut = values[0]
        LAeq = round(LAeq_brut / 10, 1)
        return {"spl": LAeq, "message": None}

    except Exception as e:
        return {"spl": None, "message": f"Error: {e}"}
      
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)