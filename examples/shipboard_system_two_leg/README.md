# Two-leg shipboard power-system example

This example simulates a dual-bus shipboard network with two two-leg DC/DC converters and six three-phase inverters. It uses the supplied, unmodified generated solver header.

The workflow has two independent steps, both without command-line arguments:

1. Run the C++ executable to generate CSV files.
2. Run the Python script to generate two English-language figures.

The C++ program does not launch Python. It uses standard C++17 without platform-specific APIs.

## Requirements

- CMake 3.24 or later and a C++17 compiler.
- Python with `numpy` and `matplotlib` for plotting.

The pre-generated solver is included, so building this example does not require Eigen or running SolverCodegen first.

## Build

Run from this directory:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
```

CMake copies `plot_paper.py` beside the executable.

## Run and plot

For a Windows Visual Studio build:

```powershell
cd build/Release
.\simulate_pi.exe
python .\plot_paper.py
```

For Linux/macOS or a Ninja/Make single-configuration build:

```sh
cd build
./simulate_pi
python3 ./plot_paper.py
```

Wait for both simulation cases to finish before plotting. The executable runs both cases automatically. No duration, PI gain, output prefix, or other runtime parameter is required.

If you build all examples using `cmake -S examples -B build/examples` from the repository root, the corresponding Visual Studio executable directory is `build/examples/shipboard_system_two_leg/Release`.

## Fixed experiments

| Case | Event | Simulation duration | Figure window |
|---|---|---|---|
| Fig.16 | At 0.5 s, reduce the DC bus from approximately +/-6 kV to +/-2 kV using open-loop DC/DC control | 0.6 s | 0.47-0.58 s |
| Fig.19 | At approximately 10.133 s, reduce inverter 1's voltage-amplitude reference from 6 kV to 3 kV using PI control | 10.2 s | 10.09-10.20 s |

Both cases use a 50 ns circuit step and 100 kHz PWM. Each starts from zero initial state using a separate solver template instance, so history states are not carried between experiments. No extra disturbance is applied. In the PI case, the other five inverters retain their original modulation.

Fixed case definitions and parameter provenance are in [paper_cases.hpp](paper_cases.hpp).

## Output files

All outputs are written to `results/` beside the executable. Running again overwrites this example's corresponding output files.

| File | Contents |
|---|---|
| `fig16.csv` | DC bus and inverter phase waveforms for the bus-reduction case |
| `fig19.csv` | Circuit waveforms for the PI voltage-reduction case |
| `fig19_control.csv` | Reference amplitude, measured feedback, modulation, and controller state |
| `fig16.json`, `fig19.json` | Completion status, step count, and simulation settings |
| `fig16_dc_bus.png` | Positive/negative DC bus and two inverter phase voltages |
| `fig19_pi_voltage.png` | Three-phase output voltages during PI-controlled amplitude reduction |
| `validation.json` | Saved-data checks, window statistics, and CSV hashes |

`fig16_control.csv` contains only a header because the Fig.16 case does not use the PI controller.

The figures show event windows rather than compressing the complete simulation onto one axis. They retain the original time axis and ripple without smoothing or phase adjustment. The plot script checks completion, increasing timestamps, finite values, and displayed voltage limits before reporting success.

## PI controller

The controller updates every 10 us. It averages the preceding PWM period's three phase voltages, computes the Clarke-vector magnitude, and applies a first-order feedback filter with a 0.2 ms time constant.

The normalized error is `(reference - filtered_amplitude) / 6000`. The reconstructed controller uses `Kp = 0.2`, `Ki = 600 /s`, and a modulation range of `[0, 1]`, with conditional integration for anti-windup. This feedback is a voltage-amplitude estimate, not RMS.

The implementation is in [pi_voltage_controller.hpp](pi_voltage_controller.hpp). The simulation driver is [simulate_pi.cpp](simulate_pi.cpp), and the independent plotting entry is [plot_paper.py](plot_paper.py).

## Relationship to the paper

Reference: *Software and Synthesis Development Libraries for Power Electronic System Real-Time Simulation*, 2019 ESTS, pp.375-376, Fig.16 and Fig.19. DOI: `10.1109/ESTS.2019.8847940`.

The paper explicitly specifies a 50 ns step, 100 kHz switching, and a DC bus reduction to one third of its original voltage. Event times and AC amplitudes are approximated from the plots. The 60 Hz fundamental is inferred from the plotted period rather than explicitly stated.

The paper does not publish the PI gains, feedback/filter implementation, controller sampling interval, startup procedure, carrier shape, or initial phase. The settings above are a documented reconstruction, not the paper's original controller parameters.

The supplied netlist has no additional DC source at far-end nodes 35/36. CPU double-precision simulation also differs from the paper's 72-bit fixed-point FPGA/HIL platform. These experiments therefore reproduce the available operating scenarios, not the original hardware or every plotted sample.
