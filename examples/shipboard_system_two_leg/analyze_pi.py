"""Validate the PI experiment and report tracking, rejection and step sensitivity."""
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
args = parser.parse_args()
ROOT = args.output.resolve()
for p in [Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/simhei.ttf")]:
    if p.exists():
        font_manager.fontManager.addfont(str(p))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(p)).get_name()
        break
plt.rcParams.update({"axes.unicode_minus": False, "font.size": 10, "axes.grid": True,
                     "grid.alpha": .25, "lines.linewidth": 1, "savefig.dpi": 200})

def load(case, name):
    path = ROOT/case/name
    d = np.genfromtxt(path.with_suffix(".csv"), names=True, delimiter=",")
    c = np.genfromtxt(path.parent/(name+"_control.csv"), names=True, delimiter=",")
    m = json.loads(path.with_suffix(".json").read_text())
    g = json.loads((path.parent/"generation.json").read_text())
    assert m["status"] == "completed"
    assert m["completed_steps"] == round(m["duration_s"]/m["dt_s"])
    assert np.isfinite(d.view(np.float64)).all() and np.isfinite(c.view(np.float64)).all()
    assert np.all(np.diff(d["time_s"]) > 0) and np.all(np.diff(c["time_s"]) > 0)
    assert abs(d["time_s"][-1]-m["duration_s"]) < 1e-12
    assert hashlib.sha256((path.parent/"shipboard_zonal_system.hpp").read_bytes()).hexdigest() == g["header_sha256"]
    assert np.min(d["modulation"]) >= 0 and np.max(d["modulation"]) <= 1
    return d, c, {**m, "all_saved_values_finite": True, "waveform_rows": len(d), "control_rows": len(c)}

def window(d, start, end):
    return (d["time_s"] >= start-1e-12) & (d["time_s"] < end-1e-12)

def stats(c, start, end):
    selected = window(c, start, end)
    error = c["reference_V"][selected]-c["filtered_amplitude_V"][selected]
    return {"start_s": start, "end_s_exclusive": end,
            "reference_mean_V": float(c["reference_V"][selected].mean()),
            "filtered_amplitude_mean_V": float(c["filtered_amplitude_V"][selected].mean()),
            "mean_error_V": float(error.mean()), "maximum_absolute_error_V": float(np.abs(error).max()),
            "modulation_mean": float(c["modulation"][selected].mean()),
            "integrator_mean": float(c["integrator"][selected].mean()),
            "limiting_or_antiwindup_fraction": float(c["saturated"][selected].mean()),
            "local_bus_half_span_mean_V": float(.5*c["local_bus_span_V"][selected].mean())}

def settling(c, event):
    selected = c["time_s"] >= event-1e-12
    t = c["time_s"][selected]
    error = np.abs(c["filtered_amplitude_V"][selected]-3000)
    outside = np.flatnonzero(error > .02*3000)
    if len(outside) and outside[-1] == len(t)-1:
        return None
    first = 0 if not len(outside) else outside[-1]+1
    return float(t[first]-event)

pd, pc, pm = load("dt_50ns", "pi_long")
od, oc, om = load("dt_50ns", "open_long")
sd, sc, sm = load("dt_50ns", "probe_ki_600")
fd, fc, fm = load("dt_25ns", "pi_short")
dpd, dpc, dpm = load("dt_50ns", "pi_disturbance")
dod, doc, dom = load("dt_50ns", "open_disturbance")
result = {"runs": {"pi_long": pm, "matched_open_long": om, "25ns_short": fm,
                   "pi_disturbance": dpm, "open_disturbance": dom},
          "windows": {"pi_before": stats(pc, 10.10, 10.13), "pi_after": stats(pc, 10.17, 10.20),
                      "open_after": stats(oc, 10.17, 10.20),
                      "pi_disturbance_after": stats(dpc, .22, .25),
                      "open_disturbance_after": stats(doc, .22, .25)},
          "pi_2percent_settling_s": settling(pc, 10.133), "measurement_is_filtered_amplitude": True}
transient = window(dpc, .163, .22)
result["pi_disturbance_transient_filtered_V"] = {
    "minimum": float(dpc["filtered_amplitude_V"][transient].min()),
    "maximum": float(dpc["filtered_amplitude_V"][transient].max())}
keys, si, fi = np.intersect1d(np.rint(sd["time_s"]/25e-9).astype(np.int64),
                            np.rint(fd["time_s"]/25e-9).astype(np.int64), return_indices=True)
