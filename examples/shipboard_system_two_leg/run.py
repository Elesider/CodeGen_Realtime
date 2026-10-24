"""Generate the two-leg solver directly from the CLI, compile, and run long cases."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--codegen", type=Path, default=REPO/"build/two_leg_codegen/SolverCodegen.exe")
parser.add_argument("--compiler", default=shutil.which("g++") or r"D:\Program Files\Mingw\bin\g++.exe")
parser.add_argument("--output", type=Path, default=REPO/"build/shipboard_two_leg_50ns_20261024")
parser.add_argument("--analyze-only", action="store_true")
parser.add_argument("--paper-page", type=Path, help="Optional image of PDF page 8 for a side-by-side figure")
args = parser.parse_args()
args.codegen, args.output = args.codegen.resolve(), args.output.resolve()
args.output.mkdir(parents=True, exist_ok=True)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def command(argv, logfile, cwd=None):
    with logfile.open("w", encoding="utf-8") as stream:
        p = subprocess.run([str(a) for a in argv], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {argv}; see {logfile}")

def adapter():
    names = []
    for q in ("dcdc1", "dcdc2"):
        names += [f"{name}_{q}" for name in ("cp_voltage", "cn_voltage", "la_current", "lb_current")]
    names += [f"l_current_cable_l{j:02d}" for j in range(1, 17)]
    for q in range(1, 7):
        names += [f"{name}_inv{q}" for name in ("cp_voltage", "cn_voltage", "la_current", "lb_current", "lc_current")]
    assert len(names) == 54
    fields = ["sample.nodes"] + [f"&sample.outputs[{j}]" for j in range(54)]
    for q in range(8):
        fields += [f"dcdcGates[{q}]" if q < 2 else f"inverterGates[{q-2}]", f"enabled[{q}]"]
    return ('#pragma once\n#include "shipboard_zonal_system.hpp"\n'
            'struct Sample { double nodes[54]; double outputs[54]; };\n'
            'inline void advance(Sample& sample, bool dcdcGates[2][2], bool inverterGates[6][3], const bool enabled[8])\n{\n'
            '    shipboard_zonal_system_solver<0, double>(\n        '+',\n        '.join(fields)+');\n}\n'), names

if not args.analyze_only:
    for label, dt in (("50ns", 50e-9), ("25ns", 25e-9)):
        case = args.output/("dt_"+label)
        case.mkdir(exist_ok=True)
        netlist, count = re.subn(r"(?m)^#const DT\s+\S+", f"#const DT {dt:.17e}", (HERE/"shipboard_system.netlist").read_text())
        assert count == 1
        (case/"shipboard_system.netlist").write_text(netlist, encoding="utf-8")
        command([args.codegen, "shipboard_system.netlist"], case/"generation.log", cwd=case)
        header = case/"shipboard_zonal_system.hpp"
        source = header.read_text()
        assert "inv_g[54][54]" in source
        for q in ("dcdc1", "dcdc2"):
            assert f"bool sw_ctrl_{q}[2]" in source
            assert not re.search(rf"\b(?:il3|sw3|lc_current|eout3)(?:_past)?_{q}\b", source)
        # x has 55 slots because slot zero is ground; only 54 non-ground solutions exist.
        assert not re.search(r"(?m)^x\[(55|56)\]\s*=", source)
        code, names = adapter()
        (case/"solver_adapter.hpp").write_text(code)
        (case/"output_names.json").write_text(json.dumps(names, indent=2))
        (case/"config.hpp").write_text(f"#define DEMO_DT {dt:.17e}\n")
        metadata = {"dt_s": dt, "node_count": 54, "component_outputs": 54,
                    "hpp_postprocessing": False, "integration": "euler_forward",
                    "codegen_sha256": sha(args.codegen), "header_sha256": sha(header),
                    "netlist_sha256": sha(case/"shipboard_system.netlist"),
                    "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip(),
                    "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()}
        metadata["source_sha256"] = {str(p.relative_to(REPO)): sha(p) for p in [
            REPO/"src/codegen/components/BridgeConverter2LegIdealSwitches.cpp",
            REPO/"include/codegen/components/BridgeConverter2LegIdealSwitches.hpp",
            REPO/"src/codegen/netlist/producers/BridgeConverter2LegIdealSwitchesProducer.cpp",
            REPO/"src/codegen/netlist/ComponentFactory_registerBuiltinComponentProducers.cpp",
            HERE/"simulate.cpp"]}
        (case/"generation.json").write_text(json.dumps(metadata, indent=2))
        command([args.compiler, "-std=c++14", "-O3", "-static", "-Wall", "-Wextra", "-Wno-unused-variable",
                 "-I", case, HERE/"simulate.cpp", "-o", case/"simulate.exe"], case/"compile.log")
        runs = [("busstep", ".6")]
        if label == "50ns":
            runs.append(("acstep", "10.2"))
        for scenario, duration in runs:
            print(f"Running {label}: {scenario}, {duration} s", flush=True)
            command([case/"simulate.exe", scenario, duration, case/scenario], case/(scenario+".log"))
            print((case/(scenario+".log")).read_text().strip(), flush=True)
        assert sha(header) == metadata["header_sha256"], "Generated header must remain unmodified."
analysis_command = [sys.executable, str(HERE/"analyze.py"), str(args.output)]
if args.paper_page:
    analysis_command += ["--paper-page", str(args.paper_page)]
subprocess.run(analysis_command, check=True)
