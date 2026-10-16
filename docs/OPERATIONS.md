# 项目操作指南（Operations Guide）

本文档完整记录本项目（方面级情感分析 App）从搭建、数据处理、模型训练（含 GPU）、到
DagsHub/GitHub 发布的全流程配置信息。

- 仓库（GitHub）：https://github.com/LosproeOcl/WUT-DevOps-Course （分支 `finalProject_sentimentAnalysis`）
- 仓库（DagsHub）：https://dagshub.com/losproeocl/WUT-DevOps-Course
- MLflow Tracking：`https://dagshub.com/losproeocl/WUT-DevOps-Course.mlflow`

---

## 1. 项目概述

| 项 | 说明 |
|---|---|
| 任务 | 方面级情感分析（Aspect-Category Sentiment） |
| 输入 | 一条餐厅评论 |
| 输出 | 口味 / 服务 / 价格 / 环境 四个方面的正负情感 + 置信度 |
| 数据集 | 美团 ASAP 中文评论（4.6 万条，18 方面 → 映射 4 方面） |
| 模型 | TF-IDF+LR（生产）、BiLSTM、BERT/RoBERTa（GPU） |
| 前端 | FastAPI + 单页 HTML（中英双语切换） |

---

## 2. 环境与依赖

### 2.1 本地 Python 环境

项目使用专属虚拟环境 `.venv`（基于 Python 3.12）：

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
python -m pip install -r requirements-ml.txt -r requirements-dev.txt
```

依赖分三档：

| 文件 | 用途 |
|---|---|
| `requirements.txt` | 运行/推理依赖（fastapi、uvicorn、joblib、scikit-learn、numpy、pandas） |
| `requirements-ml.txt` | 训练依赖（mlflow<3、matplotlib、dagshub、torch） |
| `requirements-dev.txt` | 测试/lint（pytest、httpx、ruff） |

> 注意：`mlflow<3` 是因为 DagsHub 的 MLflow 服务器基于 2.x，MLflow 3.x 的
> `CreateLoggedModel` 端点与之不兼容（`INVALID_PARAMETER_VALUE`）。

### 2.2 环境变量（.env）

训练脚本通过环境变量连接 DagsHub MLflow（**不要把 token 提交到 git**）：

| 变量 | 说明 | 示例 |
|---|---|---|
| `DAGSHUB_REPO_OWNER` | DagsHub 用户名/组织 | `losproeocl` |
| `DAGSHUB_REPO_NAME` | DagsHub 仓库名 | `WUT-DevOps-Course` |
| `MLFLOW_TRACKING_USERNAME` | DagsHub 用户名 | `losproeocl` |
| `MLFLOW_TRACKING_PASSWORD` | DagsHub access token | `<token>`（保密） |

Windows PowerShell 设置示例：

```powershell
$env:DAGSHUB_REPO_OWNER = "losproeocl"
$env:DAGSHUB_REPO_NAME = "WUT-DevOps-Course"
$env:MLFLOW_TRACKING_USERNAME = "losproeocl"
$env:MLFLOW_TRACKING_PASSWORD = "你的token"
```

GitHub Actions 需要的 Secret（`Settings → Secrets → Actions`）：

| Secret | 用途 |
|---|---|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub 访问令牌 |

---

## 3. 数据版本控制（DVC）

### 3.1 远端配置

使用**本地目录**模拟远端（`dvc-remote/`，已 gitignore）：

```
.dvc/config:
  [core]
      remote = local
  ['remote "local"']
      url = ../dvc-remote
```

```bash
dvc add data/raw data/processed   # 生成 .dvc 指针
dvc push                          # 上传到 dvc-remote/
dvc pull                          # 拉取
```

> 之前的 Azure 远端（`azure://dvc`，account `wut2026`）已移除，改用本地目录。

### 3.2 数据版本

| 版本 | 文件 | 说明 |
|---|---|---|
| v1 | `data/processed/{train,val,test}_v1.csv` | 原始文本（未分词） |
| v2 | `data/processed/{train,val,test}_v2.csv` | 字级分词 + 去重 |

