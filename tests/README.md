# Generated bridge solver regressions

`test_bridge_converter_2leg.py` requires Python 3.7+ and the same C++ compiler
used for SolverCodegen. It uses the Python standard library. Each test generates
a solver from a netlist, compiles that unmodified header, and runs the executable.

After configuring and building SolverCodegen, run:

```text
ctest --test-dir build -R bridge_converter_2leg_e2e --output-on-failure
```

The CMake option `SOLVERCODEGEN_BUILD_TESTS` enables this test independently of
Eigen's `BUILD_TESTING` option. Set `Python3_EXECUTABLE` during CMake configuration
if the interpreter is not found automatically. The generated test files and logs
are kept under the build tree's `tests/bridge_converter_2leg/` directory.

The script can also be run directly, passing absolute paths:

```text
python tests/test_bridge_converter_2leg.py --codegen /path/to/SolverCodegen --cxx /path/to/g++ --work-dir /path/to/test-output
```

The numerical reference is independent of generated update text. For each leg,
it integrates `L di/dt = u - Vout - Rseries*i` using the documented forward Euler
scheme and checks the separate output-port KCL `Vout = Rload*i`. Each internal
capacitor uses `C dVc/dt = Gin*(Vterminal-Vc) - Irail`, with the component's fixed
`Gin = 10000 S`. A scalar external rail KCL then determines the next terminal
voltage from a voltage source with finite series resistance. All nodes and
internal outputs are checked at every step. A 1 kOhm load makes the 50 ns RL
recurrence stable while retaining observable current and diode conduction.

Coverage includes all four enabled two-leg gate combinations, disabled zero
current, both signs of current in diode mode, and two independent converters with
different dt/C and dt/L in one generation process and compiled solver. Structure
checks ensure the two-leg model has four non-ground nodes, four bridge sources,
and no third-leg state, output, switch input, or dummy node. The old three-leg
interface is compiled and compared against the same circuit equations. Invalid
dt/C/L/R values and incorrect parameter/terminal counts must be rejected by the CLI.
