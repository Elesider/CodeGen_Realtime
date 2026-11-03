"""No arguments: plot three-phase output and the actual SPWM gate trace."""
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
    root = results_folder(__file__, ["inverter.csv", "spwm.csv"])
    d, pwm = read_csv(root/"inverter.csv"), read_csv(root/"spwm.csv")
    t = d["time_s"]
    if abs(t[-1]-1.0) > 1e-12:
        raise ValueError("Inverter run must reach 1 s")
    if not np.array_equal(pwm["gate_a_upper"]+pwm["gate_a_lower"], np.ones(len(pwm))):
        raise ValueError("Upper/lower gates are not complementary")
    if not np.array_equal(pwm["gate_a_upper"], pwm["reference_a"] >= pwm["carrier"]):
        raise ValueError("Gate trace does not match the SPWM comparator")
    window = (t >= .94-1e-12) & (t <= 1.0+1e-12)
    tw = t[window]
    model = np.column_stack([np.sin(2*np.pi*50*tw), np.cos(2*np.pi*50*tw), np.ones(len(tw))])
    coeff = [np.linalg.lstsq(model, d[f"node{k}_voltage"][window], rcond=None)[0] for k in (3, 4, 5)]
    amplitudes = [float(np.hypot(c[0], c[1])) for c in coeff]
    phases = [np.arctan2(c[1], c[0]) for c in coeff]
    phase_ab = float(np.degrees(np.angle(np.exp(1j*(phases[1]-phases[0])))))
    phase_ac = float(np.degrees(np.angle(np.exp(1j*(phases[2]-phases[0])))))
    # Independent low-frequency LC/load transfer function, not the generated recurrence.
    w = 2*np.pi*50
    expected_peak = 1000/abs(1-.001*1e-6*w*w+1j*w*.001/10)
    if any(abs(a-expected_peak)/expected_peak > .05 for a in amplitudes):
        raise ValueError(f"Unexpected steady voltage amplitudes: {amplitudes}")
    if abs(phase_ab+120) > 5 or abs(phase_ac-120) > 5:
        raise ValueError(f"Wrong three-phase sequence: {phase_ab}, {phase_ac}")
    style()
    colors = ("#b51f23", "#228347", "#1765cb")
    fig, ax = plt.subplots(figsize=(12, 5.1))
    fig.subplots_adjust(left=.09, right=.98, bottom=.22, top=.77)
    fig.suptitle("Three-phase inverter - filtered output voltages", x=.09, ha="left", fontsize=16, fontweight="bold")
    for key, color, label in zip(("node3_voltage", "node4_voltage", "node5_voltage"), colors, ("Phase A", "Phase B", "Phase C")):
        ax.plot(tw, d[key][window], color=color, label=label)
    ax.set(xlim=(.94, 1), xlabel="Time / s", ylabel="Phase voltage / V")
    ax.legend(loc="upper right", ncol=3)
    fig.text(.09, .84, "50 Hz reference | 100 kHz triangular carrier | m = 1 | dt = 50 ns | simulated from 0 to 1 s", fontsize=10, color="#526173")
    fig.text(.09, .065, "50 Hz fitted phase peaks: "+", ".join(f"{v:.1f} V" for v in amplitudes)+". Phase separation: 120 degrees.", fontsize=10)
    fig.savefig(root/"inverter_voltage.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(2, 1, figsize=(12, 6.3), sharex=True)
    fig.subplots_adjust(left=.09, right=.98, bottom=.18, top=.80, hspace=.20)
    fig.suptitle("SPWM - reference / carrier comparison and gate signals", x=.09, ha="left", fontsize=16, fontweight="bold")
    tx = pwm["time_s"]*1000
    ax[0].plot(tx, pwm["carrier"], color="#939da7", label="100 kHz carrier", lw=1)
    for phase, color in zip("abc", colors):
        ax[0].plot(tx, pwm[f"reference_{phase}"], color=color, label=f"{phase.upper()} reference")
    ax[0].set_ylabel("Normalized value")
    ax[0].legend(ncol=4, fontsize=9, loc="upper right")
    ax[1].step(tx, pwm["gate_a_upper"], where="post", color=colors[0], label="A upper")
    ax[1].step(tx, pwm["gate_a_lower"], where="post", color=colors[2], ls="--", label="A lower")
    ax[1].set(xlabel="Time / ms", ylabel="Gate", ylim=(-.15, 1.3), yticks=[0, 1], xlim=(22, 22.05))
    ax[1].legend(loc="upper right", ncol=2, fontsize=9)
    fig.text(.09, .86, "Five PWM periods; trace saved at every 50 ns step, using the actual C++ gate commands.", fontsize=10, color="#526173")
    fig.text(.09, .055, "Upper = (reference >= carrier); lower = NOT upper. Complementary switching without dead time.", fontsize=10)
    fig.savefig(root/"inverter_spwm.png", dpi=180)
    plt.close(fig)
    write_validation(root, {"dt_s": 50e-9, "duration_s": 1, "steps": 20000000,
                            "node_output_count": 5, "all_values_finite": True,
                            "fundamental_hz": 50, "carrier_hz": 100000, "modulation": 1,
                            "phase_peak_V": amplitudes, "ideal_LC_phase_peak_V": expected_peak,
                            "phase_AB_degrees": phase_ab, "phase_AC_degrees": phase_ac,
                            "gates_match_comparator": True, "complementary_gates": True})
    print(root/"inverter_voltage.png")
    print(root/"inverter_spwm.png")


if __name__ == "__main__":
    main()
