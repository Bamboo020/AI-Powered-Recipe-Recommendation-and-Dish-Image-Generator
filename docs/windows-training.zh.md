# Windows 模型训练准备

状态日期：2026-11-22。本文只针对 `AI-Dish-Test`。

## 当前已完成的环境

| 项目 | 当前值 |
| --- | --- |
| Python | `D:\CondaEnvs\myenv\python.exe`（3.14.7） |
| PyTorch | 2.14.1+cu132 |
| GPU | NVIDIA GeForce RTX 4080 Laptop GPU，约 12 GB 显存 |
| CUDA | PyTorch 检测可用 |
| 模型缓存 | `D:\CondaEnvs\myenv\cache` |
| Diffusers 官方示例 | `D:\CondaEnvs\myenv\src\diffusers` |

Sentence Transformers、Transformers、Datasets、Accelerate、PEFT、TRL、Diffusers、scikit-learn、TensorBoard 和 ftfy 已安装并通过导入检查。

重新检查或补齐依赖：

```powershell
& '.\scripts\setup-training-windows.ps1'
& 'D:\CondaEnvs\myenv\python.exe' .\scripts\check_training_environment.py
```

## 当前尚未完成的部分

当前 `data/` 中没有数据集，Hugging Face 基础模型也没有由本项目下载。训练脚本已经准备，但尚未在当前 Windows 环境进行正式训练。

## 数据集名称、位置和下载

| 数据集 | 必须保存到 | 用途 |
| --- | --- | --- |
| Food.com Recipes and Reviews | `data\raw\foodcom-recipes-and-reviews.zip` | 食谱导入和任务专用文本样本来源 |
| Food-101 | `data\raw\food-101.tar.gz` | 当前五类 CNN 训练 |

在项目根目录执行：

```powershell
.\scripts\download-data.ps1
# Download only one dataset if needed:
.\scripts\download-data.ps1 -Dataset foodcom
.\scripts\download-data.ps1 -Dataset food101
```

来源：

- Food.com: https://www.kaggle.com/api/v1/datasets/download/irkaal/foodcom-recipes-and-reviews
- Food-101: https://data.vision.ee.ethz.ch/cvl/food-101.tar.gz

Kaggle 如要求认证，需要先配置自己的 Kaggle API 凭据。原始数据、处理数据和模型权重均由 Git 忽略。

## 数据预处理

```powershell
$py = 'D:\CondaEnvs\myenv\python.exe'
& $py .\scripts\prepare_foodcom.py
& $py .\scripts\import_foodcom.py
& $py .\scripts\extend_photo_recipes.py
& $py .\scripts\import_foodcom.py --input .\data\processed\foodcom_photo_extension.jsonl
& $py .\scripts\prepare_food101.py
```

完成后应检查 `/api/health` 的真实食谱数量，并核对 `data_metadata/datasets.json` 中记录的来源、计数和哈希是否仍与本次下载一致。

## 训练入口

### 五类 Food-101 CNN

```powershell
& 'D:\CondaEnvs\myenv\python.exe' .\scripts\train_cnn.py --epochs 60 --batch-size 32
```

支持类别为 dumplings、fried_rice、omelette、pizza 和 ramen。脚本在当前机器上会优先使用 CUDA。输出 checkpoint 到 `model_assets\food101_5class`，指标写入 `evaluation\results`。

### Sentence Transformer 检索模型

训练文件：`data\training\retriever\train.jsonl`。

```json
{"query":"tomato egg 20 minutes","positive":"Tomato and Egg Stir Fry: tomato, egg; 15 minutes","negative":"Chocolate Cake: flour, sugar; 90 minutes"}
```

```powershell
& 'D:\CondaEnvs\myenv\python.exe' .\scripts\train_retriever.py
```

最终模型输出到 `training_outputs\retriever\final`。

### 文本 LLM LoRA

训练文件：`data\training\llm\train.jsonl`，每行需要 `messages` 数组。

```powershell
& 'D:\CondaEnvs\myenv\python.exe' .\scripts\train_llm_lora.py --model '<Hugging-Face模型ID或本地目录>'
```

输出是 `training_outputs\llm-lora\final-adapter`。PEFT adapter 不能自动作为 Ollama 模型使用；必须按所选架构完成合并、量化和兼容格式转换。

### 食材识别 VLM LoRA

训练文件：`data\training\vlm\train.jsonl`，每行需要 `images` 和多模态 `messages`。

```powershell
& 'D:\CondaEnvs\myenv\python.exe' .\scripts\train_vlm_lora.py --model '<兼容Transformers的VLM模型ID或本地目录>'
```

输出到 `training_outputs\vlm-lora\final-adapter`。运行时目前通过 Ollama 调用视觉模型，因此训练后仍需验证转换和导入兼容性。

### Diffusion LoRA

图像目录必须使用 ImageFolder 形式，并带有 `metadata.jsonl`：

```json
{"file_name":"dish001.jpg","text":"food photo of tomato and egg stir fry"}
```

```powershell
.\scripts\train-diffusion-lora.ps1 -Model '<Diffusers基础模型ID或本地目录>' -DatasetDirectory 'D:\path\to\imagefolder'
```

默认配置为 512px、batch size 1、梯度累积、梯度检查点和 FP16 LoRA，适配约 12 GB 显存；不同基础模型仍可能需要降低分辨率或调整显存策略。

## 正式训练前的最低要求

1. 固定 train/validation/test，并防止重复或近重复样本跨集合泄漏。
2. 保存数据来源、许可证、哈希、处理脚本版本、随机种子和训练参数。
3. 用少量样本先完成过拟合/冒烟测试。
4. 仅根据验证集选择配置，测试集只用于最终评估。
5. 为检索、LLM、VLM 和生成图片增加独立人工评估。
6. 不把“脚本能启动”描述为“模型已经训练或质量已经验证”。

当前状态是：环境和入口已准备，数据集与基础模型尚未下载，Windows 正式训练尚未开始。
