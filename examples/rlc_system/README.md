# RLC circuit example

Based on the supplied `rlc.netlist`. The circuit has a 100 V source with 1 mOhm series resistance, a 1 mH inductor, and a parallel 10 Ohm resistor / 10 mF capacitor at the output. The capacitor is **10 mF**.

The fixed simulation starts from zero initial state and runs for 1 s with a 50 ns time step. It uses the unmodified, normally generated `RLC_Circuit.hpp`, without matrix patches or alternative solver versions.

## Build

Run from this directory:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

## Run and plot

Windows Visual Studio build:

```powershell
cd build/Release
.\simulate_rlc.exe
python .\plot.py
```

Linux/macOS or a Ninja/Make single-configuration build:

```sh
cd build
./simulate_rlc
python3 ./plot.py
```

Neither step requires arguments. C++ only writes CSV; Python runs separately and requires `numpy` and `matplotlib`.

## Output

Files are written to `results/` beside the executable:

- `rlc.csv`: source-terminal voltage, capacitor voltage, and inductor current, including the initial and final samples. The solver runs every 50 ns and saves every 0.1 ms.
- `rlc_voltage.png`: capacitor voltage over 1 s.
- `rlc_current.png`: inductor current over 1 s.
- `validation.json`: row count, duration, and finite-value checks.

The CSV records the solver outputs directly, including the generated solver's original current-state update ordering. The figures show simulation data only, without analytical or alternative-version comparisons.
