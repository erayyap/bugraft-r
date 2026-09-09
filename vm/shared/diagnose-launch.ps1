$ErrorActionPreference='Stop'
$out=@()
foreach($p in Get-ChildItem C:\BugCraft\Prism -Filter 'PrismLauncher*.log' -Recurse) {
 $out += "FILE: $($p.Name)"
 foreach($line in Get-Content $p.FullName) {
  if($line -match '(?i)failed|error|wrapper|exit code|crashed|could not|cannot|metadata|download|24w37a|component|http' -and $line -notmatch '(?i)token|authorization|session|arguments|password|Bearer') {$out += $line}
 }
}
$out += 'INSTANCE FILES:'
$out += (Get-ChildItem C:\BugCraft\Prism\instances\diagnostic-24w37a -Recurse | Select-Object FullName,Length | Out-String)
$out | Set-Content '\\host.lan\Data\control\launch-diagnostic.txt'
