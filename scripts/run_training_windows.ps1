<#
自动续训：运行 scripts/rave_train_windows.py；若训练异常退出，从同名运行目录的最新检查点自动恢复，最多重试 -MaxRetries 次。

- RAVE 运行目录名为 <Name>_<配置哈希>，同样的 Name 与参数恢复时会回到同一目录。
- 检查点只在验证时保存（每 --val_every 步，默认 10000），崩溃最多丢失到上一次验证之后的进度。
- 每次启动、退出码和时间写入 <OutPath>\<Name>-runner.log；训练输出写入 <OutPath>\<Name>-<时间>-attempt<N>.log。
- 连续失败达到上限即停止，不无限重试；正常结束（退出码 0）不再重启。

示例：
  powershell -ExecutionPolicy Bypass -File scripts\run_training_windows.ps1 `
    -Name exp003-forest-s105ck01 `
    -DbPath E:\nature-machine-latent-data\processed\forest-s105ck01-v001\db `
    -OutPath E:\nature-machine-latent-data\checkpoints\exp-003 `
    -ExtraArgs "--max_steps 2000000"

-ExtraArgs 为一个字符串，按空格拆分后原样传给 rave train（参数值本身不能含空格）。
#>
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [Parameter(Mandatory = $true)][string]$DbPath,
  [Parameter(Mandatory = $true)][string]$OutPath,
  [string]$Config = 'v2_small',
  [int]$MaxRetries = 5,
  [int]$RetryDelaySeconds = 60,
  [string]$Python = 'E:\envs\rave-2.3.1\Scripts\python.exe',
  [string]$ExtraArgs = ''
)
$extra = @($ExtraArgs -split '\s+' | Where-Object { $_ })
$ErrorActionPreference = 'Continue'
$env:PATH = "$(Split-Path $Python -Parent);$env:PATH"
$wrapper = Join-Path $PSScriptRoot 'rave_train_windows.py'
New-Item -ItemType Directory -Force $OutPath | Out-Null
$runnerLog = Join-Path $OutPath "$Name-runner.log"
function Write-RunnerLog([string]$msg) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" | Tee-Object -FilePath $runnerLog -Append }

$base = @('--config', $Config, '--db_path', $DbPath, '--out_path', $OutPath, '--name', $Name,
          '--channels', '1', '--gpu', '0') + $extra
Push-Location (Split-Path $OutPath -Parent)
try {
  for ($attempt = 1; $attempt -le $MaxRetries + 1; $attempt++) {
    $runArgs = $base
    $run = Get-ChildItem $OutPath -Directory -Filter "${Name}_*" -ErrorAction SilentlyContinue |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($run -and (Get-ChildItem $run.FullName -Recurse -Filter *.ckpt -ErrorAction SilentlyContinue)) {
      $runArgs = $base + @('--ckpt', $run.FullName)
      Write-RunnerLog "attempt ${attempt}: resume from $($run.FullName)"
    } else {
      Write-RunnerLog "attempt ${attempt}: start new run"
    }
    $log = Join-Path $OutPath "$Name-$(Get-Date -Format yyyyMMdd-HHmmss)-attempt${attempt}.log"
    & $Python $wrapper @runArgs *> $log
    $code = $LASTEXITCODE
    Write-RunnerLog "attempt ${attempt}: exit code $code"
    if ($code -eq 0) { Write-RunnerLog 'finished normally'; break }
    if ($attempt -gt $MaxRetries) { Write-RunnerLog "giving up after $MaxRetries retries"; exit $code }
    Start-Sleep -Seconds $RetryDelaySeconds
  }
} finally { Pop-Location }
