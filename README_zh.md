# 方面级情感分析

> [English README](README.md)

一个 Web 应用：输入一条中文餐厅评论，对 **口味 / 服务 / 价格 / 环境** 四个维度分别判断情感（正面 / 负面 / 中性）。

这最初是 DevOps & MLOps 课程的期末项目，最后做成了一个完整的 MLOps 小流水线：DVC 管数据、MLflow 管实验、Docker + GitHub Actions 做 CI/CD，FastAPI 应用带中英双语界面、三个可选模型、CSV 批量导入导出、以及保存结果的增删改查。

## 应用功能

- 两个页面：`/`（分析）和 `/history`（历史记录）。
- 输入一条评论 → 四个维度各给标签 + 置信度 + 概率条。
- 可选模型：TF-IDF + LR、BERT、RoBERTa。
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

## 环境配置

Python 3.12，项目独立 venv：

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements-ml.txt -r requirements-dev.txt
```

依赖按用途分成三个文件：

| 文件 | 用途 |
|------|------|
| `requirements.txt` | 仅运行时（fastapi、uvicorn、joblib、scikit-learn、numpy、pandas、python-multipart） |
| `requirements-ml.txt` | 训练 + 深度模型推理（mlflow<3、matplotlib、dagshub、torch、transformers） |
| `requirements-dev.txt` | pytest、httpx、ruff |

连接 DagsHub 的环境变量（token 不进 git）：

| 变量 | 含义 |
|------|------|
| `DAGSHUB_REPO_OWNER` / `DAGSHUB_REPO_NAME` | DagsHub 仓库，如 `losproeocl` / `WUT-DevOps-Course` |
| `MLFLOW_TRACKING_USERNAME` / `MLFLOW_TRACKING_PASSWORD` | DagsHub 用户名 / access token |

## 数据

用的是 **ASAP**（Meituan-Dianping/asap）数据集：约 46,850 条中文餐厅评论，每条标注了 18 个细粒度维度。`ml/aspects.py` 把它们归并成四个粗维度：

| 维度 | ASAP 类别 |
|------|-----------|
| 口味 | Food#Portion、Food#Taste、Food#Appearance、Food#Recommend |
| 服务 | Service#Queue、Service#Hospitality、Service#Parking、Service#Timely |
| 价格 | Price#Level、Price#Cost_effective、Price#Discount |
| 环境 | Ambience#Decoration、Ambience#Noise、Ambience#Space、Ambience#Sanitary |

情感取值 `1`/`0`/`-1`（`-2` 表示"未提及"，直接丢弃）。中文按字符分词——快、不依赖词典、词表小。

DVC 跟踪 `data/raw` 和 `data/processed`，远端是 Azure Blob：

```bash
dvc remote add -d myazure azure://efreiwut-projdvc
dvc remote modify myazure account_name efreiwut2026dvc
dvc remote modify --local myazure connection_string "<密钥>"   # 写入 .dvc/config.local，已 gitignore
dvc push
```

处理后的数据有两个版本：`v1`（原始文本）和 `v2`（字符分词 + 去重）。

## 模型与训练

试过三个模型。任务是每个维度做二分类（正面 vs 负面）；训练时丢掉模糊的"中性"类，推理时置信度低于阈值就标为中性。

| 模型 | 训练位置 | macro-F1（口味/服务/价格/环境） |
|------|----------|------------------------------|
| TF-IDF + LR（tuned） | CPU，`ml/train.py` | 0.738 / 0.784 / 0.786 / 0.760 |
| BiLSTM | CPU，`ml/train_lstm.py` | 在这份数据上偏弱 |
| BERT（bert-base-chinese，3 epoch） | AutoDL GPU，`ml/train_bert.py` | 0.758 / 0.806 / 0.758 / 0.824 |
| RoBERTa（chinese-wwm-ext，3 epoch） | AutoDL GPU | 0.765 / 0.803 / 0.763 / 0.789 |

BERT/RoBERTa 是在 AutoDL 的 RTX 3080 Ti 上微调的。TF-IDF + LR 保留为默认模型，因为 CPU 上秒出结果且效果接近；BERT 在多维度混合的句子上更准。

训练命令：

```bash
python -m ml.data_pipeline              # 生成 v1/v2 CSV
python -m ml.train --data-version v2 --mode tuned   # TF-IDF + LR，写 MLflow
python -m ml.train_lstm --data-version v2           # BiLSTM
python -m ml.train_bert --data-dir data --epochs 3  # BERT/RoBERTa（建议 GPU）
```

## 实验与模型注册

MLflow 记录每次运行（git SHA、数据校验和、超参、各维度指标）并注册模型。设了上面的环境变量就写到 DagsHub，否则写到本地 `mlruns/`。DagsHub 上注册的模型：

`absa_restaurant`（统一 TF-IDF+LR）、`absa_restaurant_lstm`、`absa_restaurant_bert`、`absa_restaurant_roberta`。

注意：DagsHub 的 MLflow 服务器是 2.x，客户端必须 `mlflow<3`。

## CI/CD 与 Docker

`.github/workflows/ci.yml`：

- 向 `dev`/`staging`/`main`/`finalProject_sentimentAnalysis` 发 PR：ruff + pytest + docker build。
- 推 `staging`：发布 `:staging` 镜像；推 `main`：发布 `:latest`。

`Dockerfile` 是 `python:3.12-slim`，只装运行时依赖。torch/transformers 是懒加载，所以镜像不用带 ~2 GB 的深度学习栈就能跑 TF-IDF 模型。

## 踩过的坑和解决办法

1. **多个 Python 安装导致 numpy/scipy 冲突。** 机器上有五个 Python 共用一个 user site-packages，一次中断的 `pip` 升级还留下了 `~umpy`/`~ip`/`~crypt` 文件夹，`import sklearn` 报 `numpy.core.multiarray failed to import`。解决：选定 C:\Python312，删掉 `~` 开头的残留，重装 numpy。

2. **置信度没意义。** 一开始的三分类模型置信度只有 ~0.45，因为"中性"是个大杂烩类。去掉中性改成二分类后，macro-F1 和置信度都实实在在上来了——试过校准、硬拉置信度，只会虚高却拉低 F1，就没用。

3. **数据量卡住了模型上限。** 英文 SemEval（~3k 条）太小，任何深度模型都发挥不出来。换成 ASAP（~46,850 条中文评论），光是"价格"就从 ~400 条涨到 ~39k 条。

4. **MLflow 3.x 连不上 DagsHub。** `CreateLoggedModel` 返回 `INVALID_PARAMETER_VALUE`，因为 DagsHub 服务器是 2.x。解决：锁 `mlflow<3`。

5. **huggingface_hub + httpx2 下载 bug。** 在 AutoDL 上 `AutoTokenizer.from_pretrained` 报 `process() takes no keyword arguments`。绕过：用 `wget` 从 hf-mirror 下载模型文件，从本地路径加载。

6. **中文下 TF-IDF 特征为空。** 默认 `token_pattern=\b\w\w+\b` 会过滤单个 CJK 字符。改成 `token_pattern=r"\S+"`。

7. **整个页面 JS 突然全失灵。** Python 三引号 HTML 字符串里的 `'\n'` 变成了真实换行，把 `buffer.indexOf('...')` 弄断了。解决：改用 `String.fromCharCode(10)`。

8. **400 MB 权重不该进 git。** BERT/RoBERTa 的 state dict 各约 440 MB，已 gitignore（LSTM 用 DVC 跟踪）；TF-IDF 模型（~30 MB）直接提交方便 Docker 用。

9. **epoch 越多反而越差。** RoBERTa 跑 5 个 epoch 过拟合（train loss 0.12，测试 F1 反而降）。这数据集上 3 个 epoch 是甜点。

10. **国内推 Azure 超时。** 第一次 `dvc push` 大文件报 `Timeout on reading data from socket`。是间歇性的，重试几次就推完了。

## 运行

```bash
python -m uvicorn app.main:app --reload      # 或：python -m app.main
# http://127.0.0.1:8000  （分析）  /history（历史记录）

docker build -t absa-app .
docker run -p 8000:8000 absa-app
```

测试：`python -m pytest`；lint：`ruff check app ml tests scripts`。
