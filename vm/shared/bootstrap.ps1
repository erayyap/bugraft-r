$ErrorActionPreference='Stop'
$shared='\\host.lan\Data'
if(Test-Path 'Z:\tools'){$shared='Z:'}
$base='C:\BugCraft'
New-Item -ItemType Directory -Force $base | Out-Null
try {
  Expand-Archive "$shared\tools\prism.zip" "$base\Prism" -Force
  foreach($v in @(8,17,21)){
    Expand-Archive "$shared\tools\java$v.zip" "$base\java$v" -Force
    $j=Get-ChildItem "$base\java$v" -Directory | Select-Object -First 1
    Copy-Item "$shared\tools\mesa\x64\*.dll" "$($j.FullName)\bin" -Force
  }
  Copy-Item "$shared\tools\vc_redist.x64.exe" "$base\vc_redist.x64.exe" -Force
  Start-Process "$base\vc_redist.x64.exe" -ArgumentList '/install /quiet /norestart' -Wait
  Copy-Item "$shared\control\prism-account-transfer.json" "$base\Prism\accounts.json" -Force
  Remove-Item "$shared\control\prism-account-transfer.json"
  @"
[General]
ConfigVersion=1.2
Language=en_US
MaxMemAlloc=4096
MinMemAlloc=512
JavaAutoDetect=false
JavaAutoDownload=false
ShowConsole=false
ShowConsoleOnError=false
"@ | Set-Content "$base\Prism\prismlauncher.cfg"
  $env:GALLIUM_DRIVER='llvmpipe'
  $env:LIBGL_ALWAYS_SOFTWARE='true'
  $env:LP_NUM_THREADS='4'
  Set-Content "$shared\control\bootstrap-ready.txt" 'Installed Prism 11.1.0, Temurin Java 8/17/21, Mesa llvmpipe 26.2.0'
  & "$shared\guest-control.ps1"
} catch {
  Set-Content "$shared\control\bootstrap-error.txt" $_.Exception.Message
}