中文用**字级分词**（`" ".join(text)`），避免 jieba 分词慢的问题，且词表小、不易过拟合。

### 3.3 数据规模（ASAP，v2 展开后）

| 方面 | 行数 |
|---|---|
| food | 59,548 |
| service | 37,777 |
| price | 39,252 |
| ambience | 32,929 |

---

## 4. 实验跟踪（MLflow + DagsHub）

### 4.1 Tracking 配置

训练脚本 `ml/train.py` / `ml/train_lstm.py` 通过 `configure_tracking()` 决定目标：

- 设置了 `DAGSHUB_REPO_OWNER/NAME` → 用 `dagshub.init(..., mlflow=True)` 指向 DagsHub
- 否则用 `--tracking-uri` 或本地 `mlruns/`

实验名：`absa_restaurant_aspects`

### 4.2 每个 run 记录的内容

- **代码版本**：`git_sha`
- **数据版本**：`data_version` + `train_checksum`（MD5）
- **超参数**：`mode`、`epochs`、`embed_dim`、模型名等
- **指标**：各 aspect 的 `macro_f1`、`accuracy`、per-class F1
- **模型**：注册到 MLflow Model Registry

### 4.3 DagsHub 上注册的模型

| 模型名 | 类型 | 来源 |
|---|---|---|
| `absa_restaurant` | 统一 TF-IDF+LR（pyfunc） | 本地 CPU |
| `absa_restaurant_lstm` | BiLSTM（pyfunc） | 本地 CPU |
| `absa_restaurant_bert` | bert-base-chinese（3 epoch） | AutoDL GPU |
| `absa_restaurant_roberta` | chinese-roberta-wwm-ext（3 epoch） | AutoDL GPU |
| `absa_restaurant_{food,service,price,ambience}` | 4 个 TF-IDF+LR | 本地 CPU |

### 4.4 最终结果（macro-F1）

| 方面 | TF-IDF+LR(tuned) | BERT(3ep) | RoBERTa(3ep) |
|---|---|---|---|
| food | 0.738 | **0.758** | 0.765 |
| service | 0.784 | **0.806** | 0.803 |
| price | **0.786** | 0.758 | 0.763 |
| ambience | 0.760 | **0.824** | 0.789 |

结论：BERT 在 4 方面里 3 个反超；RoBERTa 与 BERT 打平；5 epoch 会过拟合（3 epoch 最佳）。

---

## 5. CI/CD（GitHub Actions）

工作流文件：`.github/workflows/ci.yml`

| 触发 | 分支 | 行为 |
|---|---|---|
| `pull_request` | dev/staging/main/finalProject_sentimentAnalysis | test + lint + docker build |
| `push` | 同上 | test + lint + docker build |
| `push` 到 `staging` | staging | + 发布 `:staging` 镜像 |
| `push` 到 `main` | main | + 发布 `:latest` 镜像 |

关键 action 版本：`actions/checkout@v7`、`actions/setup-python@v7`。

`test` job 步骤：checkout → setup-python 3.12 → `pip install -r requirements-dev.txt` →
`ruff check app ml tests scripts` → `python -m pytest` → `docker build`。

---

## 6. Git 分支策略

```
feature/* --PR--> dev --PR--> staging --PR--> main
```

本项目实际使用的分支：

| 分支 | 用途 |
|---|---|
| `main` | 生产（发布 `:latest`） |
| `staging` | 预发（发布 `:staging`） |
| `dev` | 开发集成分支 |
| `finalProject_sentimentAnalysis` | 本最终项目的开发/提交分支 |

---

## 7. Docker

`Dockerfile`（`python:3.12-slim` 推理镜像）只装运行依赖：

```bash
docker build -t absa-app .
docker run -p 8000:8000 absa-app
# 打开 http://127.0.0.1:8000
```

---

## 8. 忽略文件清单

### 8.1 `.gitignore`

