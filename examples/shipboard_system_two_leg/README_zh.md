# 使用两腿 DC/DC 的船舶系统示例

后续增加了独立的[单逆变器电压幅值 PI 闭环试验](README_PI_zh.md)，包含匹配开环、母线抗扰及 50/25 ns 对照。下文的原始长时案例仍保留。

本示例从 `examples/shipboard_system/shipboard_system.netlist` 派生：两台供电侧 DC/DC 使用正式元件 `BridgeConverter2LegIdealSwitches`，仅保留实际连接正、负母线的 A、B 两腿。六台三相逆变器继续使用原来的三腿元件。原示例保留，便于比较。

## 网表改动

两台 DC/DC 分别为：

```text
BridgeConverter2LegIdealSwitches dcdc1(DT, DCDC_CIN, DCDC_LFILT, DCDC_RFILT) {1,0,2,3,19}
BridgeConverter2LegIdealSwitches dcdc2(DT, DCDC_CIN, DCDC_LFILT, DCDC_RFILT) {35,0,36,11,27}
```

同时删除原来只用于闲置 C 腿的节点 55、56、两个 1 MΩ 接地电阻和 `DCDC_HIGHZ` 常量。其余参数、节点与连接保持原样，包括 `DT=50.0e-9`、DC/DC 每腿 100 µH 电感与 0.1 mΩ 串联电阻、母线输出 100 µF 电容、电缆参数和 7 Ω 交流负载。模型名称仍为 `shipboard_zonal_system`，生成的头文件应放在独立输出目录。

有一项原示例条件需要明确：节点 1、0、2 接有 ±10 kV 输入源；第二台 DC/DC 的输入节点 35、0、36 没有对应的独立外部电压源。本示例也保留这一条件。因此不能默认把这里的结果当作论文左右两端均有独立电源的工况。若要增加右侧电源，应建立并明确标注另外的实验。

## 两腿元件接口

```text
BridgeConverter2LegIdealSwitches label(time_step, dc_cap, leg_ind, leg_res) {P,G,N,A,B}
```

| 参数或端子 | 含义 |
|---|---|
| `time_step` | 元件离散步长，单位 s；与系统其他动态元件的步长一致 |
| `dc_cap` | 分裂直流母线中每只输入电容的电容量，单位 F |
| `leg_ind`、`leg_res` | A、B 两腿各自的串联电感与电阻，单位 H、Ω；电阻允许为零 |
| `P,G,N` | 直流正极、中点、负极 |
| `A,B` | 两个桥臂经各自串联电感、电阻后的输出端 |

生成的求解器为每个元件提供两个门极控制位 `sw_ctrl_<label>[2]`，顺序为 A、B；每一位为 `true` 时选择该腿上管，为 `false` 时选择下管。`sw_en_<label>=true` 表示启用门极控制；为 `false` 时采用与原三腿元件相同的二极管续流逻辑。门极值为零不是关闭桥臂。

四个测量输出为 `cp_voltage_<label>`、`cn_voltage_<label>`、`la_current_<label>`、`lb_current_<label>`，对应上下直流电容电压及 A、B 腿电流。没有 C 腿的门极、状态、电流输出、源贡献或节点。完整系统求解器的参数列表还包含其他元件的信号，应以实际生成的头文件签名为准。

这是共用分裂直流母线的高压两腿桥模型；它没有隔离变压器，也没有隔离型双有源桥（DAB）的两组全桥。A、B 两腿可分别建立正、负输出。这里的“two leg”表示桥臂数量。

## 为什么去掉闲置腿

原三腿复用接法在 DC/DC 额外的 C 腿接入 1 MΩ 电阻。它与 100 µH 电感形成约 0.1 ns 的衰减时间常数。启用整台变换器时，C 腿仍会接到某一条直流轨；仅把其门极设为零并不能关掉它。

对该近似串联 RL 模式，前向 Euler 的放大因子是 `1-hR/L`。50 ns 时约为 −499，物理上的快速衰减会变成交替数值放大。删除未使用的整个 C 腿后，该附加快速模式也随之消失。

本元件沿用原桥模型的显式 Euler 更新，保留 A、B 有效支路以及直流电容的原更新逻辑；不借助局部 ZOH、额外子步或更小的系统步长处理闲置腿。因此，此示例修正的是复用三腿模块时附加的未使用支路。它也不承诺任何参数、负载、连接和步长下都稳定；其他显式状态仍须满足各自的稳定性与精度要求。

## 与论文的对应关系

