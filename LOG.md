# 操作日志（完整过程记录）

本文档按时间顺序记录全部命令及其关键输出。执行环境：Git Bash（文件类命令）+ PowerShell（git/gh 命令）。

> 约定：`$` 表示命令，`>` 表示关键输出。

---

## Phase 0：初始化与保护现有项目

### 0.1 现有项目加 .gitignore（保护）

```bash
# E:\19284\postgraduate\WHUT-26-1\Devops&MLOps\.gitignore
git-playground/
```

```bash
$ git add .gitignore
$ git commit -m "Ignore practice playground directory"
$ git push
# > e6c9cbe..8b3a152  main -> main
```

（后续练习 9 前再追加一行，见 9.0）

### 0.2 创建练习仓库并配置 refspec

```bash
$ mkdir git-playground && cd git-playground
$ git init -b main
$ git config user.name "LosproeOcl"
$ git config user.email "140792174+LosproeOcl@users.noreply.github.com"
$ git remote add origin https://github.com/LosproeOcl/WUT-DevOps-Course.git
$ git config remote.origin.push refs/heads/main:refs/heads/git-playground
$ git config remote.origin.fetch +refs/heads/git-playground:refs/remotes/origin/main
$ git config branch.main.remote origin
$ git config branch.main.merge refs/heads/main    # 注意：后面在练习 8 修正为 git-playground
```

---

## 练习 1-2：建仓、连接、首次提交推送

```bash
$ echo "My Git practice notes" > notes.txt
$ echo "Hello world" > greeting.txt
$ echo "color=blue" > settings.txt

$ git status -s
> ?? greeting.txt
> ?? notes.txt
> ?? settings.txt

$ git add notes.txt greeting.txt settings.txt
$ git diff --staged
> +Hello world
> +My Git practice notes
> +color=blue

$ git commit -m "Create practice files"
> [main (root-commit) 48b252b] Create practice files

$ git push origin main:git-playground
> * [new branch] main -> git-playground
```

---

## 练习 3：编辑-暂存-提交-推送

```bash
$ echo "I can inspect and save changes." >> notes.txt
$ git status -s
>  M notes.txt

$ git diff                 # 未暂存改动
$ git add notes.txt
$ git diff                 # 空（改动进入暂存区）
$ git diff --staged        # 显示暂存内容

$ git commit -m "Add a practice note"
> [main f1c71bc] Add a practice note

$ git log --oneline -3
$ git push
> 48b252b..f1c71bc  main -> git-playground
$ git status -s            # 干净
```

---

## 练习 4：创建分支并合并

```bash
$ git switch -c feature-list
$ echo "Practice branching" > tasks.txt
$ git add tasks.txt
$ git commit -m "Add practice tasks"
> [feature-list 355bb15] Add practice tasks

$ git branch               # * feature-list, main
$ git switch main
$ ls                       # 无 tasks.txt

$ git merge --no-ff feature-list -m "Merge practice tasks"
> Merge made by the 'ort' strategy.   # 840b6e8

$ cat tasks.txt
> Practice branching

$ git log --graph --oneline --all -8
```

---

## 练习 5：触发并解决合并冲突

```bash
$ git switch -c friendly-greeting
$ echo "Hello friends" > greeting.txt
$ git add greeting.txt
$ git commit -m "Use a friendly greeting"       # 40e3c1d

$ git switch main
$ echo "Hello team" > greeting.txt
$ git add greeting.txt
$ git commit -m "Use a team greeting"           # 3b90da2

$ git merge friendly-greeting
> CONFLICT (content): Merge conflict in greeting.txt

$ git status -s
> UU greeting.txt
$ cat greeting.txt
> <<<<<<< HEAD
> Hello team
> =======
> Hello friends
> >>>>>>> friendly-greeting

$ git merge --abort         # 回到 "Hello team"
$ git merge friendly-greeting   # 再次冲突
$ echo "Hello team and friends" > greeting.txt
$ git add greeting.txt
$ git commit -m "Resolve greeting conflict"     # 4060096
$ git status -s             # 干净
```

