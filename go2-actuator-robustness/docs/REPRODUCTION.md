# 运行与复现说明

## 已验证环境
Python 3.11；mjlab 1.2.0；MuJoCo 3.5.0；mujoco-warp 3.5.0；
warp-lang 1.12.0；rsl-rl-lib 5.0.1；torch 2.15.0；scipy 1.17.1。
工作站为 Windows 11 / WSL2 Ubuntu 22.04，RTX 4060 Laptop 8 GB，驱动 621.01。
版本约束见 [constraints.txt](../constraints.txt)。

上游为 unitreerobotics/unitree_rl_mjlab，
固定提交 1425b15f73bd4095f0df53709d7c389c3eb9e790。
Linux 系统库按上游 [安装说明](https://github.com/unitreerobotics/unitree_rl_mjlab/blob/main/doc/setup_zh.md) 安装。

## 当前工作站
以下激活方式已在原工作站使用；下载仓库的其他机器需更换实际路径。

```bash
source /root/robotrl_go2/go2rl/bin/activate
cd /root/robotrl_go2/go2-actuator-robustness
export UNITREE_RL_MJLAB=/root/robotrl_go2/unitree_rl_mjlab
```

## 新机器安装模板
先准备兼容的 NVIDIA 驱动、上游 Linux 系统库及上述固定提交的官方仓库。
如果已有独立 Python 3.11 环境则复用；以下示例仅供尚无项目环境的机器：

```bash
export UNITREE_RL_MJLAB=/absolute/path/to/unitree_rl_mjlab
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -c constraints.txt -e "$UNITREE_RL_MJLAB" scipy==1.17.1
uv pip install --no-deps -e .
```

此安装模板未在第二台机器验证。constraints 中的 Torch 需要兼容其 CUDA 运行时的驱动；
不要在当前已部署的 go2rl 环境里重复创建环境。

## 训练与评估命令模板
这些是对应已完成实验的调用形式；本文不会启动新训练。
每种初始策略使用 256 个环境、1500 轮、训练种子 42。
先指定本机真实存在的模型路径，再运行需要的命令：

```bash
export BASELINE_CHECKPOINT=/absolute/path/to/baseline/model_1499.pt
export DR_CHECKPOINT=/absolute/path/to/dr/model_1499.pt
export BALANCED_CHECKPOINT=/absolute/path/to/balanced/model_1998.pt

python -m go2_robust.train --variant dr --iterations 1500 --num-envs 256 --seed 42
python -m go2_robust.train --variant history --iterations 1500 --num-envs 256 --seed 42

python -m go2_robust.diagnose --baseline-checkpoint "$BASELINE_CHECKPOINT"
python -m go2_robust.train --variant balanced --iterations 500 --num-envs 256 --seed 42 --resume-from "$DR_CHECKPOINT"
python -m go2_robust.evaluate --variant balanced --checkpoint "$BALANCED_CHECKPOINT" --samples --output results/balanced_s42
```

Balanced 模型使用额外 500 轮微调，累计 2000 个更新周期。
model_1998.pt 的命名来自上游恢复训练时的迭代编号语义；实际累计预算记录在结果 JSON 中。
已有成功状态受到重复运行保护。不要为重新绘图重复训练。

## 交互演示
需要匹配 variant 的本地模型；以下为调用模板：

```bash
python -m go2_robust.demo --variant balanced --checkpoint "$BALANCED_CHECKPOINT" --delay-ms 40 --kp-scale 1.0 --kd-scale 1.0
```

浏览器打开 http://localhost:8080 。交互演示会接受临时指令并可能在失败后重置，
固定工况指标使用 evaluate 的独立协议。一次只启动一个默认端口的 viewer。

## 数据与图
直接查看 [五图索引](../reports/visualization/README.md)、
[24 行工况指标](../reports/precision_evaluation.csv) 和
[绘图源数据](../reports/visualization/source_data)。
公开图包含 PNG、SVG、PDF；大 TIFF 保留在本地完整图包中。
源数据包含 28,800 条标称时序记录、聚合值和训练曲线；
历史策略没有保存逐环境标称时序，因此未虚构其时序曲线。

原工作站绘图调用为：
```bash
python -m go2_robust.visualize
```
当前绘图入口仍读取 results/ 下的原始实验路径，公开快照未包含这些完整原始目录。
独立机器重新运行该入口需要恢复脚本列出的输入路径；仓库的 source_data/ 保留了
公开图所使用的标称时序和汇总数据，可独立检查图表数据。

网页上传会新建 GitHub 提交历史。结果记录里的 extension_commit 指向实验当时的本地
Git 提交；这些历史提交不包含在源码 ZIP 中，本地完整 Git 仓库仍保留。
权重与原始训练日志不在上传包里，因此本包用于源码和工程结果展示，
无需 GPU 即可阅读；执行训练、评估或演示仍需模型/环境。
