"""CLI -> generated header -> compiled solver regression, using only the standard library.

The reference calculates physical RL/capacitor updates and independent scalar KCL
solves for two disconnected split-bus circuits. It never edits generated code or
reads the generated update equations. The fixed input conductance is part of the
component's LB-LMC interface, not a capacitor companion derived from dt/C.
"""
import argparse
from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path
import re
import subprocess
import sys
import unittest


PARSER = argparse.ArgumentParser(description=__doc__)
PARSER.add_argument("--codegen", required=True, type=Path)
PARSER.add_argument("--cxx", required=True, type=Path)
PARSER.add_argument("--work-dir", required=True, type=Path)
ARGS = PARSER.parse_args()


@dataclass
class Parameters:
    label: str
    dt: float
    cap: float
    inductance: float
    resistance: float
    source_voltage: float
    source_resistance: float
    legs: int = 2
    load_resistance: float = 1000.0


A = Parameters("bcA", 50e-9, 1e-3, 1e-4, 2e-4, 800.0, 0.25)
B = Parameters("bcB", 25e-9, 2e-3, 3e-4, 0.75, 500.0, 0.125)


def run(command, *, cwd, input_text=None, success=True):
    result = subprocess.run([str(arg) for arg in command], cwd=cwd,
                            input=input_text, capture_output=True, text=True)
    if success and result.returncode:
        raise AssertionError(f"Command failed ({result.returncode}): {command}\n"
                             f"{result.stdout}\n{result.stderr}")
    return result


def netlist(model, components):
    lines = [f"#name {model}"]
    first = 1
    for p in components:
        kind = f"BridgeConverter{p.legs}LegIdealSwitches"
        terminals = [first, 0, first + 1] + list(range(first + 2, first + 2 + p.legs))
        lines.extend([
            f"VoltageSource srcp_{p.label}({p.source_voltage:.17g}, {p.source_resistance:.17g}) {{{first},0}}",
            f"VoltageSource srcn_{p.label}({p.source_voltage:.17g}, {p.source_resistance:.17g}) {{0,{first+1}}}",
            f"{kind} {p.label}({p.dt:.17g}, {p.cap:.17g}, {p.inductance:.17g}, {p.resistance:.17g}) "
            + "{" + ",".join(map(str, terminals)) + "}",
        ])
        for leg in range(p.legs):
            lines.append(f"Resistor load{leg}_{p.label}({p.load_resistance:.17g}) {{{first+2+leg},0}}")
        first += 2 + p.legs
    return "\n".join(lines) + "\n"


def generate(model, components):
    return generate_text(model, netlist(model, components))


