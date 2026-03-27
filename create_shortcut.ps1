# PowerShell script to create a proper Windows desktop shortcut
# for Parts Agent Pro with icon

$WScriptShell = New-Object -ComObject WScript.Shell
$Shortcut = $WScriptShell.CreateShortcut("$env:USERPROFILE\Desktop\Parts Agent Pro.lnk")

# Set the target to the batch file
$Shortcut.TargetPath = "$env:USERPROFILE\Desktop\Parts Agent 20260313\Parts Agent Pro.bat"

# Set working directory
$Shortcut.WorkingDirectory = "$env:USERPROFILE\Desktop\Parts Agent 20260313"

# Set description
$Shortcut.Description = "Parts Agent Pro - Unified Auto Parts Matching Application"

# Set icon (use Python icon or default batch icon)
$Shortcut.IconLocation = "C:\Python314\python.exe,0"

# Save the shortcut
$Shortcut.Save()

Write-Host "Desktop shortcut created: Parts Agent Pro.lnk"