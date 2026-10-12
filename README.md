# DevOps & MLOps 课前环境准备记录

- 检查/安装日期：2026-10-11
- 机器：Windows 11（Build 10.0.26200）
- 用户：yqysperiod\19284

## 一、课程要求 vs 当前状态

| 项目 | 课程要求 | 当前状态 | 结论 |
|---|---|---|---|
| Python | 3.10 或更高 | 3.12.0 | ✅ 满足 |
| 开发环境 | JupyterLab 或 IDE | VS Code 已装 + JupyterLab 4.6.4 已装 | ✅ 满足 |
| MLflow | 安装 | 3.17.0 | ✅ 满足 |
| DVC | 安装 | 3.67.1 | ✅ 满足 |
| Flask | 可提前安装 | 3.1.3 | ✅ 满足 |
| FastAPI | 可提前安装 | 0.136.3（+ uvicorn 0.48.0） | ✅ 满足 |
| Git | 2.51 及以上 | 2.55.0（原 2.39.1，已升级） | ✅ 满足 |
| Docker | 27 及以上 | Docker Desktop 4.94.0 / Engine 29.8.2（WSL2 后端） | ✅ 满足（`hello-world` 验证通过） |
| DagsHub 账户 | 注册 | 未注册 | ⬜ 需用户操作 |
| GitHub 账户 | 注册 | 已注册（gh CLI 2.100.0 已登录） | ✅ 满足 |

## 二、本次执行的操作

1. **Python 包安装（用户级 `pip install --user`）**
   - `jupyterlab` 4.6.4、`mlflow` 3.17.0、`dvc` 3.67.1（连带 `scikit-learn` 1.9.1 等）
   - 脚本目录 `%APPDATA%\Python\Python312\Scripts` 已加入用户 PATH，`jupyter` / `mlflow` / `dvc` 可直接调用。
2. **Git 升级**
   - `winget upgrade --id Git.Git`：2.39.1 → **2.55.0**
3. **Docker Desktop 安装**
   - `winget install --id Docker.DockerDesktop`：安装 **Docker Desktop 4.94.0**（内置 Docker Engine 29.8.2、Compose v5.5.1）
4. **WSL2 后端准备（Docker 引擎依赖）**
   - 通过提权脚本启用 Windows 功能：`Microsoft-Windows-Subsystem-Linux`、`VirtualMachinePlatform`
   - 安装 WSL **3.0.1**（内核 6.18.40.1）

## 三、后续状态

- ✅ 已重启电脑；Docker Desktop 已启动，引擎正常（WSL2 后端，Engine 29.8.2），
  `docker run hello-world` 验证通过（见 `logs/docker-verify-*.log`）。
- ✅ 已登录 GitHub（账号 **LosproeOcl**，`gh auth login` 完成，HTTPS 协议 + keyring 凭据），
  本目录已初始化为 Git 仓库并推送至 <https://github.com/LosproeOcl/WUT-DevOps-Course>（`main` 分支）。
- ⬜ 注册账户：**DagsHub**（https://dagshub.com）

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

## 五、课程资料

- `261012L1-DevOps课前介绍.docx`：第 1 讲 DevOps 课前介绍
- `261012L2-Version control-1Git功能场景讲解.docx`：第 2 讲 版本控制（Git 功能场景）
- `261012L3-Version control-2Git分支管理与GitHub协作.docx`：第 3 讲 版本控制（Git 分支管理与 GitHub 协作）
- `1. git-guide-and-practice.pdf`：Git 指南与实践

## 六、日志与脚本

- 日志目录：`logs/`
  - `pip-install-*.log`：Python 包安装日志
  - `docker-install-*.log`：Docker Desktop 安装日志
  - `wsl-install-*.log`、`wsl-elevated.log`：WSL2 后端安装日志
- 脚本目录：`scripts/`
  - `check-env.ps1`：环境自检脚本
  - `install-wsl.ps1`：WSL2 提权安装脚本
