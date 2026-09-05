param([string]$Url)
# DHL Code Helper (silent): receives the dhllogin:// redirect URL from the
# browser and writes it to a file so the setup can read the authorization
# code. No UI, so it doesn't block or spawn extra windows.
try {
    $Url | Out-File -FilePath "$PSScriptRoot\letzter-code.txt" -Encoding utf8 -Force
} catch {}
try { Set-Clipboard -Value $Url } catch {}