selected = (keys % 80 == 0) & (sd["time_s"][si] >= .09) & (sd["time_s"][si] <= .2)
comparison = {"uniform_2us_points": int(selected.sum()), "fields": {}}
for col in ["va_V", "vb_V", "vc_V", "filtered_amplitude_V", "modulation"]:
    e, ref = (sd[col][si]-fd[col][fi])[selected], fd[col][fi][selected]
    comparison["fields"][col] = {"maximum_absolute_difference": float(np.abs(e).max()),
                                 "relative_rms_difference_percent": float(100*np.sqrt(np.mean(e**2)/np.mean(ref**2)))}
result["50ns_vs_25ns_short"] = comparison

fig, axs = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
axs[0, 0].plot(pc["time_s"], pc["reference_V"]/1000, "--", color=".3", label="参考")
axs[0, 0].plot(pc["time_s"], pc["filtered_amplitude_V"]/1000, color="#c93434", label="PI 反馈幅值")
axs[0, 0].set(xlim=(0, 10.2), xlabel="时间 (s)", ylabel="幅值 (kV)", title="完整 0–10.2 s，2.04 亿个电路步")
axs[0, 0].legend(ncol=2)
keep = window(pd, 10.10, 10.20)
for col, color, label in [("va_V", "#2563d4", "A 相"), ("vb_V", "#188b3c", "B 相"), ("vc_V", "#c93434", "C 相")]:
    axs[0, 1].plot(pd["time_s"][keep], pd[col][keep]/1000, color=color, label=label)
axs[0, 1].set(xlim=(10.10, 10.20), xlabel="时间 (s)", ylabel="相电压 (kV)", title="单台逆变器 PI 闭环：三相输出")
axs[0, 1].legend(ncol=3)
for c, label, color in [(pc, "PI 闭环", "#c93434"), (oc, "匹配开环", "#2563d4")]:
    keep = window(c, 10.10, 10.20)
    axs[1, 0].plot(c["time_s"][keep], c["filtered_amplitude_V"][keep]/1000, color=color, label=label)
    axs[1, 1].plot(c["time_s"][keep], c["modulation"][keep], color=color, label=label+" m")
keep = window(pc, 10.10, 10.20)
axs[1, 0].plot(pc["time_s"][keep], pc["reference_V"][keep]/1000, "--", color=".3", label="参考")
axs[1, 1].plot(pc["time_s"][keep], pc["integrator"][keep], "--", color="#188b3c", label="PI 积分项")
axs[1, 0].set(xlim=(10.10, 10.20), xlabel="时间 (s)", ylabel="滤后幅值 (kV)", title="参考跟踪：6 kV → 3 kV")
axs[1, 1].set(xlim=(10.10, 10.20), xlabel="时间 (s)", ylabel="调制度 / 积分项", title="PI 自行调节 m；开环直接 1 → 0.5")
for ax in axs.flat:
    ax.axvline(10.133, color=".4", ls=":")
    ax.legend(fontsize=9)
fig.suptitle("两腿 DC/DC 电网｜逆变器 1 电压幅值 PI｜50 ns 电路步长\n控制周期 10 µs；Kp=0.2，Ki=600 /s，测幅滤波 τ=0.2 ms；其余五台逆变器 m=1", fontsize=14)
fig.savefig(ROOT/"pi_closed_loop_results.png")
plt.close(fig)

fig, axs = plt.subplots(3, 1, figsize=(11, 8), sharex=True, constrained_layout=True)
for c, name, color in [(dpc, "PI 闭环", "#c93434"), (doc, "匹配开环", "#2563d4")]:
    keep = window(c, .15, .25)
    for ax, col, scale in [(axs[0], "filtered_amplitude_V", 1000), (axs[1], "modulation", 1), (axs[2], "local_bus_span_V", 2000)]:
        ax.plot(c["time_s"][keep], c[col][keep]/scale, label=name, color=color)
axs[0].axhline(3, ls="--", color=".3", label="3 kV 参考")
for ax in axs:
    ax.axvline(.163, color=".3", ls=":")
    ax.legend(ncol=3)
axs[0].set(ylabel="滤后幅值 (kV)", title="母线降压扰动：参考保持 3 kV，0.163 s 将 DC/DC 占空比 0.8 → 0.75")
axs[1].set_ylabel("逆变器 1 调制度 m")
axs[2].set(xlim=(.15, .25), xlabel="时间 (s)", ylabel="本地母线半跨压 (kV)")
fig.suptitle("闭环抗扰验证｜PI 测量输出电压并补偿电源变化，无母线前馈")
fig.savefig(ROOT/"pi_disturbance_rejection.png")
plt.close(fig)

fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
probe_stats = []
for ki in [300, 600, 1000]:
    _, c, _ = load("dt_50ns", f"probe_ki_{ki}")
    keep = window(c, .132, .165)
    axs[0].plot((c["time_s"][keep]-.133)*1000, c["filtered_amplitude_V"][keep]/1000, label=f"Ki={ki} /s")
    axs[1].plot((c["time_s"][keep]-.133)*1000, c["modulation"][keep], label=f"Ki={ki} /s")
    probe_stats.append({"ki_per_s": ki, "settling_2percent_s": settling(c, .133)})
axs[0].axhline(3, color=".3", ls="--")
axs[0].set(ylabel="滤后幅值 (kV)", title="短时调参：Kp=0.2，滤波 τ=0.2 ms；最终采用 Ki=600 /s")
axs[1].set(xlim=(-1, 32), xlabel="距参考阶跃 (ms)", ylabel="调制度 m")
for ax in axs: ax.legend(ncol=3)
fig.savefig(ROOT/"pi_gain_comparison.png")
plt.close(fig)
result["gain_probes"] = probe_stats

source = ROOT/"source"
source.mkdir(exist_ok=True)
old_source = REPO/"build/shipboard_two_leg_50ns_20261024/source"
for filename in ["paper_2019.pdf", "paper_2019_page8.png"]:
    if not (source/filename).exists() and (old_source/filename).exists():
        shutil.copyfile(old_source/filename, source/filename)
if (source/"paper_2019_page8.png").exists():
    fig, axs = plt.subplots(1, 2, figsize=(15, 5), constrained_layout=True)
    axs[0].imshow(plt.imread(source/"paper_2019_page8.png"), extent=(0, 918, 1188, 0))
    axs[0].set_xlim(474, 831); axs[0].set_ylim(586, 304); axs[0].axis("off")
    axs[0].set_title("论文 Fig.19：外部微控制器 PI 闭环 HIL")
    keep = window(pd, 10.097, 10.2)
    for col, color, label in [("va_V", "#2563d4", "A 相"), ("vb_V", "#188b3c", "B 相"), ("vc_V", "#c93434", "C 相")]:
        axs[1].plot(pd["time_s"][keep], pd[col][keep]/1000, color=color, label=label)
    axs[1].axvline(10.133, color=".4", ls=":")
    axs[1].set(xlim=(10.097, 10.2), xlabel="时间 (s)", ylabel="相电压 (kV)", title="本次：自行设计的单逆变器电压幅值 PI")
    axs[1].legend(ncol=3)
    fig.suptitle("50 ns 闭环降压对照｜论文未公开增益及测量结构，本次参数自行设计；未逐点拟合原图", fontsize=13)
    fig.savefig(ROOT/"paper_pi_comparison.png")
    plt.close(fig)

