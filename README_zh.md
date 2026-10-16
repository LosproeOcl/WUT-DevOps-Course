# 方面级情感分析

> [English README](README.md)

一个 Web 应用：输入一条中文餐厅评论，对 **口味 / 服务 / 价格 / 环境** 四个维度分别判断情感（正面 / 负面 / 中性）。

这是 DevOps & MLOps 课程的期末项目，最后做成了一个端到端的 MLOps 小流水线：DVC 管数据、MLflow 管实验、Docker + GitHub Actions 做 CI/CD，FastAPI 应用带中英双语界面、三个可选模型、CSV 批量导入导出、以及保存结果的增删改查。

## 应用功能

- 两个页面：`/`（分析）和 `/history`（历史记录）。
- 输入一条评论 → 四个维度各给标签 + 置信度 + 概率条。
- 三个模型可选：TF-IDF + LR、BERT、RoBERTa。
- 上传 CSV → 逐条批量分析、结果入库、下载带原列 + 情感/置信度/概率列的 CSV。
- 保存的结果存 SQLite，在 `/history` 页查看、编辑、单条/批量删除、导出 CSV。
- 界面支持中英文切换。

## 目录结构

```
app/                 FastAPI 应用
  main.py            路由 + 两个 HTML 页面
  model.py           模型加载与推理（tfidf / bert / roberta）
  database.py        保存记录的 SQLite 层
  schemas.py         Pydantic 模型
ml/                  训练与数据代码
  data_pipeline.py   ASAP CSV -> (text, aspect, polarity) 行，v1/v2
  train.py           TF-IDF + LR，日志进 MLflow
  train_lstm.py      BiLSTM（PyTorch）
  train_bert.py      BERT/RoBERTa 微调
  aspects.py         维度映射 + 分词
data/                raw/ processed/（DVC）、demo.csv
models/              训练权重（tfidf 入库；bert/roberta/lstm 已忽略）
tests/               pytest 单元 + 接口测试
.github/workflows/ci.yml
Dockerfile
```

## 开发历程

这是塑造了整个项目的一系列决策和弯路，按发生顺序记录。

课程作业要求的是一个训练或微调过模型的 ML 应用，带数据版本管理、实验跟踪、Git、Docker 和 CI/CD，还要有交互演示、保留一部分测试集。餐厅评论的方面级情感分析正好对上这份要求：演示本身很直观——输入一条评论，得到各维度的情感；保留测试集的需求也顺理成章地退化成一个小型的、不参与评估的 `demo.csv`。选它是因为合适，而不是因为任务有多新。

正式写代码之前，得先修机器。机器上同时装着五个 Python，共用一个 user site-packages，还残留着一次中断的 `pip` 升级留下的 `~umpy`、`~ip`、`~crypt` 文件夹，`import sklearn` 直接报 `numpy.core.multiarray failed to import`。把环境统一到 `C:\Python312`、删掉残留、重装 numpy，这件事花了比预期更多的时间，也决定了后面所有工作都放在项目独立的 `.venv` 里，不再碰全局环境。

数据集换过两次。最初用英文 SemEval-2014 餐厅评论，两个需求让它维持不下去：一是应用要输出四个固定维度，标注就得从"方面词"改成"方面类别"；二是界面要双语、要支持中文。MAMS 是中文 ABSA 的标准语料，但挂在 Google Drive 上，下载不顺。美团点评的 ASAP 更合适——中文、在 GitHub 上、约 46,850 条、18 个方面类别正好能归并成四个维度，比 SemEval 大一个量级。中文按字符切分，省掉了词典依赖。

模型是改动最多的部分。先上 TF-IDF + LR 做基线，0.45 左右的置信度不是校准问题，而是"中性"这个类太模糊、成了大杂烩；去掉它改成二分类之后，macro-F1 和置信度才真正上去。再想用深度模型超过这个基线，就需要 GPU，而笔记本没有，于是租了 AutoDL。CPU 上的 BiLSTM 因为数据不够没跑出名堂，在 AutoDL 上微调 BERT 和 RoBERTa 才见效。它们在多维度混合的句子上确实更好，但不是全面领先，而且 CPU 推理慢，所以三个模型都留了下来，运行时切换，TF-IDF 当默认。

DVC 的远端搬过一次。一开始没有 Azure 账号，先用本地目录顶着。拿到 Azure 学生账号之后，建了存储账户和容器，把远端切到 Azure Blob。第一次 push 大文件时报 socket 超时，是国内访问 Azure 的间歇性问题，重试就过了。

实验跟踪按课程的 MLflow 指南走，先本地、再 DagsHub。这一步踩到一个版本冲突：MLflow 3.x 调的 `CreateLoggedModel` 端点在 DagsHub 的 2.x 服务器上不存在，最后把客户端锁在 `mlflow<3`。

应用本身从单个 `/predict` 端点一点点长起来：四维度输出、双语界面、模型选择、CSV 批量导入导出、保存记录增删改查，最后拆成分析和历史两个页面。最烦人的一个 bug 是 Python 三引号字符串里的 `'\n'` 在生成的 JS 里变成了真实换行，整页按钮全部失灵，最后用 `String.fromCharCode` 绕开。

CI/CD 用 GitHub Actions，按课程指南配：发 PR 跑 ruff、pytest 和 Docker 构建，推 staging/main 发布镜像。镜像是 `python:3.12-slim`，只带运行时依赖——torch 和 transformers 懒加载，避免把两 GB 的深度学习栈塞进镜像。

## 环境配置

