"""No arguments: draw the RLC voltage and current directly from the simulation CSV."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def results_folder(script, required):
    here = Path(script).resolve().parent
    candidates = [here / "results", here / "build/Release/results", here / "build/results",
                  here / "build/Debug/results"]
    for parent in (here.parent, here.parent.parent):
        for base in (parent / "build" / here.name, parent / "build/examples" / here.name):
            candidates += [base / "Release/results", base / "results", base / "Debug/results"]
    for p in candidates:
        if all((p / name).is_file() for name in required):
            print(f"Reading: {p}")
            return p
    raise SystemExit("CSV not found. Run the C++ executable first, then plot.py beside it.")


def read_csv(path):
    data = np.genfromtxt(path, names=True, delimiter=",")
    if data.size < 2 or not all(np.isfinite(data[n]).all() for n in data.dtype.names):
        raise ValueError(f"Invalid or nonfinite CSV: {path}")
    if not np.all(np.diff(data["time_s"]) > 0):
        raise ValueError(f"Non-increasing timestamps: {path}")
    return data


def style():
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": .22, "lines.linewidth": 1.2})


def write_validation(root, values):
    (root / "validation.json").write_text(json.dumps(values, indent=2), encoding="utf-8")


def main():
    root = results_folder(__file__, ["rlc.csv"])
    d = read_csv(root / "rlc.csv")
    t = d["time_s"]
    if len(t) != 10001 or abs(t[-1]-1.0) > 1e-12:
        raise ValueError("RLC simulation did not complete the fixed 1 s run")
    style()
    for key, ylabel, title, filename in (
        ("vc_V", "Capacitor voltage / V", "RLC - capacitor voltage", "rlc_voltage.png"),
        ("il_A", "Inductor current / A", "RLC - inductor current", "rlc_current.png")):
        fig, ax = plt.subplots(figsize=(12, 5.1))
        fig.subplots_adjust(left=.09, right=.98, bottom=.17, top=.77)
        fig.suptitle(title, x=.09, ha="left", fontsize=16, fontweight="bold")
        ax.plot(t, d[key], color="#1765cb")
        ax.set(xlim=(0, 1), xlabel="Time / s", ylabel=ylabel)
        fig.text(.09, .84,
                 "100 V | Rv = 1 mOhm | L = 1 mH | R = 10 Ohm | C = 10 mF | dt = 50 ns",
                 fontsize=10, color="#526173")
        fig.savefig(root/filename, dpi=180)
        plt.close(fig)
        print(root/filename)
    write_validation(root, {"dt_s": 50e-9, "duration_s": 1, "steps": 20000000,
                            "rows": len(t), "all_values_finite": True,
                            "solver_header": "RLC_Circuit.hpp", "header_postprocessing": False})


if __name__ == "__main__":
    main()
