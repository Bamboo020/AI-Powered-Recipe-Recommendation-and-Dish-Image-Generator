# 本机 AI 配置记录

日期：2026-11-17。Apple M4，16GB 统一内存，Python 3.13。复用已有模型，未下载新的大模型。

| 服务 | 本机配置 | 实测 |
| --- | --- | --- |
| 语义向量 | Ollama `nomic-embed-text:latest` | 推荐返回 hybrid_semantic_v1；首次约 1.98 秒 |
| LLM | Ollama `qwen2.5:7b` | 返回真实中文说明，约 15.38 秒 |
| Diffusion | 本地 Stable Diffusion 1.5 缓存，MPS、20 步、guidance 7.5、512px | 首次成功保存 PNG，含导入/加载约 90.53 秒，采样约 29 秒 |
| CNN | 未配置 | 缺少匹配类别顺序的训练权重；不输出随机预测 |

以上是单次功能验证，不是性能基准或质量评估。首次图片偏离炒饭外观，因而为演示记录增加了英文菜品视觉描述；调整后第二次生成耗时约 32.55 秒（采样约 21 秒），仍需人工核对生成内容。

## 启动

根目录 `.env` 已写入本机实际路径且由 Git 忽略。服务器启动时自动加载；Shell 环境变量优先。

```sh
# 终端 1：若 Ollama 尚未运行
ollama serve
# 终端 2：项目根目录
sh scripts/start-backend.sh
# 终端 3
cd frontend
npm ci
npm run dev
```

浏览器：http://127.0.0.1:5173 。后端状态：http://127.0.0.1:8000/api/health 。

服务端 `.env` 包含 `OLLAMA_EMBED_MODEL`、`OLLAMA_MODEL`、`DIFFUSION_MODEL`、`AI_DEVICE=mps` 等本机设置。其他机器参考 `.env.example`，自行指定模型目录与算力，不能直接复制本机缓存路径。

## 限制与下一步

- 食谱库仍只有六条带明确来源标注的演示记录；真实数据导入尚未完成。
- nomic 是本机现有的功能基线；中文检索质量尚未评估，可换多语言 SentenceTransformer。
- LLM 与 Diffusion 是预训练模型推理，未自行训练；LLM 文字仍需核对。
- 图像生成是同步单图接口，没有持久化任务队列与取消功能。
- Ollama 请求结束卸载模型，Diffusion 默认在生成后释放缓存权重，以降低统一内存压力。
- CNN 推理适配器存在，但需要可信的 ResNet18 食物分类 state_dict、对应的有序类别 JSON 和评估记录，之后再配置 `CNN_CHECKPOINT` 与 `CNN_LABELS_PATH`。
- 完整依赖快照在 `backend/requirements-local-ai.lock.txt`，对应本机环境；基础 CI 仍使用独立的轻量依赖。

整体结构见 [系统架构](system-architecture.zh.md)。原始实测响应保存在忽略目录 `output/local-ai-smoke.json`，生成图片位于忽略目录 `generated/`。
