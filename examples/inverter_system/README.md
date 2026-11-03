# Three-phase inverter example

Adapted from the supplied inverter example. The netlist and generated `ExampleInverterSystem.hpp` are retained unchanged.

The fixed settings preserve the original driver: +/-1000 V DC supply, 50 Hz sinusoidal references, a 100 kHz symmetric triangular carrier, modulation index 1, complementary gates without dead time, a 50 ns time step, and a 1 s duration. Each phase has a 1 mH inductor, 1 uF capacitor, and 10 Ohm load.

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
.\simulate_inverter.exe
python .\plot.py
```

Linux/macOS or a Ninja/Make single-configuration build:

```sh
cd build
./simulate_inverter
python3 ./plot.py
```

Neither step requires arguments. The C++ driver uses standard C++17 and only writes CSV. The independent Python script needs `numpy` and `matplotlib`.

## Output

Files are written to `results/` beside the executable:

- `inverter.csv`: sparse records across the full run, with samples every 1 us over 0.94-1.00 s.
- `spwm.csv`: actual references, carrier, and A-phase gate commands over 22.00-22.05 ms, sampled every 50 ns.
- `inverter_voltage.png`: steady three-phase voltages over three 50 Hz cycles.
- `inverter_spwm.png`: reference/carrier comparison and gate signals over five PWM periods.
- `validation.json`: amplitude, phase-sequence, and gate-logic checks.

Circuit CSV timestamps mark the end of an integration step. SPWM timestamps mark the start of the step when the gate command is applied.

## Driver corrections

The generated interface returns exactly five node voltages, `x_out[5]`. The driver reads and writes only those five values, avoiding the original six-element overrun.

`std::acos(-1.0)` replaces `std::numbers::pi` to support C++17. Samples are streamed directly to CSV. The carrier uses integer step indices, giving exactly 200 steps per PWM period.
