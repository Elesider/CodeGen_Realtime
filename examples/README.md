# Standalone simulation examples

Each example follows the same workflow: run the C++ executable without arguments to generate CSV files, then run its Python script without arguments to generate figures. C++ does not launch Python. The examples use standard C++17 and do not depend on a shared helper directory.

| Directory | Executable target | Plot script | Fixed scenario |
|---|---|---|---|
| [rlc_system](rlc_system/README.md) | simulate_rlc | plot.py | RLC circuit, 50 ns time step, 1 s duration |
| [inverter_system](inverter_system/README.md) | simulate_inverter | plot.py | Three-phase inverter, 50 Hz reference, 100 kHz PWM, 1 s duration |
| [shipboard_system_two_leg](shipboard_system_two_leg/README.md) | simulate_pi | plot_paper.py | Paper Fig.16 / Fig.19 scenarios, 50 ns, 0.6 s / 10.2 s duration |

`shipboard_system` retains the original netlist and topology as references. It does not provide a standalone simulation driver.

## Build all examples

Run from the repository root:

```sh
cmake -S examples -B build/examples -DCMAKE_BUILD_TYPE=Release
cmake --build build/examples --config Release
```

The examples use the supplied solver headers; building them does not require Eigen or running the code generator first.

For Visual Studio builds, executables and copied plot scripts are under:

- `build/examples/rlc_system/Release/`
- `build/examples/inverter_system/Release/`
- `build/examples/shipboard_system_two_leg/Release/`

Ninja and Make single-configuration builds omit the `Release/` directory. Each example also has its own CMake project; see its README for standalone build commands.

## Run and plot

For example, in Windows PowerShell:

```powershell
cd build/examples/rlc_system/Release
.\simulate_rlc.exe
python .\plot.py
```

On Linux/macOS, use `./simulate_rlc` and `python3 ./plot.py` from the corresponding executable directory. Python needs `numpy` and `matplotlib`; neither is a C++ build dependency.

CSV files, figures, and validation records are written to `results/` beside each executable. CMake copies the plot script beside the executable. Running again overwrites the same example's output files. All figure text and documentation are in English.

## Verification

The examples have been built with MSVC 19.50 and GCC 15.2 on Windows x64. Both RLC and inverter examples completed 20,000,000 steps and generated two figures. The shipboard example completed its 10.2 s PI scenario. These checks do not constitute a Linux/macOS runtime test.

The RLC example uses the unmodified generated header and plots simulation data only. The inverter checks its three-phase sequence and actual SPWM gate commands. MinGW builds statically link their C++ runtime libraries.
