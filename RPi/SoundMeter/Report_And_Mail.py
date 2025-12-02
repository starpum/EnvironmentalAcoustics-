import os
import glob
import ssl
import smtplib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
from typing import List, Dict, Any

# ----------------------------
# Configuration

DOSSIER = "/home/acoustic/Documents/Mesures"
DOSS_CSV = os.path.join(DOSSIER, "measurements")
PLOT_DIR = os.path.join(DOSSIER, "reports")
os.makedirs(PLOT_DIR, exist_ok=True)

PROJECT_CONFIG = "/home/acoustic/Documents/Mesures/PROJECT_CONFIG.json"  # JSON config path
ROLL_SEC = 300  # L90,5min window size (seconds)

plt.style.use("seaborn-v0_8")

# ----------------------------
# Load config from JSON

def load_config(path=PROJECT_CONFIG):

    """
    Load configuration from JSON file.
    Expected JSON file structure:
    {
      "smtp": {
        "user": "your_email@gmail.com",
        "pass": "your_app_password"
      },
      "recipients": {
        "to": ["addr1@example.com", "addr2@example.com"],
        "cc": ["cc@example.com"],
        "bcc": ["bcc@example.com"]
      },
      "periods": [
        {"name":"day","start":7,"end":19,"limit":55.0},
        {"name":"evening","start":19,"end":23,"limit":50.0},
        {"name":"night","start":23,"end":7,"limit":45.0}
      ]
    }"""

    with open(path,"r") as fh:
        cfg = json.load(fh)
    smtp = cfg["smtp"]
    rec = cfg["recipients"]
    periods = cfg.get("periods", [])
    return smtp["user"], smtp["pass"], rec["to"], rec.get("cc",[]), rec.get("bcc",[]), periods

# ----------------------------
# Files & Loading

def discover_day_csvs(base_dir: str, target_date: datetime.date) -> List[str]:
    ymd = target_date.strftime("%Y-%m-%d")
    return sorted(glob.glob(os.path.join(base_dir, f"mesures_{ymd}_*.csv")))

def load_day_from_csv(csv_files: List[str]):
    """
    Load and concatenate one day's CSVs. 
    Returns:
      times      : pandas.DatetimeIndex
      laeq_1s    : numpy array (float)
      freqs_hz   : numpy array (float sorted)
      S_db       : 2D numpy array [n_times, n_bins]
    """
    frames = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)

            # Clean column names
            df.columns = df.columns.str.strip().str.replace('"','')

            # Normalize LAeq column
            if "LAeq,1s" in df.columns:
                df = df.rename(columns={"LAeq,1s": "LAeq"})
            elif "LAeq" not in df.columns:
                continue

            # Parse datetime
            if "Date&Time" in df.columns:
                df["Date&Time"] = pd.to_datetime(df["Date&Time"], errors="coerce")
                df = df.dropna(subset=["Date&Time"])
            else:
                continue

            frames.append(df)
        except Exception:
            continue

    if not frames:
        return pd.DatetimeIndex([]), np.array([]), np.array([]), np.empty((0, 0))

    # Merge all frames
    day_df = pd.concat(frames, ignore_index=True).sort_values("Date&Time")
    day_df = day_df.drop_duplicates(subset=["Date&Time"]).set_index("Date&Time").sort_index()

    # Resample to 1-second grid
    day_df = day_df.resample("1s").mean(numeric_only=True)

    # Extract LAeq
    laeq_1s = day_df["LAeq"].astype(float).to_numpy()

    # Extract frequency bands
    band_cols = [c for c in day_df.columns if c.endswith("Hz")]
    freqs = np.array([float(c.replace("Hz", "")) for c in band_cols], dtype=float)
    sort_idx = np.argsort(freqs)
    band_cols_sorted = [band_cols[i] for i in sort_idx]
    freqs_hz = freqs[sort_idx]
    S_db = day_df[band_cols_sorted].astype(float).to_numpy()

    # Build output DataFrame with required columns
    out_df = day_df[["LAeq"] + band_cols_sorted].copy()
    for col in ["SPL_A", "SPL_C", "SPL_Z"]:
        if col in day_df.columns:
            out_df[col] = day_df[col]

    out_df = out_df.reset_index()

    # Save to PLOT_DIR
    tag = day_df.index[0].date().strftime("%Y%m%d") if len(day_df) else "empty"
    out_path = os.path.join(PLOT_DIR, f"dayfile_{tag}.csv")
    out_df.to_csv(out_path, index=False)

    return day_df.index, laeq_1s, freqs_hz, S_db

# ----------------------------
# Computations for reporting

