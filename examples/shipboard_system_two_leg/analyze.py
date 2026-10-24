"""Validate long runs and compare their qualitative features with paper figures."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--paper-page", type=Path, help="Image of the complete 2019 paper's PDF page 8")
args = parser.parse_args()
ROOT = args.output.resolve()
for candidate in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")):
    if candidate.exists():
        font_manager.fontManager.addfont(str(candidate))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(candidate)).get_name()
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 10, "axes.grid": True,
                     "grid.alpha": .25, "lines.linewidth": 1.0, "savefig.dpi": 200})

def load(label):
    path = ROOT/label
    data = np.genfromtxt(path.with_suffix(".csv"), delimiter=",", names=True)
    meta = json.loads(path.with_suffix(".json").read_text())
    generation = json.loads((path.parent/"generation.json").read_text())
    assert meta["status"] == "completed", meta
    assert meta["completed_steps"] == round(meta["requested_duration_s"]/meta["dt_s"])
    assert np.all(np.isfinite(data.view(np.float64)))
    assert np.all(np.diff(data["time_s"]) > 0)
    assert abs(data["time_s"][-1]-meta["requested_duration_s"]) < 1e-12
    assert generation["hpp_postprocessing"] is False
    header = path.parent/"shipboard_zonal_system.hpp"
    assert hashlib.sha256(header.read_bytes()).hexdigest() == generation["header_sha256"]
    return data, {**meta, "saved_rows": len(data), "all_saved_values_finite": True,
                  "generated_header_unchanged": True}

bus, bm = load("dt_50ns/busstep")
fine, fm = load("dt_25ns/busstep")
ac, am = load("dt_50ns/acstep")

def mask(data, start, end):
    return (data["time_s"] >= start-1e-12) & (data["time_s"] < end-1e-12)

def magnitude(data):
    return np.sqrt((2/3)*(data["va_V"]**2+data["vb_V"]**2+data["vc_V"]**2))

def stats(data, start, end):
    chosen = mask(data, start, end)
    t = data["time_s"][chosen]
    design = np.column_stack([np.sin(2*np.pi*60*t), np.cos(2*np.pi*60*t), np.ones(len(t))])
    fitted = np.linalg.lstsq(design, data["va_V"][chosen], rcond=None)[0]
    return {"start_s_inclusive": start, "end_s_exclusive": end, "saved_points": int(chosen.sum()),
            "bus_positive_mean_V": float(data["bus_pos_V"][chosen].mean()),
            "bus_negative_mean_V": float(data["bus_neg_V"][chosen].mean()),
            "phase_vector_magnitude_mean_V": float(magnitude(data)[chosen].mean()),
            "phase_A_60Hz_fitted_peak_V": float(np.hypot(fitted[0], fitted[1])),
            "total_load_power_mean_W": float(data["total_load_power_W"][chosen].mean())}

result = {"runs": {"50ns_busstep": bm, "25ns_busstep": fm, "50ns_acstep": am},
          "windows": {"bus_before": stats(bus, .47, .49), "bus_after": stats(bus, .55, .58),
                      "ac_before": stats(ac, 10.10, 10.13), "ac_after": stats(ac, 10.17, 10.20)}}
bk = np.rint(bus["time_s"]/25e-9).astype(np.int64)
fk = np.rint(fine["time_s"]/25e-9).astype(np.int64)
keys, bi, fi = np.intersect1d(bk, fk, return_indices=True)
assert np.max(np.abs(bus["time_s"][bi]-fine["time_s"][fi])) < 1e-12
uniform = (keys % 80 == 0) & (bus["time_s"][bi] >= .47-1e-12) & (bus["time_s"][bi] <= .58+1e-12)
comparison = {"shared_saved_points": len(keys), "uniform_2us_event_points": int(uniform.sum()), "fields": {}}
for col in ("bus_pos_V", "bus_neg_V", "far_bus_pos_V", "far_bus_neg_V", "va_V", "vb_V", "vc_V", "total_load_power_W"):
    error = bus[col][bi]-fine[col][fi]
    chosen, reference = error[uniform], fine[col][fi][uniform]
    comparison["fields"][col] = {"max_abs_all_shared": float(np.abs(error).max()),
                                  "max_abs_uniform_event": float(np.abs(chosen).max()),
                                  "rms_uniform_event": float(np.sqrt(np.mean(chosen**2))),
                                  "relative_rms_uniform_event_percent": float(100*np.sqrt(np.mean(chosen**2)/np.mean(reference**2)))}
result["50ns_vs_25ns"] = comparison

def buses(ax, data, start, end):
    selected = (data["time_s"] >= start) & (data["time_s"] <= end)
    for col, color, label in [("bus_pos_V", "#c93434", "正母线"), ("bus_neg_V", "#bd730a", "负母线")]:
        ax.plot(data["time_s"][selected], data[col][selected]/1000, color=color, label=label)
    ax.set(xlim=(start, end), xlabel="时间 (s)", ylabel="电压 (kV)")

def phases(ax, data, start, end, two=False):
    selected = (data["time_s"] >= start) & (data["time_s"] <= end)
    signals = [("va_V", "#2563d4", "A 相"), ("vb_V", "#188b3c", "B 相"), ("vc_V", "#bc3c3c", "C 相")]
    for col, color, label in signals[:2] if two else signals:
        ax.plot(data["time_s"][selected], data[col][selected]/1000, color=color, label=label)
    ax.set(xlim=(start, end), xlabel="时间 (s)", ylabel="电压 (kV)")

fig, axs = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
buses(axs[0, 0], bus, 0, .6)
axs[0, 0].axvline(.5, color=".4", ls="--")
axs[0, 0].set_title("完整 0–0.6 s：母线降压，1200 万步")
axs[0, 0].legend(ncol=2)
buses(axs[0, 1], bus, .47, .58)
phases(axs[0, 1], bus, .47, .58, two=True)
axs[0, 1].axvline(.5, color=".4", ls="--")
axs[0, 1].set_title("Fig.16 相似工况：母线 ±6 kV → 约 ±2 kV")
axs[0, 1].legend(ncol=4, fontsize=8)
overview = np.abs(ac["time_s"]/100e-6-np.rint(ac["time_s"]/100e-6)) < 1e-7
axs[1, 0].plot(ac["time_s"][overview], magnitude(ac)[overview]/1000, color="#2563d4", label="三相矢量幅值（含纹波）")
axs[1, 0].plot(ac["time_s"][overview], ac["bus_pos_V"][overview]/1000, color="#c93434", label="正母线")
axs[1, 0].axvline(10.133, color=".4", ls="--")
axs[1, 0].set(xlim=(0, 10.2), xlabel="时间 (s)", ylabel="电压 (kV)", title="完整 0–10.2 s：交流降压，2.04 亿步")
axs[1, 0].legend(loc="lower center", ncol=2)
phases(axs[1, 1], ac, 10.10, 10.20)
axs[1, 1].axvline(10.133, color=".4", ls="--")
axs[1, 1].set_title("Fig.19 相似工况：自定开环幅值减半")
axs[1, 1].legend(ncol=3)
fig.suptitle("正式两桥臂 DC/DC｜50 ns｜CLI 直接生成 HPP，保留前向 Euler\n100 kHz 开关；60 Hz 为假设；无闲置第三腿、无生成后积分补丁", fontsize=14)
fig.savefig(ROOT/"two_leg_longrun.png")
plt.close(fig)

page = args.paper_page or ROOT/"source/paper_2019_page8.png"
if not page.exists():
    previous = REPO/"build/shipboard_50ns_longrun_20261024/reference/page_8.png"
    if previous.exists():
        page.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous, page)
if page.exists():
    paper = plt.imread(page)
    fig, axs = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    # Show bounded viewports of the PDF page; retain the original curve pixels.
    for ax, bounds, title in [(axs[0, 0], (82, 451, 292, 70), "论文 Fig.16 原图：开环母线降压"),
                              (axs[1, 0], (474, 831, 586, 304), "论文 Fig.19 原图：外部 PI 闭环 HIL")]:
        ax.imshow(paper, extent=(0, 918, 1188, 0))
        ax.set_xlim(bounds[0], bounds[1])
        ax.set_ylim(bounds[2], bounds[3])
        ax.axis("off")
        ax.set_title(title)
    buses(axs[0, 1], bus, .472, .572)
    phases(axs[0, 1], bus, .472, .572, two=True)
    axs[0, 1].axvline(.5, color=".4", ls="--")
    axs[0, 1].legend(ncol=4, fontsize=8)
    axs[0, 1].set_title("本次两腿模型：50 ns，0.5 s 占空比阶跃")
    phases(axs[1, 1], ac, 10.097, 10.20)
    axs[1, 1].axvline(10.133, color=".4", ls="--")
    axs[1, 1].legend(ncol=3)
    axs[1, 1].set_title("本次两腿模型：50 ns，自定开环调制度阶跃")
    fig.suptitle("论文与本次结果并列对照｜事件类型、降幅和衰减趋势比较\n左侧来源：Milton & Benigni, ESTS 2019, p.375；原图无原始数值，未计算逐点误差", fontsize=13)
    fig.savefig(ROOT/"paper_comparison.png")
    plt.close(fig)
result["paper_figure_available"] = page.exists()

fig, axs = plt.subplots(2, 1, figsize=(11, 6), sharex=True, constrained_layout=True)
for col, label in [("bus_pos_V", "正母线"), ("bus_neg_V", "负母线")]:
    axs[0].plot(bus["time_s"][bi][uniform], (bus[col][bi]-fine[col][fi])[uniform], label=label)
for col, label in [("va_V", "A 相"), ("vb_V", "B 相"), ("vc_V", "C 相")]:
    axs[1].plot(bus["time_s"][bi][uniform], (bus[col][bi]-fine[col][fi])[uniform], label=label)
for ax in axs:
    ax.set_ylabel("50 ns − 25 ns (V)")
    ax.axvline(.5, color=".4", ls="--")
    ax.legend(ncol=3)
axs[1].set(xlim=(.47, .58), xlabel="时间 (s)")
fig.suptitle("直接生成的两腿模型步长对照｜严格 2 µs 共有采样网格")
fig.savefig(ROOT/"timestep_comparison.png")
plt.close(fig)
(ROOT/"analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

def link(label, relative):
    return f"[{label}]({(ROOT/relative).as_posix()})"

w = result["windows"]
lines = ["# 两桥臂 DC/DC：50 ns 长时结果", "",
         "本次直接使用新生成器输出的 HPP；未修改生成后的积分代码或矩阵乘法。两台 DC/DC 只有 A/B 两腿，54 个非地节点，54 个元件测量输出。所有桥仍采用前向 Euler。", "",
         "| 案例 | 步长 | 实际时长 | 完成步数 |", "|---|---:|---:|---:|"]
for name, meta in result["runs"].items():
    lines.append(f"| {name} | {meta['dt_s']*1e9:g} ns | {meta['last_time_s']:g} s | {meta['completed_steps']:,} |")
lines += ["", "三项运行的全部保存值均有限；HPP 的 SHA-256 在编译与运行前后保持一致。全量状态检查周期为 100 步，启动前 2000 步及末步加密；母线与代表相每步检查。", "",
          "| 半开时间窗口 | 正母线均值 | 负母线均值 | 三相矢量幅值均值 | A 相 60 Hz 拟合峰值 |",
          "|---|---:|---:|---:|---:|"]
for name, values in w.items():
    lines.append(f"| {name}: {values['start_s_inclusive']:g}–{values['end_s_exclusive']:g} s | {values['bus_positive_mean_V']:.2f} V | {values['bus_negative_mean_V']:.2f} V | {values['phase_vector_magnitude_mean_V']:.2f} V | {values['phase_A_60Hz_fitted_peak_V']:.2f} V |")
lines += ["", "矢量幅值定义为 sqrt(2/3·(va²+vb²+vc²))，含开关纹波；拟合峰值由 60 Hz 正弦、余弦与直流偏置最小二乘得到，二者不是同一量。晚期窗口仍可能有残余振荡。", "",
          "## 与论文比较", "",
          "| 项目 | 论文 | 本次 |", "|---|---|---|",
          "| Fig.16 母线降压 | 开环，约 0.5 s，±6 kV 降至三分之一，暂态振铃衰减 | 0.5 s 自定占空比 0.8→0.6；约 ±6 kV→±2 kV，有界衰减 |",
          "| Fig.19 交流降压 | 外部微控制器 PI 闭环 HIL；约 10.133 s 幅值约减半 | 10.133 s 自定开环调制度 1→0.5；约 6 kV→3 kV |",
          "| 数值实现 | 50 ns；72 位定点 FPGA | 50 ns；CPU double 离线计算；另有 25 ns 对照 |", "",
          "降幅与定性暂态特征相符，但相位、纹波、瞬态包络及图中的电压偏置并非逐点一致。论文没有提供原始时间序列，也没有公开完整 PI、门极和启动条件，因此没有计算对论文曲线的 RMSE，不声称严格闭环或硬件复现。60 Hz 为读图后的假设。原网表远端 35/36 无独立电源的差异保留，未通过改参数强行贴图。", "",
          "## 步长验证", "",
          f"50 ns 与 25 ns 在事件窗口共有严格 2 µs 网格 {comparison['uniform_2us_event_points']:,} 点；两者均使用 50 ns 控制时钟。相对 RMS 定义为 RMS(50ns−25ns)/RMS(25ns)。", "",
          "| 信号 | 事件窗最大绝对差 | 事件窗相对 RMS 差 |", "|---|---:|---:|"]
for col in ("bus_pos_V", "bus_neg_V", "va_V", "vb_V", "vc_V"):
    values = comparison["fields"][col]
    lines.append(f"| {col} | {values['max_abs_uniform_event']:.4f} V | {values['relative_rms_uniform_event_percent']:.5f}% |")
lines += ["", "这是新模型的步长敏感性检查，不是对原论文数据的误差估计。", "",
          "## 文件", "", "- "+link("完整长时波形", "two_leg_longrun.png"),
          *( ["- "+link("论文并列图", "paper_comparison.png")] if page.exists() else [] ),
          "- "+link("步长差值图", "timestep_comparison.png"),
          "- "+link("全部分析统计", "analysis.json"), "- "+link("50 ns 原样生成 HPP", "dt_50ns/shipboard_zonal_system.hpp"),
          "- "+link("50 ns 母线 CSV", "dt_50ns/busstep.csv"), "- "+link("50 ns 交流 CSV", "dt_50ns/acstep.csv"),
          "- "+link("生成来源与哈希", "dt_50ns/generation.json"), "",
          "源代码、控制细节、重跑命令见正式示例目录的 README_zh.md。"]
(ROOT/"README_zh.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print(json.dumps({"windows": w, "comparison": comparison["fields"]}, ensure_ascii=False, indent=2))
