# DevOps & MLOps 课程记录

- 机器：Windows 11（Build 10.0.26200）
- 用户：yqysperiod\19284

## 一、环境

| 组件 | 版本 | 状态 |
|---|---|---|
| Python | 3.12.0 | ✅ |
| Git | 2.55.0.windows.5 | ✅ |
| Docker Desktop | 4.94.0（Engine 29.8.2，WSL2 后端） | ✅ |
| JupyterLab | 4.6.4 | ✅ |
| MLflow | 3.17.0 | ✅ |
| DVC | 3.67.1 | ✅ |
| Flask | 3.1.3 | ✅ |
| FastAPI / uvicorn | 0.136.3 / 0.48.0 | ✅ |
| scikit-learn | 1.9.1 | ✅ |
| GitHub | LosproeOcl（gh CLI 2.100.0） | ✅ |
| DagsHub | losproeocl | ✅ |
| Azure | 学生账号（$100 额度，Blob 存储） | ✅ |

## 二、目录结构

```
Devops&MLOps/
├── finalProject/        # 期末项目（独立分支 finalProject_sentimentAnalysis）
├── LearningDoc/         # 学习文档
├── Config/              # 环境配置（logs/、scripts/）
├── Note/                # 课堂笔记
├── PracticeIntro/       # 练习指南（PDF，含中文版）
├── PowerPoint/          # 课件
├── Quiz_recap/          # 测验回顾
├── cars-crud/           # 练习项目（独立分支 cars-crud）
├── git-playground/      # 练习项目（独立分支）
└── data/                # DVC 数据
```

## 三、期末项目

**方面级情感分析**（`finalProject/`，分支 `finalProject_sentimentAnalysis`）

- 输入中文餐厅评论，输出口味 / 服务 / 价格 / 环境四个维度的正负情感
- FastAPI 应用：分析 + 历史两个页面，中英双语界面
- 三个可选模型：TF-IDF + LR（默认）、BERT、RoBERTa
- CSV 批量导入导出、保存记录 CRUD（SQLite）
- DVC 数据版本管理（Azure Blob 远端）、MLflow 实验跟踪与模型注册（DagsHub）
- Docker + GitHub Actions CI/CD
- Release：<https://github.com/LosproeOcl/WUT-DevOps-Course/releases/tag/v1.0.0>
- 详见 `finalProject/README.md`、`finalProject/README_zh.md`

## 四、版本清单

| 组件 | 版本 |
|---|---|
| Python | 3.12.0 |
| Git | 2.55.0.windows.5 |
| Docker CLI / Engine | 29.8.2 |
| Docker Desktop | 4.94.0 |
| Docker Compose | v5.5.1 |
| WSL | 3.0.1（内核 6.18.40.1-1） |
| JupyterLab | 4.6.4 |
| MLflow | 3.17.0 |
| DVC | 3.67.1 |
| Flask | 3.1.3 |
| FastAPI | 0.136.3 |
| uvicorn | 0.48.0 |
| scikit-learn | 1.9.1 |
| GitHub CLI (gh) | 2.100.0 |

## 五、日志与脚本

- 日志目录 `Config/logs/`：pip / docker / wsl 安装日志
- 脚本目录 `Config/scripts/`：`check-env.ps1`（环境自检）、`install-wsl.ps1`（WSL2 提权安装）
