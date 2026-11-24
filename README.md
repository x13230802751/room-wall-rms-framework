# 房间墙面粗糙度与五接口测量框架

**输入一个房间的完整点云，输出自动识别的墙面候选、每墙支持点 RMS，并接入门窗、结构四角、局部测区和 Word 报告接口。**

主方法固定为：**完整有限点云 → 原版 Efficient RANSAC 支持点 → 墙体几何规则 → SVD 最佳拟合平面 → RMS**。不做去噪滤波，不降采样，不使用 50 mm 恢复带，不在最终拟合后按残差删点。法向估计使用完整点云的 30 邻域 PCA；它是原版检测器的输入准备。

## 输入与输出

| 输入 | 输出 |
|---|---|
| 单房间 PCD 或 XYZ CSV；明确 m/mm 和向上方向（默认 +Z）；不必提供四点 | 候选墙数量与编号、每墙原版支持点 RMS（mm）、原始点序号与 XYZ、参考平面、洞口候选、可靠性受检的结构四角、局部四点和 RMS、result.json、report.docx |
| 可选队友提供的已确认洞口或局部测区 JSON | 对应几何排除后的 surface_rms、whole_wall_rms、local_rms；支持点基线 support_rms 始终保留 |

墙数量是候选数量，不是人工确认真实墙数。没有可靠顶面、四墙不闭合或角点离实测墙点太远时，整墙结构测量标为 needs_review，支持点和有效局部测区继续输出。自动门窗识别是几何空洞候选，不能把遮挡自动当作真实洞口。

## 安装与运行

当前验证平台：Windows、Python 3.11、MinGW g++。Python 3.10+ 可安装；其他平台的原生编译尚未验证。需要 Git 和可运行的 g++。

```powershell
git clone https://github.com/x13230802751/room-wall-rms-framework.git
cd room-wall-rms-framework
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe scripts/fetch_native.py
.\.venv\Scripts\python.exe native/build.py --source-root native/sources
.\.venv\Scripts\python.exe -m room_measurement --cloud 'D:/data/room.pcd' --unit m --up 0 0 1 --out outputs/my_room
```

使用可编辑安装 `pip install -e .`，因为原生程序在仓库 native/bin 中构建。原版依赖按固定提交获取，不随仓库重新分发；请保留其研究用途与 GPL 等原有许可，见 [来源说明](PROVENANCE.md)。

无课程数据也可以验证安装：

```powershell
.\.venv\Scripts\python.exe examples/make_demo.py --out outputs/demo.csv
.\.venv\Scripts\python.exe -m room_measurement --cloud outputs/demo.csv --unit m --out outputs/demo_run
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

输出目录必须为空或不存在。程序默认生成 Word；只需要机器接口时加 `--json-only`。一份点云对应一个房间，多个房间分别运行。

## 对接总框架

五个接口的签名和 JSON 协议见 [接口说明](docs/interfaces.md)。总控入口为 `room_measurement.pipeline.run`，可用 `Interfaces` 替换其中任何模块。

1. **分墙**：原版检测及墙规则，保留原始行号。这里“取回原始点”只是索引取值，不扩展点集。
2. **门窗**：墙面二维空洞与边界直线拟合候选，或接队友已确认结果。仅 confirmed 洞口参与几何排除。
3. **墙角**：四墙闭合、可靠顶面和角点附近实测支持检查；不把支持点包围框当作结构四角。
4. **局部测区**：默认寻找覆盖率合格的 1×1 m 实墙区域，避开洞口候选；不根据低 RMS 挑选区域。
5. **RMS**：接受原始点及可选四角，几何求交后用原始 XYZ 重新 SVD 拟合，输出毫米 RMS。

确认洞口的空间排除属于测区定义，不是按噪声或残差删点。`support_rms`、`surface_rms`、`whole_wall_rms`、`local_rms` 的测量域不同，不能混称一个“墙面真值”。

## 负责范围与证据

你的核心负责部分是“完整房间点云 → 墙面支持点 → 墙面粗糙度 RMS”和向总框架提供稳定接口。课程 Task 1 还需要房间长宽高、门窗宽高、文献综述、框架设计及误差评价；这些都应由小组分工完成。

- [总体任务与个人分工说明](docs/项目总体框架与个人任务说明.docx)
- [可读版说明](docs/handoff.md)
- [实现与验收计划](docs/implementation_plan.md)
- [真实数据验证摘要](results/integration_verification.json)
- [安装、独立编译与演示验证记录](results/build_verification.json)

代码可端到端运行，不等于全部工程测量精度已通过验收。原版支持集可能漏掉真实鼓包；门窗几何候选和结构尺寸需要独立参考验证。原始课程点云、课程文件、旧实验、凭据和本地依赖不会上传。已有旧仓库保持不变。
