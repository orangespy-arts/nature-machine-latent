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

-AffinityMask：启动前把本脚本进程限制到这些逻辑核，训练子进程（含续训）继承该设置。
默认 65535 = 逻辑核 0-15，即 i7-13700K 的 8 个 P 核（含超线程）。Windows 10 没有 Thread Director，
训练主线程（Windows 上 num_workers=0，数据也在主线程加载）曾被调度到 E 核，第一阶段从 13.5 降到约 11 步/秒；
限制到 P 核后恢复。设为 0 表示不限制。换别的 CPU 时需按核编号重新设定。
#>
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [Parameter(Mandatory = $true)][string]$DbPath,
  [Parameter(Mandatory = $true)][string]$OutPath,
  [string]$Config = 'v2_small',
  [int]$MaxRetries = 5,
  [int]$RetryDelaySeconds = 60,
  [string]$Python = 'E:\envs\rave-2.3.1\Scripts\python.exe',
  [string]$ExtraArgs = '',
  [long]$AffinityMask = 65535
)
$extra = @($ExtraArgs -split '\s+' | Where-Object { $_ })
$ErrorActionPreference = 'Continue'
$env:PATH = "$(Split-Path $Python -Parent);$env:PATH"
$wrapper = Join-Path $PSScriptRoot 'rave_train_windows.py'
New-Item -ItemType Directory -Force $OutPath | Out-Null
$runnerLog = Join-Path $OutPath "$Name-runner.log"
function Write-RunnerLog([string]$msg) { "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" | Tee-Object -FilePath $runnerLog -Append }
if ($AffinityMask -ne 0) {
  [System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = [IntPtr]$AffinityMask
  Write-RunnerLog "processor affinity set to 0x$('{0:X}' -f $AffinityMask) (inherited by training processes)"
}

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
