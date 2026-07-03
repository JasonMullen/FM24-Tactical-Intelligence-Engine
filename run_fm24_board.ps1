$ProjectDir = "C:\Users\jason\OneDrive\Attachments\Desktop\FM24_Tactical_Intelligence_Engine_Framework"
$PythonExe = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$Url = "http://localhost:8501"

Set-Location $ProjectDir

Write-Host ""
Write-Host "Starting FM24 Tactical Intelligence Engine..." -ForegroundColor Green
Write-Host "Project: $ProjectDir" -ForegroundColor Cyan
Write-Host "URL: $Url" -ForegroundColor Cyan
Write-Host ""
Write-Host "Do not close this PowerShell window while using the board." -ForegroundColor Yellow
Write-Host ""

Start-Process $Url

& $PythonExe -m streamlit run app\dashboard.py --server.address localhost --server.port 8501