def energy_average_LAeq(values_db: np.ndarray) -> float:
    """LAeq = 10*log10(mean(10^(L/10)))"""
    return float(10.0 * np.log10(np.mean(10.0 ** (values_db / 10.0)))) if len(values_db) else np.nan

def compute_L90_day(laeq_1s: np.ndarray) -> float:
    """L90,day = 10th percentile of LAeq,1s (level exceeded 90% of time)."""
    return float(np.percentile(laeq_1s, 10)) if len(laeq_1s) else np.nan

def compute_L90_rolling(times: pd.DatetimeIndex, laeq_1s: np.ndarray, roll_sec: int = ROLL_SEC) -> pd.Series:
    """Rolling L90 over roll_sec seconds (centered)."""
    if len(laeq_1s) == 0:
        return pd.Series([], index=times)
    s = pd.Series(laeq_1s, index=times)
    return s.rolling(f'{roll_sec}s', center=True).quantile(0.10)

# ----------------------------
# Dynamic limit line (one moving line)

def classify_period(h: int, periods: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    For overnight periods (end < start): active when h >= start OR h < end.
    """
    for p in periods:
        start, end = p['start'], p['end']
        if start < end:
            if start <= h < end:
                return p
        else:
            if h >= start or h < end:
                return p
    return periods[0]  # fallback

def dynamic_limit_series(times: pd.DatetimeIndex, periods: List[Dict[str, Any]]) -> np.ndarray:
    return np.array([classify_period(t.hour, periods)['limit'] for t in times], dtype=float)

# ----------------------------
# Exceedances

def compute_exceedances_dynamic(times: pd.DatetimeIndex, laeq_1s: np.ndarray, limit_series: np.ndarray) -> Dict[str, Any]:
    mask = laeq_1s > limit_series
    n_exceed = int(mask.sum())
    pct_time = (100.0 * n_exceed / len(laeq_1s)) if len(laeq_1s) else 0.0
    if n_exceed == 0:
        return dict(n_exceed=0, pct_time=0.0, first=None, last=None)
    idx = np.where(mask)[0]
    return dict(
        n_exceed=n_exceed, pct_time=pct_time,
        first=times[idx[0]].strftime("%H:%M:%S"),
        last=times[idx[-1]].strftime("%H:%M:%S"),
    )

# ----------------------------
# Plots

def plot_levels(times, laeq_1s, l90_5min, l90_day, limit_series, out_path):
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(times, laeq_1s, color="#1c7ec5", lw=1.1, label="LAeq,1s")
    l90_5 = l90_5min.dropna()
    if len(l90_5) > 0:
        ax.plot(l90_5.index, l90_5.values, color="#2ca02c", lw=1.4, label="L90,5min")
    if not np.isnan(l90_day):
        ax.hlines(l90_day, xmin=times[0], xmax=times[-1], colors="#ff7f0e",
                  linestyles="--", label=f"L90,day = {l90_day:.1f} dB(A)")
    ax.plot(times, limit_series, color="#d62728", linestyle=":", lw=1.5, label="Legal limit")
    ax.set_title("Daily sound levels — LAeq,1s + L90,5min + L90,day + dynamic limit")
    ax.set_ylabel("Level [dB(A)]")
    ax.set_xlabel("Time")
    ax.legend(loc="upper left", ncol=2)
    ax.grid(True, alpha=0.25)
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_spectrogram(times, freqs_hz, S_db, out_path):

    if S_db.size == 0 or len(times) == 0:
        return False

    # Convert times to matplotlib numbers
    t_nums = mdates.date2num(times)
    dt = (t_nums[1] - t_nums[0]) if len(t_nums) > 1 else 1/(24*3600)
    t_edges = np.concatenate([t_nums - dt/2, [t_nums[-1] + dt/2]])

    # Frequency edges
    df = np.diff(freqs_hz).mean() if len(freqs_hz) > 1 else 1.0
    f_edges = np.concatenate([freqs_hz - df/2, [freqs_hz[-1] + df/2]])

    # Plot
    fig, ax = plt.subplots(figsize=(12, 5))
    mesh = ax.pcolormesh(t_edges, f_edges, S_db.T, shading="auto", cmap="plasma")

    # Colorbar
    cbar = fig.colorbar(mesh, ax=ax, pad=0.02)
    cbar.set_label("Sound level [dB]", fontsize=11)

    # Labels & formatting
    ax.set_title("Daily Spectrogram", fontsize=14, weight="bold")
    ax.set_ylabel("Frequency [Hz]", fontsize=11)
    ax.set_xlabel("Time", fontsize=11)
    ax.set_yscale("log")
    ax.set_ylim((max(20.0, f_edges[0]), f_edges[-1]))
    ax.xaxis.set_major_formatter(DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    ax.grid(True, which="both", linestyle="--", alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)
    return True

# ----------------------------------------------
# Email (inline images via attachments with CID)

def send_email(user, passwd, subject, metrics, inline_images, to_list, cc_list, bcc_list):

    root = MIMEMultipart('mixed')
    root['From'] = user
    root['To'] = ", ".join(to_list)
    if cc_list: root['Cc'] = ", ".join(cc_list)
    root['Subject'] = subject

    # Plain text fallback
    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText("Daily noise report. Please view the HTML version for graphs.", 'plain'))

    # HTML body with nicer formatting
    exceed_html = (
        f"<p style='color:#d62728;'>Exceeded limit {metrics['exceed_info']['n_exceed']} s "
        f"({metrics['exceed_info']['pct_time']:.1f}% of day). "
        f"First: {metrics['exceed_info']['first']}, Last: {metrics['exceed_info']['last']}.</p>"
        if metrics['exceed_info']['n_exceed'] > 0 else
        "<p style='color:#2ca02c;'>No exceedance above dynamic limit detected.</p>"
    )

    html_body = f"""
    <html>
    <body style="font-family:Arial, sans-serif; color:#333;">
      <h2 style="color:#1c7ec5;">Daily Measurement Report</h2>
      <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;">
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>LAeq,day</td><td>{metrics['laeq_day']:.1f} dB(A)</td></tr>
        <tr><td>L90,day</td><td>{metrics['l90_day']:.1f} dB(A)</td></tr>
      </table>
      {exceed_html}
      <h3>Day Levels</h3>
      <img src="cid:levels" style="max-width:100%; border:1px solid #ccc;"/>
      <h3>Spectrogram</h3>
      <img src="cid:spectrogram" style="max-width:100%; border:1px solid #ccc;"/>
    </body>
    </html>
    """

    # Related container with HTML + images
    rel = MIMEMultipart('related')
    rel.attach(MIMEText(html_body, 'html'))

    for item in inline_images:
        with open(item["path"], "rb") as f:
            data = f.read()
        img = MIMEImage(data, _subtype="png")
        img.add_header('Content-ID', f"<{item['name']}>")
        img.add_header('Content-Disposition', 'inline')
        rel.attach(img)

    alt.attach(rel)
    root.attach(alt)

    # Send
    all_rcpts = to_list + cc_list + bcc_list
    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, passwd)
        server.sendmail(user, all_rcpts, root.as_string())

# ----------------------------
# Orchestration

def generate_and_send_daily_report(config_path=PROJECT_CONFIG, target_date=None):
    # Load everything from JSON
    user, passwd, to_list, cc_list, bcc_list, periods = load_config(PROJECT_CONFIG)

    # Default to yesterday
    if target_date is None:
        today = datetime.now().date()
        target_date = today - timedelta(days=1)

    # Find CSVs
    csv_files = discover_day_csvs(DOSS_CSV, target_date)
    if not csv_files:
        raise FileNotFoundError(f"No CSVs found for {target_date.isoformat()} under {DOSS_CSV}")

    # Load data
    times, laeq_1s, freqs_hz, S_db = load_day_from_csv(csv_files)
    laeq_daily = energy_average_LAeq(laeq_1s)
    l90_day    = compute_L90_day(laeq_1s)
    l90_5min   = compute_L90_rolling(times, laeq_1s, ROLL_SEC)
    limit_line = dynamic_limit_series(times, periods)
    ex_all     = compute_exceedances_dynamic(times, laeq_1s, limit_line)

    #print(f"Daily LAeq : {laeq_daily:.1f} dB(A), L90,day: {l90_day:.1f} dB(A)")

    # Plots
    tag = target_date.strftime("%Y%m%d")
    levels_png  = os.path.join(PLOT_DIR, f"levels_dynamic_{tag}.png")
    spectro_png = os.path.join(PLOT_DIR, f"spectrogram_{tag}.png")
    plot_levels(times, laeq_1s, l90_5min, l90_day, limit_line, levels_png)
    spectro_ok = plot_spectrogram(times, freqs_hz, S_db, spectro_png)

    # Inline images
    inline_images = [{"name": "levels", "path": levels_png, "mime": "image/png"}]
    if spectro_ok and os.path.exists(spectro_png):
        inline_images.append({"name": "spectrogram", "path": spectro_png, "mime": "image/png"})

    # Metrics dict for email
    metrics = {
        "laeq_day": laeq_daily,
        "l90_day": l90_day,
        "exceed_info": ex_all
    }

    # Subject line
    subject = f"Daily noise report — {target_date.isoformat()}"

    # Send email
    send_email(user, passwd, subject, metrics, inline_images, to_list, cc_list, bcc_list)


def main():
    generate_and_send_daily_report(target_date=None)

if __name__ == "__main__":
    main()