Python 3.12，项目独立 venv：

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-ml.txt -r requirements-dev.txt
```

| 文件 | 用途 |
|------|------|
| `requirements.txt` | 运行时（fastapi、uvicorn、joblib、scikit-learn、numpy、pandas、python-multipart） |
| `requirements-ml.txt` | 训练 + 深度模型推理（mlflow<3、matplotlib、dagshub、torch、transformers） |
| `requirements-dev.txt` | pytest、httpx、ruff |

环境变量（token 不进 git）：

| 变量 | 含义 |
|------|------|
| `DAGSHUB_REPO_OWNER` / `DAGSHUB_REPO_NAME` | DagsHub 仓库，如 `losproeocl` / `WUT-DevOps-Course` |
| `MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD` | DagsHub 用户名 / access token |
| `REVIEWS_DB_PATH` | 可选；保存记录的 SQLite 路径 |
| `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` | GitHub Actions 发布镜像用的 secret |

## 数据

ASAP（Meituan-Dianping/asap），约 46,850 条中文评论，18 个方面类别归并成四个：

| 维度 | ASAP 类别 |
|------|-----------|
| 口味 | Food#Portion、Food#Taste、Food#Appearance、Food#Recommend |
| 服务 | Service#Queue、Service#Hospitality、Service#Parking、Service#Timely |
| 价格 | Price#Level、Price#Cost_effective、Price#Discount |
| 环境 | Ambience#Decoration、Ambience#Noise、Ambience#Space、Ambience#Sanitary |

情感取值 `1`/`0`/`-1`（`-2` = 未提及，丢弃）。DVC 跟踪 `data/raw` 和 `data/processed`，远端是 Azure Blob：

```bash
dvc remote add -d myazure azure://efreiwut-projdvc
dvc remote modify myazure account_name efreiwut2026dvc
dvc remote modify --local myazure connection_string "<密钥>"   # .dvc/config.local，已 gitignore
dvc push
```

两个版本：`v1`（原始）和 `v2`（字符分词 + 去重）。

## 模型与训练

每个维度做二分类（正面 vs 负面）；训练时丢掉"中性"类，低置信度的预测标为中性。

| 模型 | 训练位置 | macro-F1（口味/服务/价格/环境） |
|------|----------|------------------------------|
| TF-IDF + LR（tuned） | CPU，`ml/train.py` | 0.738 / 0.784 / 0.786 / 0.760 |
| BiLSTM | CPU，`ml/train_lstm.py` | 这份数据上偏弱 |
| BERT（bert-base-chinese，3 epoch） | AutoDL GPU，`ml/train_bert.py` | 0.758 / 0.806 / 0.758 / 0.824 |
| RoBERTa（chinese-wwm-ext，3 epoch） | AutoDL GPU | 0.765 / 0.803 / 0.763 / 0.789 |

```bash
python -m ml.data_pipeline              # 生成 v1/v2 CSV
python -m ml.train --data-version v2 --mode tuned   # TF-IDF + LR，写 MLflow
python -m ml.train_lstm --data-version v2           # BiLSTM
python -m ml.train_bert --data-dir data --epochs 3  # BERT/RoBERTa（建议 GPU）
```

DagsHub 上注册：`absa_restaurant`（统一 TF-IDF+LR）、`absa_restaurant_lstm`、`absa_restaurant_bert`、`absa_restaurant_roberta`。

## 课程要求对照

| 要求（来自 `project-instructions.pdf`） | 对应实现 |
|----------------------------------------|----------|
| 训练/微调模型 | GPU 上微调 BERT/RoBERTa |
| 数据集多版本 | ASAP，DVC `v1`/`v2` |
| 3+ 个带边界用例的测试 | 33 个 pytest 测试（单元 + 接口） |
| Git 分支（main/staging/dev） | 外加 `finalProject_sentimentAnalysis` |
| Docker（精简 Dockerfile + .dockerignore） | `python:3.12-slim`、`.dockerignore` |
| CI/CD（PR 跑 test+lint+docker build、部署） | `.github/workflows/ci.yml` |
| DVC（Azure 远端、2+ 版本） | Azure Blob、`v1`/`v2` |
| MLflow（2+ 实验、模型注册） | baseline vs tuned；DagsHub 模型注册 |
| 交互应用 + 保留测试集 | `data/demo.csv`，不参与评估 |

## 踩坑速查

- `numpy.core.multiarray failed to import` → 多个 Python 共用 user site + `~` 残留；统一到 C:\Python312 并删掉。
- 置信度 ~0.45 → "中性"是大杂烩类；改二分类。
- 数据量限制模型 → 换 ASAP（大十倍）。
- `CreateLoggedModel` → `INVALID_PARAMETER_VALUE` → 锁 `mlflow<3`（DagsHub 服务器是 2.x）。
- AutoDL 上 `process() takes no keyword arguments` → 用 `wget` 从 hf-mirror 下模型，从本地路径加载。
- 中文下 TF-IDF 特征为空 → `token_pattern=r"\S+"`（默认会过滤单个 CJK 字符）。
- JS 按钮失灵 → 三引号 HTML 里的 `'\n'` 变成真实换行；用 `String.fromCharCode(10)`。
- 400 MB 权重 → gitignore（LSTM 走 DVC；TF-IDF ~30 MB 直接提交）。
- 5 epoch 过拟合 → 3 个最合适。
- Azure 推送超时 → 间歇性，重试。

## 运行

```bash
python -m uvicorn app.main:app --reload      # 或：python -m app.main
# http://127.0.0.1:8000 （分析）  /history（历史记录）

docker build -t absa-app .
docker run -p 8000:8000 absa-app
```

测试：`python -m pytest`；lint：`ruff check app ml tests scripts`。