(ROOT/"analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
w = result["windows"]
report = ["# 单逆变器电压幅值 PI 闭环试验", "",
          "在 codex/two-leg-dcdc-50ns 分支的正式两腿模型上增加逆变器 1 的输出电压幅值 PI，其他五台逆变器仍保持 m=1。电路 HPP 仍由 CLI 原样生成、54 节点、前向 Euler；无生成后补丁。", "",
          "## 控制结构与参数", "",
          "每 50 ns 推进电路并累加逆变器 1 三相输出；每个 10 µs 载波周期结束后取前一周期相电压均值，再用 Clarke α=(2va−vb−vc)/3、β=(vb−vc)/sqrt(3) 得幅值 sqrt(α²+β²)，经一阶低通后反馈。先均值后测幅可以抑制载波；Clarke 去除零序。这里反馈的是滤后幅值指标，不是相电压 RMS。", "",
          "```text", "控制周期 Tc = 10 µs；电路步长 h = 50 ns；PWM = 100 kHz；参考频率 = 60 Hz（假设）",
          "滤波 τ = 0.2 ms，系数 1-exp(-Tc/τ) = 0.0487706",
          "e = (Vref - Vfiltered)/6000", "I_next = I + 600*Tc*e（触发向外饱和时冻结）",
          "m = clamp(0.2*e + I, 0, 1)", "```", "",
          "未使用母线前馈，也没有在闭环里直接将调制度乘 0.5；10.133 s 改的是参考值 6000→3000 V。启动约 4 ms，参考随后 2 ms 线性升高。DC/DC 约 20 µs 开启、2 ms 软启动后占空比保持 0.8。浮点门极使能比较使本次首次 DC/DC 使能为 20.05 µs；两积分步长均沿用相同 50 ns 门极网格。", "",
          "抗饱和采用条件积分：输出上限且误差要求继续升高、或下限且误差要求继续降低时，停止该次积分；反向误差可退出饱和。CSV saturated 包括输出限幅或候选积分被阻止，不严格等于 m==1。disable 清空 PI 与测量滤波状态。", "",
          "## 实际结果", "", "| 工况 / 窗口 | 参考 | 滤后幅值均值 | 平均误差 | m 均值 |",
          "|---|---:|---:|---:|---:|"]
for name, v in w.items():
    report.append(f"| {name}: {v['start_s']:g}–{v['end_s_exclusive']:g} s | {v['reference_mean_V']:.1f} V | {v['filtered_amplitude_mean_V']:.3f} V | {v['mean_error_V']:.3f} V | {v['modulation_mean']:.6f} |")
report += ["", f"主闭环从零初态完成 10.2 s、{pm['completed_steps']:,} 个 50 ns 步；匹配开环也完成相同时间。保存值均有限。滤后幅值进入并保持 3000 V±2% 的时间约为 {result['pi_2percent_settling_s']*1000:.2f} ms（按保存的控制记录判定）。", "",
           "6000 V 目标略高于 m≤1 时的稳态可用输出，前段约 22 V 残差属于调制度上限；不靠扩大线性调制范围或改低参考来掩盖。3000 V 位于可调范围，PI 消除其平均误差；瞬时纹波仍存在。", "",
           "抗扰案例在 0.133 s 将参考降至 3 kV，然后 0.163 s 将 DC/DC 占空比由 0.8 改为 0.75，使本地母线从约 ±6 kV 降为约 ±5 kV。PI 自行提高 m；匹配开环仍为 m=0.5。该案例验证反馈补偿能力，母线阶跃是自行加入的诊断，不是论文给定的第二次事件。", "",
           "## 与论文的关系", "",
           "2019 论文第 375–376 页 Fig.17/19 使用外部 TI F28335 对一台三相逆变器闭环；未公开 PI 增益、采样率、峰值/RMS/dq测量选择及滤波。本次参照所控对象自行设计幅值 PI，在 CPU 中运行；不能称为恢复论文原 PI、72 位定点 FPGA 或真实外部 HIL。降幅与最终幅值类似，过渡包络/相位/纹波仍有差异。没有原始时间序列，未计算对论文原图的 RMSE。", "",
           "开环对照也只改变逆变器 1，其余五台保持 m=1；上一轮六台同时开环降幅的数据没有混入本次误差比较。", "",
           "## 验证与文件", "",
           "25 ns 短时对照使用同一 50 ns 门极时钟、10 µs PI 周期和物理事件时刻；比较的是 0.09–0.20 s 严格 2 µs 共有点。详细最大差与相对 RMS 差见 analysis.json，不是论文数据误差。控制器有独立的平均对象阶跃/抗扰回归，电路生成器旧测试也保留。", "",
           "控制 CSV 在控制区间起点保存新参考和新命令、前周期测量；波形 CSV 在积分区间终点保存刚结束区间的状态与保持命令。所有跟踪指标使用控制 CSV。", ""]
for name, file in [("闭环完整结果图", "pi_closed_loop_results.png"), ("母线扰动对比", "pi_disturbance_rejection.png"),
                   ("短时增益对比", "pi_gain_comparison.png"), ("论文并列图", "paper_pi_comparison.png"),
                   ("完整数值统计", "analysis.json"), ("50ns闭环波形", "dt_50ns/pi_long.csv"),
                   ("50ns闭环控制记录", "dt_50ns/pi_long_control.csv"), ("未修改的HPP", "dt_50ns/shipboard_zonal_system.hpp")]:
    if (ROOT/file).exists(): report.append(f"- [{name}]({(ROOT/file).as_posix()})")
report += ["", "复算入口为 examples/shipboard_system_two_leg/run_pi.py；可用 --probe-only 只调参，--skip-probes 复用调参结果，--analyze-only 只重新统计绘图。默认输出独立目录，不覆盖上一轮开环结果。"]
(ROOT/"README_zh.md").write_text("\n".join(report)+"\n", encoding="utf-8")
print(json.dumps({"windows": w, "settling_2percent_s": result["pi_2percent_settling_s"], "short_step_comparison": comparison}, ensure_ascii=False, indent=2))
