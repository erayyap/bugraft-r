$ErrorActionPreference='Stop'
$shared='\\host.lan\Data';if(Test-Path 'Z:\tools'){$shared='Z:'}
$control="$shared\control";$base='C:\BugCraft';$active=$null
$mutex=New-Object System.Threading.Mutex($false,'Local\BugCraftController')
if(-not $mutex.WaitOne(0)){exit}
if(Test-Path "$control\state.json"){$active=(Get-Content "$control\state.json" -Raw|ConvertFrom-Json).active}
$env:GALLIUM_DRIVER='llvmpipe';$env:LIBGL_ALWAYS_SOFTWARE='true';$env:LP_NUM_THREADS='4'
Add-Type @'
using System;using System.Runtime.InteropServices;
public class Desktop { [DllImport("user32.dll", SetLastError=true)] public static extern IntPtr SendMessageTimeout(IntPtr h,uint msg,UIntPtr w,IntPtr l,uint flags,uint timeout,out UIntPtr result); [DllImport("user32.dll")] public static extern void mouse_event(uint flags,int dx,int dy,uint data,UIntPtr extra); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h); [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h,int x,int y,int w,int z,bool r); }
'@
function State {
  $games=@(Get-Process java,javaw -ErrorAction SilentlyContinue | Where-Object {$_.Path -like 'C:\BugCraft\java*'})
  $s=@{utc=[DateTime]::UtcNow.ToString('o');game_running=($games.Count -gt 0);games=@($games | ForEach-Object {@{pid=$_.Id;window=($_.MainWindowHandle -ne 0);title=$_.MainWindowTitle}});active=$active;os=(Get-CimInstance Win32_OperatingSystem).Caption}
  $s|ConvertTo-Json -Depth 5|Set-Content "$control\state.tmp";Move-Item "$control\state.tmp" "$control\state.json" -Force
}
$ticks=0
while($true){
  $ui=$null
  try {$ui=Get-Content "$control\ui-request.json" -Raw -ErrorAction Stop|ConvertFrom-Json} catch {}
  if($ui){
    Remove-Item "$control\ui-request.json" -ErrorAction SilentlyContinue
    if($ui.action -eq 'move_relative' -and [Math]::Abs($ui.dx) -le 500 -and [Math]::Abs($ui.dy) -le 500){
      [Desktop]::mouse_event(1,[int]$ui.dx,[int]$ui.dy,0,[UIntPtr]::Zero)
      @{id=$ui.id;ok=$true}|ConvertTo-Json|Set-Content "$control\ui-response.json"
    }
  }
  $r=$null
  try {$r=Get-Content "$control\request.json" -Raw -ErrorAction Stop|ConvertFrom-Json} catch {}
  if($r){
    Remove-Item "$control\request.json" -ErrorAction SilentlyContinue
    try{
      if($r.op -eq 'launch'){
        if(@(Get-Process java,javaw -ErrorAction SilentlyContinue|Where-Object {$_.Path -like 'C:\BugCraft\java*'}).Count -gt 0){throw 'Previous owned game still running'}
        $active=$r.attempt
        $inst="$base\Prism\instances\$active";New-Item -ItemType Directory -Force $inst|Out-Null
        $j=(Get-ChildItem "$base\java$($r.java)" -Directory|Select-Object -First 1).FullName+'\bin\javaw.exe'
        @{formatVersion=1;components=@(@{uid='net.minecraft';version=$r.version})}|ConvertTo-Json -Depth 5|Set-Content "$inst\mmc-pack.json"
        @"
[General]
InstanceType=OneSix
name=$active
OverrideJavaLocation=true
OverrideJava=true
JavaPath=$($j.Replace('\','/'))
OverrideMemory=true
MinMemAlloc=512
MaxMemAlloc=4096
OverrideWindow=true
MinecraftWinWidth=960
MinecraftWinHeight=540
OverrideCommands=true
WrapperCommand=C:/BugCraft/capture.exe
"@|Set-Content "$inst\instance.cfg"
        if(-not (Test-Path "$base\capture.exe")){throw 'Native capture wrapper missing'}
        New-Item -ItemType Directory -Force "$inst\minecraft"|Out-Null
        "enableVsync:false`nmaxFps:30`nrenderDistance:6`nsimulationDistance:5`nguiScale:2`nfullscreen:false`nshowSubtitles:false`nonboardAccessibility:false`nskipMultiplayerWarning:true"|Set-Content "$inst\minecraft\options.txt"
        Start-Process "$base\Prism\prismlauncher.exe" -ArgumentList "--launch $active" -WorkingDirectory "$base\Prism" -RedirectStandardOutput "$base\private-prism-out.log" -RedirectStandardError "$base\private-prism-err.log"
      } elseif($r.op -eq 'probe_window'){
        $windows=@()
        foreach($g in @(Get-Process java,javaw -ErrorAction SilentlyContinue|Where-Object {$_.Path -like 'C:\BugCraft\java*' -and $_.MainWindowHandle -ne 0})){
          $answer=[UIntPtr]::Zero
          $timer=[Diagnostics.Stopwatch]::StartNew()
          $sent=[Desktop]::SendMessageTimeout($g.MainWindowHandle,0,[UIntPtr]::Zero,[IntPtr]::Zero,0,1500,[ref]$answer)
          $err=[Runtime.InteropServices.Marshal]::GetLastWin32Error();$timer.Stop()
          $windows+=@{pid=$g.Id;handle=$g.MainWindowHandle.ToInt64();responded=($sent -ne [IntPtr]::Zero);win32_error=$err;elapsed_ms=$timer.ElapsedMilliseconds}
        }
        @{request=$r.id;ok=$true;windows=$windows;probe_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Depth 5|Set-Content "$control\response.json"
        State;continue
      } elseif($r.op -eq 'focus'){
        $g=Get-Process java,javaw -ErrorAction SilentlyContinue|Where-Object {$_.Path -like 'C:\BugCraft\java*' -and $_.MainWindowHandle -ne 0}|Select-Object -First 1
        if($g){[Desktop]::MoveWindow($g.MainWindowHandle,0,0,980,580,$true)|Out-Null;[Desktop]::SetForegroundWindow($g.MainWindowHandle)|Out-Null}
      } elseif($r.op -eq 'collect'){
        $dest="$shared\evidence\$active";New-Item -ItemType Directory -Force $dest|Out-Null
        $inst="$base\Prism\instances\$active\minecraft"
        foreach($folder in @('logs','crash-reports','game-stdout.txt','game-stderr.txt','capture-error.txt','options.txt')){if(Test-Path "$inst\$folder"){Copy-Item "$inst\$folder" $dest -Recurse -Force}}
        $pinst="$base\Prism\instances\$active"
        Copy-Item "$pinst\mmc-pack.json","$pinst\instance.cfg" $dest -Force
      } elseif($r.op -eq 'stop'){
        # Only processes running our dedicated installed runtimes; no broad host kills.
        Get-Process java,javaw -ErrorAction SilentlyContinue|Where-Object {$_.Path -like 'C:\BugCraft\java*'}|Stop-Process -Force
        Get-Process prismlauncher -ErrorAction SilentlyContinue|Where-Object {$_.Path -like 'C:\BugCraft\Prism\*'}|Stop-Process -Force
      } elseif($r.op -eq 'remove_worlds'){
        if($active -and $active -match '^[a-zA-Z0-9_-]+$'){
          $p="$base\Prism\instances\$active\minecraft\saves";if(Test-Path $p){Remove-Item $p -Recurse -Force}
        }
      } else {throw 'Unknown control operation'}
      @{request=$r.id;ok=$true}|ConvertTo-Json|Set-Content "$control\response.json"
    }catch{@{request=$r.id;ok=$false;error=$_.Exception.Message}|ConvertTo-Json|Set-Content "$control\response.json"}
  }
  if(($ticks % 20) -eq 0){State};$ticks++;Start-Sleep -Milliseconds 100
}
