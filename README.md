# Git Handbook —— Try it yourself 练习记录

本文档记录依据《1. git-guide-and-practice.pdf》完成的 15 步 Git 练习全过程，以及本练习仓库的特殊配置说明。

> 详细逐步操作（含命令与输出）见同目录 `LOG.md`。

## 一、背景与目标

- 来源文档：`1. git-guide-and-practice.pdf`（Git Handbook，15 个 "Try it yourself" 练习）
- 目标：在现有项目 `Devops&MLOps` 内完成全部练习，提交并推送到 GitHub，但**不影响现有项目完整性**
- 完成日期：2026-10-12

## 二、仓库结构说明（关键：独立分支映射方案）

现有项目仓库为 `LosproeOcl/WUT-DevOps-Course`，其 `main` 分支保存课程资料。

练习**没有**新建独立的 GitHub 仓库，而是采用「子文件夹 + 独立分支」方案：

- `git-playground/` 是 `Devops&MLOps` 下的一个**独立 Git 仓库**（嵌套仓库），与项目互不影响。
- 它的远程仍指向 `WUT-DevOps-Course`，但通过 refspec 把本地 `main` 映射到远端 **`git-playground`** 分支，从而不碰项目的 `main`。

| 方向 | 映射 | 说明 |
|---|---|---|
| push | `refs/heads/main -> refs/heads/git-playground` | 本地 `main` 提交推到远端 `git-playground` 分支 |
| fetch | `refs/heads/git-playground -> refs/remotes/origin/main` | 远端 `git-playground` 映射为本地 `origin/main`，使 PDF 里 `origin/main` 写法照常有效 |

现有项目侧保护：

- 在项目根目录 `.gitignore` 中加入 `git-playground/` 与 `git-playground-peer/`，防止练习仓库被误提交进项目主分支。

### 初始化配置（练习仓库内执行）

```bash
git init -b main
git config user.name "LosproeOcl"
git config user.email "140792174+LosproeOcl@users.noreply.github.com"
git remote add origin https://github.com/LosproeOcl/WUT-DevOps-Course.git
git config remote.origin.push refs/heads/main:refs/heads/git-playground
git config remote.origin.fetch +refs/heads/git-playground:refs/remotes/origin/main
git config branch.main.remote origin
git config branch.main.merge refs/heads/git-playground   # 注意：必须指向 git-playground，否则 pull 会误拉项目主分支
```

> 途中修正点：`branch.main.merge` 最初误设为 `refs/heads/main`，导致 `git pull` 去拉项目主分支而报错；已改为 `refs/heads/git-playground`。

## 三、环境与执行说明

- 系统：Windows 11
- Git：2.55.0
- 远程认证：`gh auth login`（HTTPS + keyring）
- 网络代理：`http://127.0.0.1:7897`
- **文件类命令（`echo`/`cat`/`>>`）使用 Git Bash 执行**，以产出纯文本 LF 文件；若用 PowerShell 的 `>` 重定向会写成 UTF-16（Git 会误判为二进制）。

## 四、练习总览

| # | 练习 | 核心命令 | 关键产出 |
|---|---|---|---|
| 1-2 | 建仓、连接、首次提交推送 | `init` `add` `commit` `push` | `48b252b` |
| 3 | 编辑-暂存-提交-推送 | `diff` `diff --staged` | `f1c71bc` |
| 4 | 分支合并 | `switch -c` `merge --no-ff` | `840b6e8` |
| 5 | 合并冲突 | `merge --abort` 手动解决 | `4060096` |
| 6 | rebase 冲突 | `rebase --abort` `rebase --continue` | `07dbc18` |
| 7 | Pull Request | `gh pr create/merge` | PR #1，`47f7067` |
| 8 | fetch vs pull | `fetch` `pull --ff-only` | `review.txt` 出现 |
| 9 | 克隆模拟队友 | `clone` `pull --rebase` `--left-right` | `43bb3a5` |
| 10 | pull 合并行为 | `pull --no-rebase` | 合并提交 `241f561` |
| 11 | stash | `stash push/pop` | `28a8357` |
| 12 | revert | `revert --no-edit` | `ac544cf` |
| 13 | reset | `reset --soft HEAD~1` | `75ab3fd` |
| 14 | restore | `restore --staged` `restore` | 丢弃编辑 |
| 15 | 收尾检查 | `push` `log --graph` | 工作区干净 |

## 五、最终状态

- 远端 `git-playground` 分支 HEAD：`75ab3fd Add the final draft`
- 远端项目 `main` 分支：`1e3067b Ignore practice peer clone`（**未受练习影响**）
- 本地工作区干净，`git log --graph` 包含分支提交、合并提交、rebase 重放提交、以及一次 revert。

完整提交图：

```
* 75ab3fd Add the final draft
* ac544cf Revert "Add an unwanted file"
* 6d6051f Add an unwanted file
* 28a8357 Finish the stashed idea
*   241f561 Merge branch 'git-playground' ...
|\
| * ff76cd3 Extend teammate note
* | 2ea63a9 Extend local notes
|/
* 43bb3a5 Add local work
* 94a1ef3 Add teammate note
*   47f7067 Merge pull request #1 ...
|\
| * 89a212b Add review notes
|/
* 07dbc18 Choose green
* 4a8fbc5 Choose red
*   4060096 Resolve greeting conflict
|\
| * 40e3c1d Use a friendly greeting
* | 3b90da2 Use a team greeting
|/
*   840b6e8 Merge practice tasks
|\
| * 355bb15 Add practice tasks
|/
* f1c71bc Add a practice note
* 48b252b Create practice files
```

## 六、与 PDF 的三处差异

1. 首次推送：PDF 用 `git push -u origin main`，这里用 `git push origin main:git-playground`（映射到独立分支）。
2. 练习 7 PR 的 base 分支选 `git-playground`（而非 `main`）。
3. 练习 9 克隆队友副本后，做了与主练习仓库相同的 refspec 映射（使 `main` 在副本中同样对应远端 `git-playground`）。
