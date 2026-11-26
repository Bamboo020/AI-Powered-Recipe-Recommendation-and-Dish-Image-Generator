# 当前本机运行环境记录

状态日期：2026-11-22。

## 硬件与 Python

| 项目 | 当前值 |
| --- | --- |
| 操作系统 | Windows 11 |
| GPU | NVIDIA GeForce RTX 4080 Laptop GPU |
| 显存 | 约 12 GB |
| Python | 3.14.7 |
| 解释器 | `D:\CondaEnvs\myenv\python.exe` |
| PyTorch | 2.14.1+cu132 |
| CUDA 可用性 | 已通过 `torch.cuda.is_available()` 验证 |
| 模型缓存 | `D:\CondaEnvs\myenv\cache` |

旧的 Apple M4/MPS 实测记录只保留在 `evaluation/results` 的历史报告中，不再代表当前机器。

## 当前文件状态

- `D:\CondaEnvs\myenv` 已安装基础后端、AI 推理和训练依赖。
- Diffusers 官方训练示例位于 `D:\CondaEnvs\myenv\src\diffusers`。
- 项目根目录目前没有 `.env`。
- `data/` 目录目前没有原始或处理后的数据文件。
- 当前没有 `recipes.sqlite3` 和 `image_jobs.sqlite3`；启动后按需创建。
- CNN 标签文件存在，但 `resnet18.pt` checkpoint 不存在。

## 启动基础应用

当前 `scripts/start-backend.ps1` 面向 `backend\.venv`。若直接复用已经配置好的训练环境，应在项目根目录执行：

```powershell
Copy-Item .env.example .env
Set-Location backend
& 'D:\CondaEnvs\myenv\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端启动前端：

```powershell
Set-Location 'D:\2026Fall\AI\Final Project\AI-Dish-Test\frontend'
npm ci
npm run dev
```

浏览器地址为 `http://127.0.0.1:5173`，后端状态为 `http://127.0.0.1:8000/api/health`。

如果不设置任何 AI 环境变量，基础应用仍可使用明确标注的 demo 数据和确定性逻辑；模型相关功能会显示未配置、使用模板回退或返回 503。

## 完整功能所需的额外准备

1. 按 `windows-training.zh.md` 下载并处理 Food.com 与 Food-101。
2. 导入 Food.com 后才会出现真实食谱和真实数据餐食计划。
3. 在 `.env` 中选择实际存在的 Ollama、Embedding、Diffusion 和 CNN 路径。
4. 当前 CNN 必须先重新训练或取得可信 checkpoint。
5. Ollama 服务及其模型需要单独安装/拉取；本项目没有自动下载。
6. 对 Boston 在线数据功能，需要允许访问 Boston.gov、美国 Census Geocoder 和登记的资源来源。

## 已验证范围

- 训练环境依赖导入成功，CUDA 检测成功。
- 46 个后端测试通过。
- Python 训练脚本可编译并显示命令行参数。
- PowerShell 设置、下载和 Diffusion 启动脚本通过语法检查。
- Diffusers 官方训练示例能够加载；`torchao` 缺失仅对使用 torchao 序列化的特定 checkpoint 有影响，当前流程不依赖它。

这些验证没有替代真实数据下载、模型权重下载或完整训练。
