# deploy.ps1 — 把 MotorCockpit 部署到 ESP32-S3 设备。
#
# 用法（PowerShell 执行策略可能阻止脚本，用 Bypass）：
#   powershell -ExecutionPolicy Bypass -File .\deploy.ps1 -Port COM39
#   powershell -ExecutionPolicy Bypass -File .\deploy.ps1 -Port COM39 -NoBackup
#
# 行为：
#   1. 探测设备身份
#   2. 备份设备现有全部文件到本地 _backup_device_<时间戳>（可 -NoBackup 跳过）
#   3. 上传 MotorCockpit 源文件到设备根（boot/main/config + driver/domain/lib/ui/tests）
#   4. 不删除设备上的其他文件（如旧项目的 web/ flash/ 等），避免误删数据
#
# 部署后在 REPL 运行：import tests.test_hardware as t; t.run()
# 自检通过后把 config.py 的 AUTO_START 改 True，复位自动启动 UI。

param(
    [string]$Port = "COM39",
    [switch]$NoBackup
)
$ErrorActionPreference = "Stop"
$proj = $PSScriptRoot

Write-Host "=== MotorCockpit 部署 -> $Port ===" -ForegroundColor Cyan

# 1. 确认设备
Write-Host "[1/4] 探测设备..."
mpremote connect $Port exec "import os; print('TARGET:', os.uname().machine)"

# 2. 备份
if (-not $NoBackup) {
    $backup = Join-Path $proj ("_backup_device_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
    New-Item -ItemType Directory -Force $backup | Out-Null
    Write-Host "[2/4] 备份设备现有文件 -> $backup"
    mpremote connect $Port cp -r : $backup 2>&1 | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "[2/4] 跳过备份"
}

# 3. 上传源文件
Write-Host "[3/4] 上传 MotorCockpit 源文件..."
$items = @("boot.py", "config.py", "main.py", "driver", "domain", "lib", "ui", "tests")
foreach ($item in $items) {
    $src = Join-Path $proj $item
    if (-not (Test-Path $src)) { continue }
    Write-Host "  上传 $item"
    if (Test-Path $src -PathType Container) {
        mpremote connect $Port fs cp -r $src :$item
    } else {
        mpremote connect $Port fs cp $src :$item
    }
}

# 4. 完成
Write-Host "[4/4] 部署完成。" -ForegroundColor Green
Write-Host ""
Write-Host "下一步："
Write-Host "  mpremote connect $Port repl"
Write-Host "  >>> import tests.test_hardware as t; t.run()"
Write-Host "  自检全部 PASS 后，把 config.py 的 AUTO_START 改为 True，复位启动 UI。"
