"""Generate unmodified two-leg HPPs and run a single-inverter voltage PI study."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--codegen", type=Path, default=REPO/"build/two_leg_codegen/SolverCodegen.exe")
parser.add_argument("--compiler", default=shutil.which("g++") or r"D:\Program Files\Mingw\bin\g++.exe")
parser.add_argument("--output", type=Path, default=REPO/"build/shipboard_two_leg_pi_20261024")
parser.add_argument("--probe-only", action="store_true")
parser.add_argument("--analyze-only", action="store_true")
parser.add_argument("--skip-probes", action="store_true")
args = parser.parse_args()
args.codegen, args.output = args.codegen.resolve(), args.output.resolve()
args.output.mkdir(parents=True, exist_ok=True)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def command(argv, log, cwd=None):
    with log.open("w", encoding="utf-8") as stream:
        result = subprocess.run([str(a) for a in argv], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"Exit {result.returncode}: {argv}. See {log}")

def prepare(label, dt):
    case = args.output/("dt_"+label)
    case.mkdir(exist_ok=True)
    text, count = re.subn(r"(?m)^#const DT\s+\S+", f"#const DT {dt:.17e}", (HERE/"shipboard_system.netlist").read_text())
    assert count == 1
    (case/"shipboard_system.netlist").write_text(text, encoding="utf-8")
    command([args.codegen, "shipboard_system.netlist"], case/"generation.log", cwd=case)
    header = case/"shipboard_zonal_system.hpp"
    source = header.read_text()
    assert "inv_g[54][54]" in source
    assert not re.search(r"\bil3_dcdc[12]\b", source)
    arguments = ["s.nodes"] + [f"&s.outputs[{i}]" for i in range(54)]
    for i in range(8):
        arguments += [f"dc[{i}]" if i < 2 else f"inv[{i-2}]", f"on[{i}]"]
    adapter = ('#pragma once\n#include "shipboard_zonal_system.hpp"\n'
               'struct Sample { double nodes[54]; double outputs[54]; };\n'
               'inline void advance(Sample& s, bool dc[2][2], bool inv[6][3], const bool on[8]) {\n'
               'shipboard_zonal_system_solver<0,double>('+',\n'.join(arguments)+');\n}\n')
    (case/"solver_adapter.hpp").write_text(adapter)
    (case/"config.hpp").write_text(f"#define DEMO_DT {dt:.17e}\n")
    source_files = [HERE/"pi_voltage_controller.hpp", HERE/"simulate_pi.cpp", HERE/"run_pi.py",
                    REPO/"src/codegen/components/BridgeConverter2LegIdealSwitches.cpp"]
    metadata = {"dt_s": dt, "node_count": 54, "header_postprocessing": False,
                "integration": "euler_forward", "header_sha256": sha(header), "codegen_sha256": sha(args.codegen),
                "netlist_sha256": sha(case/"shipboard_system.netlist"),
                "source_sha256": {str(p.relative_to(REPO)): sha(p) for p in source_files},
                "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO, text=True).strip(),
                "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()}
    (case/"generation.json").write_text(json.dumps(metadata, indent=2))
    command([args.compiler, "-std=c++14", "-O3", "-static", "-Wall", "-Wextra", "-Wno-unused-variable",
             "-I", case, HERE/"simulate_pi.cpp", "-o", case/"simulate_pi.exe"], case/"compile.log")
    return case

def run(case, mode, duration, event, name, ki=600, disturbance=False):
    prefix = case/name
    print(f"Running {case.name}/{name}: {mode}, {duration} s", flush=True)
    command([case/"simulate_pi.exe", mode, duration, event, prefix, .2, ki, .0002, int(disturbance)], case/(name+".log"))
    print((case/(name+".log")).read_text().strip(), flush=True)
    meta = json.loads(prefix.with_suffix(".json").read_text())
    assert meta["status"] == "completed"
    data = np.genfromtxt(case/(name+"_control.csv"), names=True, delimiter=",")
    assert np.isfinite(data.view(np.float64)).all()
    tail = data["time_s"] >= duration-.02
    return {"name": name, "ki_per_s": ki, "mode": mode, "duration_s": duration,
            "tail_filtered_V": float(data["filtered_amplitude_V"][tail].mean()),
            "tail_modulation": float(data["modulation"][tail].mean())}

if not args.analyze_only:
    fifty = prepare("50ns", 50e-9)
    if not args.skip_probes:
        probes = [run(fifty, "pi", .25, .133, f"probe_ki_{ki}", ki) for ki in (300, 600, 1000)]
        (args.output/"probe_summary.json").write_text(json.dumps(probes, indent=2))
    if args.probe_only:
        sys.exit(0)
    fine = prepare("25ns", 25e-9)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, fifty, mode, 10.2, 10.133, mode+"_long") for mode in ("pi", "open")]
        for future in futures:
            future.result()
    run(fine, "pi", .25, .133, "pi_short")
    if not (fifty/"probe_ki_600.csv").exists():
        run(fifty, "pi", .25, .133, "probe_ki_600")
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, fifty, mode, .25, .133, mode+"_disturbance", 600, True) for mode in ("pi", "open")]
        for future in futures:
            future.result()
    for case in (fifty, fine):
        meta = json.loads((case/"generation.json").read_text())
        assert sha(case/"shipboard_zonal_system.hpp") == meta["header_sha256"]
subprocess.run([sys.executable, str(HERE/"analyze_pi.py"), str(args.output)], check=True)