---

## 练习 6：触发并解决 rebase 冲突

```bash
$ git switch -c color-update
$ echo "color=green" > settings.txt
$ git add settings.txt
$ git commit -m "Choose green"                  # 0a8c972

$ git switch main
$ echo "color=red" > settings.txt
$ git add settings.txt
$ git commit -m "Choose red"                    # 4a8fbc5

$ git switch color-update
$ git rebase main
> CONFLICT (content): Merge conflict in settings.txt
$ cat settings.txt
> <<<<<<< HEAD
> color=red
> =======
> color=green
> >>>>>>> 0a8c972 (Choose green)

$ git rebase --abort       # 回到 color=green
$ git rebase main          # 再次冲突
$ echo "color=purple" > settings.txt
$ git add settings.txt
$ git -c core.editor=true rebase --continue
> [detached HEAD 07dbc18] Choose green   # ID 由 0a8c972 重写为 07dbc18

$ git log --oneline -3
$ git switch main
$ git merge --ff-only color-update
$ cat settings.txt
> color=purple
$ git push
> f1c71bc..07dbc18  main -> git-playground
```

---

## 练习 7：创建并合并 Pull Request

```bash
$ git switch -c pr-notes
$ echo "This file arrived through a pull request." > review.txt
$ git add review.txt
$ git commit -m "Add review notes"              # 89a212b
$ git push -u origin pr-notes
> * [new branch] pr-notes -> pr-notes

# 使用 gh CLI 创建 PR（base=git-playground，head=pr-notes）
$ gh pr create --repo LosproeOcl/WUT-DevOps-Course --base git-playground --head pr-notes \
    --title "Add review notes" --body "Practice pull request (Try it yourself - exercise 7)"
> https://github.com/LosproeOcl/WUT-DevOps-Course/pull/1

$ gh pr merge 1 --repo LosproeOcl/WUT-DevOps-Course --merge --delete-branch
# 合并方式 = "Create a merge commit"，合并提交 47f7067
```

---

## 练习 8：区分 fetch 与 pull

```bash
$ git switch main
$ git fetch origin
> 07dbc18..47f7067  git-playground -> origin/main

$ git log --oneline main..origin/main
> 47f7067 Merge pull request #1 ...
> 89a212b Add review notes

$ git diff main origin/main      # 显示新增 review.txt
$ ls                             # 无 review.txt（fetch 不合并）

# —— 修正配置 ——
$ git config branch.main.merge refs/heads/git-playground

$ git pull --ff-only
> Updating 07dbc18..47f7067  Fast-forward

$ cat review.txt
> This file arrived through a pull request.
$ git branch -d pr-notes         # 已合并，安全删除
```

---

## 练习 9：克隆第二份副本模拟队友

### 9.0 现有项目追加 .gitignore

```bash
# .gitignore 追加
git-playground-peer/

$ git add .gitignore
$ git commit -m "Ignore practice peer clone"    # 1e3067b
$ git push
```

### 9.1 队友副本（git-playground-peer）

```bash
$ cd ..
$ git clone https://github.com/LosproeOcl/WUT-DevOps-Course.git git-playground-peer
$ cd git-playground-peer
$ git switch -C main origin/git-playground      # 本地 main 指向远端 git-playground
$ git config user.name "LosproeOcl"
$ git config user.email "140792174+LosproeOcl@users.noreply.github.com"
$ git config remote.origin.push refs/heads/main:refs/heads/git-playground
$ git config remote.origin.fetch +refs/heads/git-playground:refs/remotes/origin/main
$ git config branch.main.remote origin
$ git config branch.main.merge refs/heads/git-playground

$ echo "A teammate added this note." > team.txt
$ git add team.txt
$ git commit -m "Add teammate note"             # 94a1ef3
$ git push
> 47f7067..94a1ef3  main -> git-playground
```

### 9.2 本副本（git-playground）制造分叉

