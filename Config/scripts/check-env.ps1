# DevOps & MLOps 环境自检脚本
# 用法: powershell -ExecutionPolicy Bypass -File check-env.ps1
$ErrorActionPreference = 'SilentlyContinue'
function Line($name, $val) { "{0,-16} {1}" -f $name, $val }

Write-Output "===== DevOps & MLOps 环境自检 ($(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) ====="

Write-Output "`n[Python]"
Line "python" (python --version 2>&1)

Write-Output "`n[Python 包]"
python -X utf8 -c "import importlib.metadata as m
for p in ['jupyterlab','mlflow','dvc','flask','fastapi','uvicorn','scikit-learn']:
    try: print(f'{p:15s} {m.version(p)}')
    except Exception: print(f'{p:15s} MISSING')"

Write-Output "`n[Git]"
$gitExe = "C:\Program Files\Git\cmd\git.exe"
if (Test-Path $gitExe) { Line "git" (& $gitExe --version) } else { Line "git" "NOT FOUND" }

Write-Output "`n[Docker]"
$dd = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (Test-Path $dd) {
    Line "docker(cli)" (& $dd --version)
    $srv = & $dd info --format '{{.ServerVersion}}' 2>&1
    if ($LASTEXITCODE -eq 0) { Line "docker(engine)" $srv } else { Line "docker(engine)" "NOT RUNNING (start Docker Desktop)" }
} else { Line "docker" "NOT FOUND" }

Write-Output "`n[WSL]"
$wslv = (wsl.exe --version 2>&1 | Select-Object -First 1)
Line "wsl" $wslv

Write-Output "`n[GitHub CLI]"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (Test-Path $gh) { Line "gh" (& $gh --version 2>&1 | Select-Object -First 1) } else { Line "gh" "NOT FOUND" }

Write-Output "`n[IDE]"
Line "VS Code" $(if (Get-Command code -ErrorAction SilentlyContinue) { "installed" } else { "see MSIX install" })

Write-Output "`n===== 完成 ====="

