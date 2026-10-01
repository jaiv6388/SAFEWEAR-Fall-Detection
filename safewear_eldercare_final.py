import json
import math
import time
from pathlib import Path
import paho.mqtt.client as mqtt

# ============================================================
# SAFEWEAR — 15 SECOND GRADED MOVEMENT → FALL DEMO
# Selects REAL F01 SisFall samples by acceleration magnitude.
# Matches Node-RED conversion: magnitude = sqrt(x²+y²+z²) / 256
# ============================================================

BROKER = "localhost"
PORT = 1883
TOPIC = "safewear/sensor"

FILE = Path.home() / "Downloads" / "SisFall_dataset" / "SA01" / "F01_SA01_R01.txt"

HZ = 12
DELAY = 1 / HZ

# 15 seconds total
# 4s Stable + 4s Movement + 4s High Movement + 3s Fall
PHASES = [
    ("STABLE",        0.70, 1.25, 48),
    ("MOVEMENT",      1.25, 2.00, 48),
    ("HIGH MOVEMENT", 2.00, 2.95, 48),
    ("FALL EVENT",    3.00, 99.0, 36),
]


def parse(line):
    parts = [x.strip() for x in line.strip().rstrip(";").replace(";", ",").split(",") if x.strip()]
    if len(parts) < 9:
        return None
    try:
        return [int(float(x)) for x in parts[:9]]
    except ValueError:
        return None


def magnitude_g(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2) / 256.0


def load_data():
    if not FILE.exists():
        raise FileNotFoundError(f"File not found: {FILE}")

    rows = []
    with FILE.open("r", encoding="utf-8", errors="ignore") as f:
        for source_sample, line in enumerate(f, start=1):
            v = parse(line)
            if v:
                rows.append((source_sample, v, magnitude_g(v)))
    return rows


def pick_phase(rows, low, high, count):
    candidates = [r for r in rows if low <= r[2] < high]
    if not candidates:
        raise RuntimeError(f"No F01 samples found in {low:.2f}g–{high:.2f}g")

    # Spread selected real samples across all matching candidates rather than
    # repeating only one reading.
    if len(candidates) >= count:
        if count == 1:
            return [candidates[len(candidates)//2]]
        idx = [round(i * (len(candidates)-1) / (count-1)) for i in range(count)]
        return [candidates[i] for i in idx]

    out = []
    while len(out) < count:
        out.extend(candidates)
    return out[:count]


def main():
    try:
        rows = load_data()
        selected = []
        for name, low, high, count in PHASES:
            phase_rows = pick_phase(rows, low, high, count)
            selected.append((name, phase_rows))
            mags = [r[2] for r in phase_rows]
            print(f"{name:13s}: {min(mags):.2f}g → {max(mags):.2f}g ({len(phase_rows)} samples)")
    except Exception as e:
        print("ERROR:", e)
        return

    client = mqtt.Client()
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print("\nSAFEWEAR 15-second graded demo")
    print("STABLE → MOVEMENT → HIGH MOVEMENT → FALL")
    print("Dashboard/Node-RED still calculate the final fall state.")
    print("Ctrl+C to stop.\n")

    sample_no = 0

    try:
        while True:
            for phase_name, phase_rows in selected:
                print(f">>> {phase_name}")

                for source_sample, v, mag in phase_rows:
                    sample_no += 1
                    ax, ay, az, gx, gy, gz, a2x, a2y, a2z = v

                    payload = {
                        "sample": sample_no,
                        "source_sample": source_sample,
                        "demo_phase": phase_name,
                        "acc1_x": ax,
                        "acc1_y": ay,
                        "acc1_z": az,
                        "gyro_x": gx,
                        "gyro_y": gy,
                        "gyro_z": gz,
                        "acc2_x": a2x,
                        "acc2_y": a2y,
                        "acc2_z": a2z
                    }

                    client.publish(TOPIC, json.dumps(payload))
                    time.sleep(DELAY)

            print("--- 15 sec cycle complete; restarting ---\n")

    except KeyboardInterrupt:
        print("\nDemo stopped.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("MQTT disconnected.")


if __name__ == "__main__":
    main()