def generate_text(model, text):
    case = ARGS.work_dir / model
    case.mkdir(parents=True, exist_ok=True)
    source = case / "model.netlist"
    source.write_text(text, encoding="utf-8")
    result = run([ARGS.codegen, source], cwd=case)
    (case / "generation.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    header = (case / f"{model}.hpp").read_text(encoding="utf-8")
    return case, header


def compile_driver(case, model, header, components, node_count=None):
    """Bind by generated argument name so the test also checks the public signature."""
    match = re.search(r"void\s+" + model + r"_solver\s*\((.*?)\)\s*\{", header, re.S)
    if not match:
        raise AssertionError("Generated solver signature was not found")
    states = []
    bindings = {"x_out": "nodes"}
    for j, p in enumerate(components):
        suffixes = ["cp_voltage", "cn_voltage"] + [f"l{chr(97+k)}_current" for k in range(p.legs)]
        for suffix in suffixes:
            bindings[f"{suffix}_{p.label}"] = f"&outputs[{len(states)}]"
            states.append(f"{suffix}_{p.label}")
        bindings[f"sw_ctrl_{p.label}"] = f"gates{j}"
        bindings[f"sw_en_{p.label}"] = f"enable{j}"
    call_arguments = []
    for argument in match.group(1).split(","):
        arg_name = re.search(r"(\w+)\s*(?:\[\d+\])?\s*$", argument).group(1)
        if arg_name not in bindings:
            raise AssertionError(f"Unexpected solver argument: {argument}")
        call_arguments.append(bindings.pop(arg_name))
    if bindings:
        raise AssertionError(f"Expected solver arguments are missing: {bindings}")
    dimensions = sum(2+p.legs for p in components) if node_count is None else node_count
    declarations, inputs, assignments = [], [], []
    for j, p in enumerate(components):
        for k in range(p.legs):
            declarations.append(f"int ctrl{j}_{k};")
            inputs.append(f"ctrl{j}_{k}")
        declarations.extend([f"int enabled{j};", f"bool gates{j}[{p.legs}];", f"bool enable{j};"])
        inputs.append(f"enabled{j}")
        assignments.extend([f"gates{j}[{k}]=ctrl{j}_{k}!=0;" for k in range(p.legs)])
        assignments.append(f"enable{j}=enabled{j}!=0;")
    driver = f'''#include "{model}.hpp"
#include <iostream>
#include <iomanip>
int main() {{
    double nodes[{dimensions}]={{}}, outputs[{len(states)}]={{}};
    {" ".join(declarations)}
    std::cout << std::setprecision(17);
    while (std::cin >> {" >> ".join(inputs)}) {{
        {" ".join(assignments)}
        {model}_solver<0,double>({", ".join(call_arguments)});
        for (double value:nodes) std::cout << value << ' ';
        for (double value:outputs) std::cout << value << ' ';
        std::cout << '\\n';
    }}
}}
'''
    cpp = case / "driver.cpp"
    cpp.write_text(driver, encoding="utf-8")
    exe = case / ("driver.exe" if sys.platform == "win32" else "driver")
    if ARGS.cxx.stem.lower() == "cl":
        command = [ARGS.cxx, "/nologo", "/EHsc", "/std:c++14", "/O2", cpp, f"/Fe:{exe}"]
    else:
        command = [ARGS.cxx, "-std=c++14", "-O2"]
        if sys.platform == "win32":
            command.append("-static")
        command += [cpp, "-o", exe]
    compiled = run(command, cwd=case)
    (case / "compile.log").write_text(compiled.stdout + compiled.stderr, encoding="utf-8")
    return exe


def control_schedule(components, count=512):
    schedule = []
    for n in range(count):
        controls = []
        for j, p in enumerate(components):
            if n < 10:
                gates, enabled = [False] * p.legs, False
            elif n < 30:
                gates, enabled = [True] * p.legs, True
            elif n == 30:
                gates, enabled = [False] * p.legs, False
            elif n < 61:
                gates, enabled = [False] * p.legs, True
            elif n == 61:
                gates, enabled = [True] * p.legs, False
            elif n < 86:
                gates, enabled = [k % 2 == 0 for k in range(p.legs)], True
            elif n == 86:
                gates, enabled = [False] * p.legs, False
            elif n < 111:
                gates, enabled = [k % 2 == 1 for k in range(p.legs)], True
            elif n == 111:
                gates, enabled = [True] * p.legs, False
            else:
                gates = [(n // (7+4*k+j)) % 2 == 0 for k in range(p.legs)]
                enabled = (n+j*5) % 47 < 37
            controls.append((gates, enabled))
        schedule.append(controls)
    return schedule


class CircuitReference:
    """Zero-initialized capacitor/inductor states; scalar network KCL, no matrix library."""
    def __init__(self, parameters):
        self.p = parameters
        self.nodes = [0.0] * (2 + parameters.legs)
        self.cap_voltages = [0.0, 0.0]
        self.currents = [0.0] * parameters.legs
        self.coverage = Counter()

    def step(self, gates, enabled):
        p, previous_caps = self.p, self.cap_voltages
        rail_currents = [0.0, 0.0]
        currents = []
        if enabled:
            self.coverage["enabled_" + "".join("1" if gate else "0" for gate in gates)] += 1
        for k, previous_current in enumerate(self.currents):
            output_voltage = self.nodes[2+k]
            if enabled:
                connected_rail = 0 if gates[k] else 1
                applied_voltage = previous_caps[connected_rail]
            elif previous_current > 0:
                self.coverage["disabled_positive_current"] += 1
                connected_rail, applied_voltage = 1, previous_caps[1]
            elif previous_current < 0:
                self.coverage["disabled_negative_current"] += 1
                connected_rail, applied_voltage = 0, previous_caps[0]
            else:
                self.coverage["disabled_zero_current"] += 1
                if output_voltage > previous_caps[0]:
                    connected_rail, applied_voltage = 0, previous_caps[0]
                elif output_voltage < previous_caps[1]:
                    connected_rail, applied_voltage = 1, previous_caps[1]
                else:
                    connected_rail, applied_voltage = None, output_voltage
            if connected_rail is not None:
                rail_currents[connected_rail] += previous_current
            currents.append(previous_current + p.dt / p.inductance *
                            (applied_voltage-output_voltage-p.resistance*previous_current))
        # Gin links each internal capacitor voltage source to its external DC terminal.
        gin = 10000.0
        caps = [previous_caps[k] + p.dt / p.cap *
                (gin*(self.nodes[k]-previous_caps[k])-rail_currents[k]) for k in range(2)]
        # KCL at each rail: (v-Vsource)/Rsource + Gin*(v-Vinternal) = 0.
        nodes = [((1 if k == 0 else -1)*p.source_voltage / p.source_resistance + gin*caps[k]) /
                 (1/p.source_resistance+gin) for k in range(2)]
        # With no shunt conductance inside each leg, external KCL gives vout=Rload*iL.
        nodes += [p.load_resistance*current for current in currents]
        self.nodes, self.cap_voltages, self.currents = nodes, caps, currents
        return nodes, caps + currents


class BridgeConverterRegression(unittest.TestCase):
    def assert_close(self, got, expected, context):
        self.assertTrue(math.isfinite(got), f"Nonfinite {context}: {got}")
        self.assertTrue(math.isclose(got, expected, rel_tol=3e-11, abs_tol=2e-10),
                        f"{context}: generated={got:.17g}; reference={expected:.17g}")

    def check_dynamics(self, model, components):
        case, header = generate(model, components)
        exe = compile_driver(case, model, header, components)
        schedule = control_schedule(components)
        inputs = "\n".join(" ".join(str(int(value)) for gates, enabled in controls
                                    for value in [*gates, enabled]) for controls in schedule) + "\n"
        result = run([exe], cwd=case, input_text=inputs)
        (case / "solver_outputs.txt").write_text(result.stdout, encoding="utf-8")
        rows = [[float(x) for x in line.split()] for line in result.stdout.splitlines()]
        self.assertEqual(len(rows), len(schedule))
        references = [CircuitReference(p) for p in components]
        node_count = sum(2+p.legs for p in components)
        for n, (row, controls) in enumerate(zip(rows, schedule)):
            expected_nodes, expected_outputs = [], []
            for ref, (gates, enabled) in zip(references, controls):
                nodes, outputs = ref.step(gates, enabled)
                expected_nodes.extend(nodes)
                expected_outputs.extend(outputs)
            expected = expected_nodes + expected_outputs
            self.assertEqual(len(row), len(expected))
            for j, (got, target) in enumerate(zip(row, expected)):
                self.assert_close(got, target, f"{model}: step={n+1}, scalar={j}")
            # Check generated values against external output-port KCL separately.
            node_offset = output_offset = 0
            for p in components:
                for k in range(p.legs):
                    self.assert_close(row[node_offset+2+k],
                                      p.load_resistance*row[node_count+output_offset+2+k],
                                      f"{model}: Vout=Rload*iL, step={n+1}, {p.label}, leg={k}")
                node_offset += 2+p.legs
                output_offset += 2+p.legs
        for ref in references:
            for event in ("disabled_zero_current", "disabled_positive_current", "disabled_negative_current"):
                self.assertGreater(ref.coverage[event], 0, f"Missing coverage {ref.p.label}: {event}")
            if ref.p.legs == 2:
                for gates in ("00", "01", "10", "11"):
                    self.assertGreater(ref.coverage["enabled_"+gates], 0)
        return header

    def test_01_true_two_leg_structure_and_recurrence(self):
        header = self.check_dynamics("TwoLegReference", [A])
        for unwanted in ("il3", "sw3", "lc_current", "eout3", "source_id_C"):
            self.assertNotIn(unwanted, header)
        self.assertRegex(header, r"real\s+x_out\[4\]")
        self.assertRegex(header, r"inv_g\[4\]\[4\]")
        self.assertRegex(header, r"bool\s+sw_ctrl_bcA\[2\]")
        self.assertNotRegex(header, r"x\[(?:55|56)\]")
        self.assertRegex(header, r"b_components\[6\]")  # 2 sources + 4 bridge sources.

    def test_02_heterogeneous_parameters_in_one_generated_solver(self):
        header = self.check_dynamics("TwoLegHeterogeneous", [A, B])
        for p in (A, B):
            for name, expected in (("HOC", p.dt/p.cap), ("HOL", p.dt/p.inductance)):
                match = re.search(r"\b" + name + "_" + p.label + r"\s*=\s*([^;]+);", header)
                self.assertIsNotNone(match)
                self.assert_close(float(match.group(1)), expected, f"{name}_{p.label}")

    def test_03_existing_three_leg_interface_and_dynamics(self):
        p = Parameters("legacy", A.dt, A.cap, A.inductance, A.resistance,
                       A.source_voltage, A.source_resistance, legs=3)
        header = self.check_dynamics("ThreeLegCompatibility", [p])
        self.assertRegex(header, r"bool\s+sw_ctrl_legacy\[3\]")
        self.assertIn("lc_current_legacy", header)
        self.assertRegex(header, r"real\s+x_out\[5\]")

    def test_04_invalid_netlist_parameters_are_rejected(self):
        valid = netlist("InvalidTwoLeg", [A])
        pattern = r"(BridgeConverter2LegIdealSwitches bcA)\([^\n]+"
        invalid_parameters = [
            "0,1e-3,1e-4,0", "-5e-8,1e-3,1e-4,0",
            "5e-8,0,1e-4,0", "5e-8,-1e-3,1e-4,0",
            "5e-8,1e-3,0,0", "5e-8,1e-3,-1e-4,0",
            "5e-8,1e-3,1e-4,-0.01", "nan,1e-3,1e-4,0",
            "5e-8,inf,1e-4,0", "5e-8,1e-3,nan,0",
            "5e-8,1e-3,1e-4,inf", "5e-8,1e-3,1e-4", "5e-8,1e-3,1e-4,0,1",
        ]
        listings = [f"BridgeConverter2LegIdealSwitches bcA({params}) {{1,0,2,3,4}}"
                    for params in invalid_parameters]
        listings += ["BridgeConverter2LegIdealSwitches bcA(5e-8,1e-3,1e-4,0) {1,0,2,3}",
                     "BridgeConverter2LegIdealSwitches bcA(5e-8,1e-3,1e-4,0) {1,0,2,3,4,5}"]
        for i, listing in enumerate(listings):
            with self.subTest(listing=listing):
                case = ARGS.work_dir / f"invalid_{i}"
                case.mkdir(parents=True, exist_ok=True)
                path = case / "model.netlist"
                path.write_text(re.sub(pattern, lambda m: listing, valid), encoding="utf-8")
                result = run([ARGS.codegen, path], cwd=case, success=False)
                (case / "generation.log").write_text(result.stdout+result.stderr, encoding="utf-8")
                self.assertNotEqual(result.returncode, 0, f"Invalid listing was accepted: {listing}")
                self.assertTrue(result.stderr.strip(), "Rejection should explain the invalid netlist")

    def test_05_nonzero_neutral_translation_and_zero_current_blocking(self):
        # Every terminal, source and load is translated together. All branch
        # currents close within this floating subcircuit, so its only connection
        # to ground, the common-mode source, carries zero net current. KCL thus
        # fixes G at +/-100 V despite the source's finite series resistance.
        # Internal capacitor voltages and inductor currents must be unchanged.
        schedule = control_schedule([A])
        inputs = "\n".join(" ".join(str(int(value)) for value in [*gates, enabled])
                           for [(gates, enabled)] in schedule) + "\n"
        for shift in (100.0, -100.0):
            with self.subTest(neutral_voltage_V=shift):
                model = "TwoLegNeutral" + ("Positive" if shift > 0 else "Negative")
                text = f"""#name {model}
VoltageSource common({shift:.17g},0.125) {{1,0}}
VoltageSource srcp({A.source_voltage:.17g},{A.source_resistance:.17g}) {{2,1}}
VoltageSource srcn({A.source_voltage:.17g},{A.source_resistance:.17g}) {{1,3}}
BridgeConverter2LegIdealSwitches bcA({A.dt:.17g},{A.cap:.17g},{A.inductance:.17g},{A.resistance:.17g}) {{2,1,3,4,5}}
Resistor loadA({A.load_resistance:.17g}) {{4,1}}
Resistor loadB({A.load_resistance:.17g}) {{5,1}}
"""
                case, header = generate_text(model, text)
                exe = compile_driver(case, model, header, [A], node_count=5)
                result = run([exe], cwd=case, input_text=inputs)
                (case / "solver_outputs.txt").write_text(result.stdout, encoding="utf-8")
                rows = [[float(x) for x in line.split()] for line in result.stdout.splitlines()]
                self.assertEqual(len(rows), len(schedule))
                reference = CircuitReference(A)
                # Translating the full nodal solve adds common-mode subtraction
                # and matrix-inversion roundoff. Use dimensioned absolute limits
                # (2e-11 of voltage/current bases), not a relative tolerance that
                # becomes arbitrarily strict near zero. Grounded regressions
                # retain their original tolerances; blocking stays much tighter.
                voltage_tolerance = 2e-11 * (A.source_voltage + abs(shift))
                current_tolerance = 2e-11 * A.source_voltage / A.load_resistance
                for n, (row, [(gates, enabled)]) in enumerate(zip(rows, schedule)):
                    relative_nodes, outputs = reference.step(gates, enabled)
                    expected = [shift] + [value + shift for value in relative_nodes] + outputs
                    self.assertEqual(len(row), len(expected))
                    for k, (got, target) in enumerate(zip(row, expected)):
                        tolerance = voltage_tolerance if k < 7 else current_tolerance
                        self.assertTrue(math.isfinite(got))
                        self.assertLessEqual(abs(got-target), tolerance,
                                             f"{model}: step={n+1}, scalar={k}; "
                                             f"generated={got:.17g}; reference={target:.17g}; "
                                             f"absolute tolerance={tolerance:.3g}")
                    if n < 10:
                        self.assertFalse(enabled)
                        # During the initial disabled window the output-to-G
                        # voltage lies between both rails. Both diode paths
                        # must block and no spurious inductor current may start.
                        for k in (7, 8):  # Five nodes, then cp/cn/ia/ib outputs.
                            self.assertLess(abs(row[k]), 1e-14,
                                            f"{model}: spurious blocked current at step {n+1}")


if __name__ == "__main__":
    ARGS.codegen = ARGS.codegen.resolve()
    ARGS.cxx = ARGS.cxx.resolve()
    ARGS.work_dir = ARGS.work_dir.resolve()
    unittest.main(argv=[sys.argv[0]], verbosity=2)
