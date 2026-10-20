# 依赖部署与启动

本文提供项目依赖的参考配置与历史验证记录。新环境需自行部署并验证，仓库不包含任何现有机器的配置、服务状态或模型权重。

## 参考服务配置

- Milvus 2.6.0：`http://127.0.0.1:19530`；健康接口 `http://127.0.0.1:9091/healthz`。
- Neo4j 5.26 Community：`bolt://127.0.0.1:7687`；管理界面 `http://127.0.0.1:7474`。用户名 neo4j，密码保存在项目 `.env`。
- MinerU 3.4.5：`http://127.0.0.1:8001`，使用 CPU pipeline，保留项目需要的 `/file_parse` 接口。
- Embedding：BAAI/bge-m3，1024 维，`http://127.0.0.1:8002/v1`。
- Reranker：BAAI/bge-reranker-v2-m3，`http://127.0.0.1:8003`。

依赖 Compose 使用 TEI 镜像和本地 float16 Safetensors 权重。部署时应选择与自己的硬件兼容的镜像，并将所需权重放入下述相对目录。半精度与 float32 可能存在数值差异，业务质量需另行评测。

LLM 通过 OpenAI-compatible 接口配置，例如 DeepSeek。请在自己的 `.env` 中设置服务地址、可用模型和密钥；本文不提供实际环境配置。

## 项目内相对目录

- `.runtime/mineru-venv/`：单独安装的 MinerU Python 环境。
- `.runtime/mineru/`：MinerU 模型、配置、输出和缓存。
- `.runtime/tei-models/embedding-fp16/`、`.runtime/tei-models/reranker-fp16/`：依赖 Compose 只读挂载的模型目录。
- `.runtime/tmp/`：启动脚本使用的临时目录。

这些目录不在版本库中，首次部署需要自行准备。Docker 数据目录和资源配额由部署者根据环境配置；不要把 `.runtime/` 误当成可以随意删除的缓存。

## 后续启动

先启动 Docker Desktop，确认 Linux 引擎可用。在项目根目录执行：

```powershell
docker compose -f compose.dependencies.yaml up -d
powershell -ExecutionPolicy Bypass -File scripts/start_mineru.ps1
```

实际部署使用 `compose.dependencies.yaml`，不需要启动另一份 PostgreSQL，也不要用旧文档的 `docker run` 示例重复创建服务。
MinerU 脚本后台启动服务并使用项目内相对缓存、配置、输出路径，使用已下载的本地模型；若 8001 已监听会拒绝重复启动。
API/Worker 如已运行，需要重启以读取更新后的 `.env`。

日志和状态：

```powershell
docker compose -f compose.dependencies.yaml ps
docker compose -f compose.dependencies.yaml logs --tail 50 embedding reranker milvus neo4j
Get-Content .runtime/mineru.stderr.log -Tail 30
```

Milvus/Neo4j 设置为 unless-stopped；模型容器失败最多重试三次。重新开机后执行上述启动命令。Neo4j 配置 256MB heap、128MB page cache；两个 TEI 容器分别限制 3GB 内存、并发 4。首次启动需等待健康接口返回 200。

## 验证结果

- 项目 `ModelClient` 成功生成两条 1024 维向量。
- 真实 Reranker 将退款规则排在无关会议文本之前，示例分数约 0.5003 与 0.0000162。
- `tests/test_external_services.py` 启用两项真实集成开关后：**2 passed in 5.07s**。覆盖 Milvus/Neo4j 写入、召回、租户隔离、删除，以及 MinerU 单页 PDF 解析。
- 真实测试发现 PyMilvus 返回的是自定义主键 chunk_id；已修正 `app/adapters/stores.py` 使用请求返回的 `entity.chunk_id`，重跑通过。
- MinerU 的上游 pipeline 依赖缺少 six，已补装。安装版本清单在 `.runtime/mineru-requirements.lock`。

复验命令（会写入并清理随机生成的测试数据）：

```powershell
$env:RUN_EXTERNAL_INTEGRATION='1'
$env:RUN_MINERU_INTEGRATION='1'
.\.venv\Scripts\python.exe -m pytest tests/test_external_services.py -q -p no:cacheprovider
```

记录保存在 `.runtime/models-validation.log`、`.runtime/dependencies-validation.log`。

## 资源与端口

按自己的模型大小、并发量和硬件设置资源上限。启动前核对 Compose 端口是否被其他应用占用，按需调整映射；不要停止不属于本项目的服务。

## 导入与问答还需满足的条件

这些验证证明依赖及其适配已可用，不代表完整业务验收完成。上传后的处理还需要运行 Worker：

```powershell
$demo = Get-Content .runtime/demo.json | ConvertFrom-Json
.\.venv\Scripts\python.exe -m app.worker --tenant $demo.tenant_id
```

当前 `DEVELOPMENT_SKIP_SCANNER=false`，没有配置扫描器会拒绝处理文件。生产按 `docs/ingestion_pipeline.md` 部署 SCANNER_URL；仅本地可信文件调试可显式同时设置 `ENVIRONMENT=development` 和 `DEVELOPMENT_SKIP_SCANNER=true`。本次未更改扫描策略。Office 转 PDF 还需要 Worker 所在机器安装 LibreOffice。

## 官方参考

- [TEI 支持的显卡与镜像](https://huggingface.co/docs/text-embeddings-inference/supported_models)
- [MinerU 旧版接口说明](https://opendatalab.github.io/MinerU/usage/compatibility/)
- [WSL 内存与交换文件配置](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)
- [DeepSeek 官方 API](https://api-docs.deepseek.com/zh-cn/)
