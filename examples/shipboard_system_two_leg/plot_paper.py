"""Draw exactly two event-window figures from the fixed simulator experiments."""
from pathlib import Path
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker


def load(root, name, duration, event):
    meta = json.loads((root / f"{name}.json").read_text(encoding="utf-8"))
    if (meta["status"] != "completed" or meta["completed_steps"] != round(duration / 50e-9)
            or abs(meta["event_time_s"] - event) > 1e-12):
        raise ValueError(f"{name}: incomplete or wrong simulation case")
    data = np.genfromtxt(root / f"{name}.csv", delimiter=",", names=True)
    if not all(np.isfinite(data[n]).all() for n in data.dtype.names):
        raise ValueError(f"{name}: CSV contains nonfinite values")
    if not np.all(np.diff(data["time_s"]) > 0):
        raise ValueError(f"{name}: timestamps must increase")
    if abs(data["time_s"][-1] - duration) > 1e-12:
        raise ValueError(f"{name}: wrong final time")
    return data


def select(data, start, end):
    return (data["time_s"] >= start - 1e-12) & (data["time_s"] < end - 1e-12)


def canvas(title, start, end, event, event_label):
    fig, ax = plt.subplots(figsize=(12, 5.9))
    fig.subplots_adjust(left=.09, right=.98, bottom=.25, top=.82)
    fig.suptitle(title, x=.09, y=.97, ha="left", fontsize=17, fontweight="bold")
    ax.set_title("Time step: 50 ns | PWM: 100 kHz | Fundamental: 60 Hz (inferred from the paper plot)",
                 loc="left", fontsize=10, color="#526173", pad=14)
    ax.set(xlim=(start, end), ylim=(-7000, 7000), xlabel="Time / s", ylabel="Instantaneous voltage / V")
    ax.yaxis.set_major_locator(ticker.MultipleLocator(2000))
    ax.xaxis.set_major_locator(ticker.MultipleLocator(.02))
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
    ax.grid(True, color="#d9e0e7", linewidth=.7)
    ax.set_axisbelow(True)
    ax.axvline(event, color="#596575", ls="--", lw=1, zorder=1)
    ax.text(event+.001, -6650, event_label, fontsize=9, color="#384759",
            bbox=dict(facecolor="white", edgecolor="none", alpha=.9, pad=3))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return fig, ax


def main(root):
    plt.rcParams.update({"axes.unicode_minus": False, "font.size": 11, "lines.linewidth": 1.1})
    bus = load(root, "fig16", .6, .5)
    ac = load(root, "fig19", 10.2, 10.133)
    ctrl = np.genfromtxt(root / "fig19_control.csv", names=True, delimiter=",")
    if not all(np.isfinite(ctrl[n]).all() for n in ctrl.dtype.names):
        raise ValueError("PI control CSV contains nonfinite values")
    if not np.any((ctrl["time_s"] < 10.133) & (ctrl["reference_V"] == 6000)):
        raise ValueError("Missing 6000 V pre-event reference")
    if not np.all(ctrl["reference_V"][ctrl["time_s"] >= 10.133-1e-12] == 3000):
        raise ValueError("Wrong 3000 V post-event reference")

    fig, ax = canvas("Fig. 16 scenario - DC bus voltage reduction", .47, .58, .5,
                     "0.500 s: DC bus target +/-6 kV to +/-2 kV")
    w = select(bus, .47, .580001)
    for key, color, label in (("bus_pos_V", "#b51f23", "Positive DC bus"),
                              ("bus_neg_V", "#a76316", "Negative DC bus"),
                              ("va_V", "#1765cb", "Phase A output"),
                              ("vb_V", "#228347", "Phase B output")):
        ax.plot(bus["time_s"][w], bus[key][w], color=color, label=label)
    ax.legend(loc="upper right", ncol=4, fontsize=10)
    before, after = select(bus, .47, .49), select(bus, .55, .58)
    bp, bn = float(bus["bus_pos_V"][after].mean()), float(bus["bus_neg_V"][after].mean())
    fig.text(.09, .11, f"Mean bus voltages over 0.55-0.58 s: positive {bp:.1f} V, negative {bn:.1f} V.", fontsize=11)
    fig.text(.09, .045, "Open-loop bus control; simulated from zero initial state to 0.6 s. Event window shown without smoothing.", fontsize=9, color="#526173")
    fig.savefig(root / "fig16_dc_bus.png", dpi=180)
    plt.close(fig)

    fig, ax = canvas("Fig. 19 scenario - Three-phase inverter PI voltage reduction", 10.09, 10.2, 10.133,
                     "10.133 s: amplitude reference 6 kV to 3 kV")
    w = select(ac, 10.09, 10.200001)
    for key, color, label in (("va_V", "#b51f23", "Phase A"),
                              ("vb_V", "#228347", "Phase B"),
                              ("vc_V", "#1765cb", "Phase C")):
        ax.plot(ac["time_s"][w], ac[key][w], color=color, label=label)
    ax.legend(loc="upper right", ncol=3, fontsize=10)
    settled = select(ctrl, 10.17, 10.2)
    amplitude = float(ctrl["filtered_amplitude_V"][settled].mean())
    mod = float(ctrl["modulation"][settled].mean())
    fig.text(.09, .11, f"Means over 10.17-10.20 s: filtered amplitude {amplitude:.1f} V; modulation index {mod:.4f}.", fontsize=11)
    fig.text(.09, .045, "PI gains are not published: reconstructed controller uses Kp=0.2, Ki=600 /s; not the original paper controller.", fontsize=9, color="#526173")
    fig.savefig(root / "fig19_pi_voltage.png", dpi=180)
    plt.close(fig)

    # Validate all displayed samples fit the axes; never hide a large transient by clipping.
    for data, start, end, keys in ((bus, .47, .58, ("bus_pos_V", "bus_neg_V", "va_V", "vb_V")),
                                  (ac, 10.09, 10.2, ("va_V", "vb_V", "vc_V"))):
        mask = select(data, start, end+1e-6)
        if any(np.max(np.abs(data[key][mask])) >= 7000 for key in keys):
            raise ValueError("Displayed voltage exceeds plot limits; expand axes before delivery")
    report = {"dt_s": 50e-9, "fig16_steps": 12000000, "fig19_steps": 204000000,
              "all_saved_values_finite": True, "no_plot_clipping": True,
              "bus_before_positive_mean_V": float(bus["bus_pos_V"][before].mean()),
              "bus_after_positive_mean_V": bp, "bus_after_negative_mean_V": bn,
              "pi_after_filtered_amplitude_mean_V": amplitude, "pi_after_modulation_mean": mod,
              "pi_settings_from_paper": False,
              "csv_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.csv")}}
    (root / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name in ("fig16_dc_bus.png", "fig19_pi_voltage.png"):
        print(root / name)


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    candidates = [here / "results", here / "build/Release/results",
                  here / "build/results", here / "build/Debug/results"]
    found = [p for p in candidates if (p / "fig16.json").exists() and (p / "fig19.json").exists()]
    if not found:
        raise SystemExit("CSV files not found. Build and run simulate_pi without arguments first.")
    # The script copied beside the executable always uses that executable's results.
    # Running the source script also supports the standard CMake output locations.
    root = found[0]
    print(f"Reading simulation results: {root}")
    main(root)
