New-Item 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR' -Force | Out-Null
Set-ItemProperty 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR' AppCaptureEnabled 0
New-Item 'HKCU:\System\GameConfigStore' -Force | Out-Null
Set-ItemProperty 'HKCU:\System\GameConfigStore' GameDVR_Enabled 0
New-Item 'HKCU:\SOFTWARE\Microsoft\GameBar' -Force | Out-Null
Set-ItemProperty 'HKCU:\SOFTWARE\Microsoft\GameBar' ShowStartupPanel 0
Set-ItemProperty 'HKCU:\SOFTWARE\Microsoft\GameBar' UseNexusForGameBarEnabled 0
Get-Process GameBar,GameBarFTServer -ErrorAction SilentlyContinue | Stop-Process -Force
Set-Content Z:\control\overlay-disabled.txt 'Game DVR capture and Game Bar startup tips disabled for guest user'
