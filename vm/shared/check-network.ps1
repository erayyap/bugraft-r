$out=@('IPv4 DNS:')
$out += (Get-DnsClientServerAddress -AddressFamily IPv4 | Format-Table -AutoSize | Out-String)
$out += 'IPv4 config:'
$out += (Get-NetIPAddress -AddressFamily IPv4 | Select-Object InterfaceAlias,IPAddress,PrefixLength | Out-String)
Clear-DnsClientCache
foreach($hostName in @('meta.prismlauncher.org','api.minecraftservices.com')) {
 try { $out += (Resolve-DnsName $hostName -Type A -DnsOnly -ErrorAction Stop | Select-Object Name,IPAddress | Out-String) } catch {$out += $_.Exception.Message}
}
try {$out += 'HTTPS status: '+(Invoke-WebRequest https://meta.prismlauncher.org/v1/net.minecraft/24w44a.json -UseBasicParsing -TimeoutSec 10).StatusCode} catch {$out += $_.Exception.Message}
$out | Set-Content \\host.lan\Data\control\guest-network.txt
