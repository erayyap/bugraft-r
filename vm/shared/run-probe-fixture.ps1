param([string]$Mode='responsive')
$ErrorActionPreference='Stop'
$dir='C:\BugCraft\java-probe-fixture'
New-Item -ItemType Directory -Force $dir | Out-Null
Get-Process javaw -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq "$dir\javaw.exe"} | Stop-Process -Force
& C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /target:winexe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /out:C:\BugCraft\java-probe-fixture\javaw.exe \\host.lan\Data\ProbeFixture.cs
if($LASTEXITCODE -ne 0){throw 'Fixture compile failed'}
$child=Start-Process "$dir\javaw.exe" -ArgumentList $Mode -PassThru
@{mode=$Mode;pid=$child.Id;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content \\host.lan\Data\control\fixture-ready.json
