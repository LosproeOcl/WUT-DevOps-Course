$ErrorActionPreference = 'Continue'
$log = 'E:\19284\postgraduate\WHUT-26-1\Devops&MLOps\logs\wsl-elevated.log'
"===== $(Get-Date -Format o) : start =====" | Out-File -FilePath $log -Encoding utf8
"--- dism: Microsoft-Windows-Subsystem-Linux ---" | Out-File -FilePath $log -Append -Encoding utf8
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart *>> $log
"--- dism: VirtualMachinePlatform ---" | Out-File -FilePath $log -Append -Encoding utf8
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart *>> $log
"--- wsl --install --no-distribution ---" | Out-File -FilePath $log -Append -Encoding utf8
wsl.exe --install --no-distribution *>> $log
"--- wsl --set-default-version 2 ---" | Out-File -FilePath $log -Append -Encoding utf8
wsl.exe --set-default-version 2 *>> $log
"===== $(Get-Date -Format o) : done =====" | Out-File -FilePath $log -Append -Encoding utf8