```gitignore
__pycache__/  *.py[cod]  *.egg-info/
.venv/  venv/  env/
.pytest_cache/  .coverage  htmlcov/
.env  *.env
/mlruns/
/data/raw/  /data/processed/
/dvc-remote/
models/lstm.joblib
.idea/  .vscode/  .DS_Store  Thumbs.db
```

### 8.2 `.dockerignore`

```dockerignore
.git/  .venv/  __pycache__/  *.py[cod]
.pytest_cache/  .env
tests/  ml/  scripts/  .github/
data/raw/  data/processed/  mlruns/  .dvc/  *.dvc
models/lstm.joblib
*.md  .gitignore  .dockerignore  .dvcignore
```

### 8.3 `.dvcignore`

```gitignore
.venv/  __pycache__/  *.pyc  .git/
.pytest_cache/  mlruns/  .idea/  .vscode/
dvc-remote/
```

### 8.4 `.gitattributes`（换行统一）

```
* text=auto eol=lf
*.png binary
*.joblib binary
```

---

## 9. 完整操作流程记录（时间线）

### 阶段 1：环境统一（本地）
1. 修复了本机 5 个 Python 环境混用、共享用户目录导致的 numpy/scipy 冲突。
2. 清理 `~umpy`/`~ip`/`~crypt` 等 pip 中断残留。
3. 统一到 `C:\Python312`（numpy 2.5.4 + scipy 1.18.1）。

### 阶段 2：项目脚手架（本地）
1. 创建 `finalProject` 目录结构（`app/`、`ml/`、`data/`、`tests/`、`scripts/`）。
2. 编写 FastAPI app（4 方面输出 + 中英双语 UI）、DVC、MLflow 训练脚本。
3. Git 分支：`main`/`staging`/`dev`；初始提交。

### 阶段 3：数据演进
1. 英文 SemEval-2014 餐厅（方面词级）→ 3 分类。
2. 改为二分类（正/负，去掉模糊的"中性"类）→ 置信度与 F1 提升。
3. 换 MAMS-ACSA（英文，方面类别）→ 4 方面。
4. 最终换 **美团 ASAP 中文数据集**（4.6 万条，18 方面 → 4 方面）。

### 阶段 4：模型演进
1. TF-IDF+LR（CPU，生产模型）。
2. BiLSTM（CPU，小数据时不如 TF-IDF+LR）。
3. BERT/RoBERTa（AutoDL GPU，最终反超 TF-IDF+LR）。

### 阶段 5：DagsHub 集成
1. `dagshub.init(mlflow=True)` 连接 DagsHub。
2. 修复 MLflow 3.x 与 DagsHub 2.x 的 `CreateLoggedModel` 不兼容（降级 `mlflow<3`）。
3. 注册 6 个模型到 MLflow Model Registry。

### 阶段 6：GPU 训练（AutoDL）
1. 连接 AutoDL（RTX 3080 Ti 12GB）。
2. 上传 ASAP 数据 + BERT 脚本。
3. 修复 `huggingface_hub`/`httpx2` 版本 bug（手动 wget 下载模型）。
4. 训练 bert-base-chinese / chinese-roberta-wwm-ext。
5. 注册 `absa_restaurant_bert` / `absa_restaurant_roberta`。

---

## 10. 常见问题排查

| 问题 | 解决 |
|---|---|
| MLflow 注册报 `INVALID_PARAMETER_VALUE` | 降级 `mlflow<3`（DagsHub 服务器是 2.x） |
| `huggingface_hub` 下载报 `process() takes no keyword arguments` | httpx2 版本 bug，手动 wget 下载模型 |
| 中文 TF-IDF 特征为空 | TF-IDF 默认 `token_pattern` 过滤单字，改 `token_pattern=r"\S+"` |
| 置信度低 | 三分类改二分类；或数据量不足（换更大数据集） |
| DagsHub `dagshub.init` 报 OAuth 错误 | 无缓存 token，改直接设 `mlflow.set_tracking_uri` + 环境变量 |
