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

按实际发生的时间顺序写，包含每个决策的理由。

### 1. 选题

课程作业（见 `PracticeIntro/project-instructions.pdf`）要求做一个训练/微调模型的 ML 应用，带数据版本管理、实验跟踪、Git、Docker、CI/CD，还要有交互演示、保留一部分测试集。餐厅评论的方面级情感分析很合适：演示就是"输入评论、得到各维度情感"，保留测试集的需求也天然对应一个不参与评估的 `demo.csv`。

### 2. 本机环境

代码还没写，机器先出问题了。机器上有五个 Python（Microsoft Store 3.11、`C:\Python312`、Anaconda、3.8、VS 自带的 3.9），共用一个 user site-packages，还残留了中断的 `pip` 升级留下的 `~umpy`/`~ip`/`~crypt` 文件夹，`import sklearn` 报 `numpy.core.multiarray failed to import`。我把环境统一到 `C:\Python312`，删掉 `~` 开头的残留，重装 numpy。这步比预期花的时间长，也决定了后面全程用项目独立 `.venv`。

### 3. 数据：从英文换到中文

一开始用英文 SemEval-2014 餐厅评论。两个需求逼着我改：

- 应用要输出**四个固定维度**（口味/服务/价格/环境），所以从"方面词级"改成了"方面类别级"标注。
- 界面要双语、要支持中文输入，所以需要中文数据集。

MAMS（中科院深圳先进院）是中文 ABSA 的标准数据集，但语料在 Google Drive 上，不好下载。**ASAP**（美团点评）更合适：中文、挂在 GitHub 上、约 46,850 条、18 个方面类别正好能归并成四个维度，比 SemEval 大十倍左右。中文按字符分词——快、不依赖词典、词表小。

### 4. 模型：TF-IDF → LSTM → BERT/RoBERTa

先上 TF-IDF + LR。它的置信度只有 ~0.45，后来发现这是"诚实"的：因为"中性"是个大杂烩类。去掉中性、改成二分类（正面/负面）后，macro-F1 和置信度都实实在在涨了。试过校准、硬拉置信度，只会让数字好看却拉低 F1，就没用。

接着想用深度模型超过它。我的笔记本没有 NVIDIA 显卡（只有 Intel 核显），CPU 上微调 transformer 要几个小时，所以租了 **AutoDL**（RTX 3080 Ti，按小时计费）。先在本机试了 BiLSTM——数据不够，效果不行。在 AutoDL 上微调了 BERT（`bert-base-chinese`）和 RoBERTa（`chinese-roberta-wwm-ext`）。

结果：BERT/RoBERTa 在多维度混合的句子上超过 TF-IDF，但不是全面领先，而且 CPU 上很慢。所以**三个模型都保留**，用下拉框切换——TF-IDF 作为默认（快），BERT/RoBERTa 作为精度优先的选项。

### 5. DVC：本地目录 → Azure Blob

一开始没有 Azure 账号，先用本地目录模拟远端。课程指南（`7. DVC-with-Azure-Blob-Storage.pdf`）默认你有 Azure。后来拿到 Azure 学生账号（EFREI 邮箱，$100 额度），建了存储账户和 blob 容器，把远端切到 Azure Blob。第一次 `dvc push` 大文件报 `Timeout on reading data from socket`——是国内访问 Azure 的间歇性网络问题，重试几次就好了。

### 6. MLflow + DagsHub

按课程的 MLflow 指南（`15-MLFlow.pdf`），先用本地 tracking，再把 MLflow 指到 DagsHub。这暴露了一个版本冲突：MLflow 3.x 用了 `CreateLoggedModel` 端点，DagsHub 的 2.x 服务器不支持（`INVALID_PARAMETER_VALUE`），于是锁了 `mlflow<3`。现在 run 和注册的模型都落在 DagsHub 上。

### 7. 应用功能迭代

它从单个 `/predict` 端点一路长成：4 维度输出、双语界面、模型选择、CSV 批量导入导出、保存记录增删改查、最后拆成两个页面（分析 + 历史）。期间踩过一个坑：Python 三引号 HTML 字符串里的 `'\n'` 变成了真实换行，把生成的 JS 弄断了、所有按钮失灵——改用 `String.fromCharCode(10)` 解决。

### 8. CI/CD

按课程指南（`3-1. GITHUB_ACTIONS_GUIDE.pdf`）配 GitHub Actions：向受保护分支发 PR 会跑 ruff + pytest + Docker 构建；推 `staging`/`main` 会发布镜像。Docker 镜像是 `python:3.12-slim`，只装运行时依赖——torch/transformers 懒加载，镜像不用带 ~2 GB 的深度学习栈。

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