```bash
$ cd ../git-playground
$ echo "My simultaneous local change." >> notes.txt
$ git add notes.txt
$ git commit -m "Add local work"                # bae6af6

$ git push
> ! [rejected] main -> git-playground (fetch first)   # 历史分叉

$ git fetch origin
> 47f7067..94a1ef3  git-playground -> origin/main
$ git log --oneline --left-right main...origin/main
> < bae6af6 Add local work
> > 94a1ef3 Add teammate note

$ git pull --ff-only
> fatal: Not possible to fast-forward, aborting.

$ git pull --rebase                             # 重放本地提交
$ git log --oneline -4
> 43bb3a5 Add local work
> 94a1ef3 Add teammate note
$ cat team.txt                                  # 双方改动都在
$ git push
> 94a1ef3..43bb3a5  main -> git-playground
```

---

## 练习 10：对比 pull 的合并行为

```bash
# 队友副本
$ cd ../git-playground-peer
$ git pull --ff-only
$ echo "Another teammate change." >> team.txt
$ git add team.txt
$ git commit -m "Extend teammate note"          # ff76cd3
$ git push
> 43bb3a5..ff76cd3  main -> git-playground

# 本副本
$ cd ../git-playground
$ echo "Another local change." >> notes.txt
$ git add notes.txt
$ git commit -m "Extend local notes"            # 2ea63a9
$ git pull --no-rebase --no-edit                # 产生合并提交
> Merge made by the 'ort' strategy.             # 241f561

$ git log --graph --oneline -6
$ git push
> ff76cd3..241f561  main -> git-playground
```

---

## 练习 11：stash 暂存未完成工作

```bash
$ echo "An unfinished idea." >> notes.txt
$ git diff
$ git stash push -m "Unfinished notes"
> Saved working directory and index state On main: Unfinished notes
$ git status -s        # 干净
$ git stash list
> stash@{0}: On main: Unfinished notes
$ cat notes.txt        # 那行消失

$ git switch feature-list
$ git switch main
$ git stash pop        # 恢复改动
$ git add notes.txt
$ git commit -m "Finish the stashed idea"       # 28a8357
```

---

## 练习 12：revert 撤销已发布提交

```bash
$ echo "This file was a mistake." > mistake.txt
$ git add mistake.txt
$ git commit -m "Add an unwanted file"          # 6d6051f
$ git push
> 241f561..6d6051f  main -> git-playground

$ git revert --no-edit HEAD
> [main ac544cf] Revert "Add an unwanted file"
$ git log --oneline -3
$ ls                 # mistake.txt 已删除
$ git push
> 6d6051f..ac544cf  main -> git-playground
```

---

## 练习 13：reset 重做未发布提交

```bash
$ git switch -c reset-practice
$ echo "Draft wording" > draft.txt
$ git add draft.txt
$ git commit -m "Temporary draft"               # 84a4cd9

$ git reset --soft HEAD~1
$ git status -s
> A  draft.txt           # 改动回到暂存区
$ git diff --staged
$ git log --oneline -2   # "Temporary draft" 已不在顶端

$ echo "Final wording" > draft.txt
$ git add draft.txt
$ git commit -m "Add the final draft"           # 75ab3fd
$ git switch main
$ git merge --ff-only reset-practice
$ cat draft.txt
> Final wording
```

---

## 练习 14：取消暂存并丢弃编辑

```bash
$ echo "An edit I do not want." >> notes.txt
$ git add notes.txt
$ git restore --staged notes.txt
$ git status -s
>  M notes.txt           # 改动仍在文件里
$ git diff
$ git restore notes.txt  # 丢弃改动
$ git status -s          # 干净
```

---

## 练习 15：收尾并检查

```bash
$ git push
> ac544cf..75ab3fd  main -> git-playground
$ git status
> On branch main / nothing to commit, working tree clean
$ git log --graph --oneline --decorate --all -25
```

---

## 最终验证

```bash
$ gh api repos/LosproeOcl/WUT-DevOps-Course/branches
# > git-playground -> 75ab3fd
# > main           -> 1e3067b   （项目主分支，未受影响）
```