- Milton、Benigni、Bakos，*System-Level, FPGA-Based, Real-Time Simulation of Ship Power Systems*，2017，[DOI: 10.1109/TEC.2017.2692525](https://doi.org/10.1109/TEC.2017.2692525)。期刊第 739 页 Fig.3 明确使用旧电流、旧端电压进行各腿电感及直流电容的显式 Euler 更新；本两腿元件保留该类更新形式。第 743–744 页仅以系统方框表示供电侧 DC/DC，没有公开其闲置腿内部处理。
- Milton、Benigni，*Software and Synthesis Development Libraries for Power Electronic System Real-Time Simulation*，2019，[DOI: 10.1109/ESTS.2019.8847940](https://doi.org/10.1109/ESTS.2019.8847940)。第 375 页 Fig.16 是约 0.5 s 时把 ±6 kV 母线降低到三分之一的开环实验，振铃随时间衰减；Fig.19 是约 10.133 s 时某个逆变器三相输出峰值由约 ±6 kV 降至 ±3 kV 的外部闭环 HIL 实验。两图对应不同控制事件。

论文明确给出 50 ns 步长、100 kHz 开关频率及 72 位定点 FPGA 实现。约 60 Hz 工频来自读图推断，控制器 PI 增益、PWM 具体设定和启动过程没有完整公开。本示例网表本身不含控制程序；后续采用的占空比、软启动、60 Hz 参考和调制深度阶跃均须由仿真程序单独披露。自行施加 SPWM 幅值减半只能对比降幅及暂态形状，不能代替 Fig.19 的原 PI 闭环。

2017 论文报告双母线系统有 54 个节点；原公开网表有 56 个非地节点，额外的两个正是闲置 C 腿的 55、56。本示例恢复到 54 个非地节点。这是支持两腿建模选择的结构对比线索，不能作为原作者实际代码必然使用两腿的严格证明。公开资料不足以保证拓扑、初始条件、控制和数值实现与原实验逐项一致，后续结果应表述为 50 ns 下的模型验证及论文特征对比。

## 生成与验证

构建支持该元件的 CLI 后，在独立工作目录中将本目录的 `shipboard_system.netlist` 作为输入，生成 `shipboard_zonal_system.hpp`，再由 C++ 仿真程序循环调用。每次调用推进一个 50 ns 时间步。调用者负责门极信号、启停、时间记录及波形导出。

仿真入口为本目录的 `run.py` / `run.ps1`，控制在 `simulate.cpp` 中。输出默认放在仓库的 `build/shipboard_two_leg_50ns_20261024/`，包含未经后处理的 HPP、CSV、运行日志、哈希记录、`README_zh.md` 结果报告及 `paper_comparison.png` 论文并列图。

```powershell
python examples/shipboard_system_two_leg/run.py --codegen build/two_leg_codegen/SolverCodegen.exe --compiler "D:/Program Files/Mingw/bin/g++.exe"
```

脚本使用 NumPy、Matplotlib。也可用 `run.ps1 -Python <解释器路径> -Codegen <CLI路径>`；PowerShell 包装脚本默认使用本机 Anaconda Python。`--analyze-only`（PowerShell 为 `-AnalyzeOnly`）只验证既有数据并绘图。图像参考页可通过 Python 脚本的 `--paper-page <2019论文PDF第8页完整图像>` 指定；没有参考图时仍生成本次波形和数值对比，不伪造原论文数据。仓库不附带论文或其图像。

本次已完成 50 ns 的母线降压 0.6 s（1200 万步）和交流降压 10.2 s（2.04 亿步），另完成 25 ns 母线对照 0.6 s（2400 万步）。三项保存数据均有限，生成的 HPP 在编译运行前后哈希一致。事件窗三相相对 RMS 步长差均小于 0.022%；这是本模型步长敏感性结果，不是与论文原始数据的逐点误差。

本次控制条件为：20 µs 开启 DC/DC，2 ms 内占空比 0.5→0.8；4 ms 开启逆变器，2 ms 内调制度 0→1。母线案例在 0.5 s 将占空比 0.8→0.6；交流案例在 10.133 s 将调制度 1→0.5。100 kHz 锯齿载波、60 Hz 三相正弦参考，所有案例用相同 50 ns 控制时钟。50/25 ns 均在积分区间起点设置门极、区间终点记录结果。

结果的母线均值由约 ±5999 V 变为约 ±2000 V；交流幅值指标由约 5979 V 变为约 2999 V，降压暂态有界。与论文的比较限于事件类型、降幅和衰减趋势，保留前述未公开控制及远端电源差异。

本机使用 MinGW 15.2 构建 CLI 的命令如下。`-Wno-template-body` 用于现有旧版 Eigen 对新编译器的兼容；`-static` 避免本机 Anaconda 与 MinGW 运行库的 DLL 冲突，两者不改变电路算法。

```powershell
& 'D:/Program Files/CMake/bin/cmake.exe' -S . -B build/two_leg_codegen -G 'MinGW Makefiles' '-DCMAKE_CXX_COMPILER=D:/Program Files/Mingw/bin/g++.exe' '-DCMAKE_C_COMPILER=D:/Program Files/Mingw/bin/gcc.exe' '-DCMAKE_MAKE_PROGRAM=D:/Program Files/Mingw/bin/mingw32-make.exe' '-DCMAKE_CXX_FLAGS=-Wno-template-body' '-DCMAKE_EXE_LINKER_FLAGS=-static' '-DBUILD_TESTING=OFF' '-DSOLVERCODEGEN_BUILD_TESTS=ON'
& 'D:/Program Files/CMake/bin/cmake.exe' --build build/two_leg_codegen --target SolverCodegen --parallel 4
& 'D:/Program Files/CMake/bin/ctest.exe' --test-dir build/two_leg_codegen -R bridge_converter_2leg_e2e --output-on-failure
```

新两腿元件在禁用且零电流时，用相对中点的 `eout-G` 判断二极管状态，并通过 ±100 V 中点平移测试；旧三腿实现不变。当前船舶网表的 G 全部接地，此处理不改变其方程。二极管过零和严格零电流判定仍沿用原离散近似，未保证任意浮动中点或关断工况都稳定。
