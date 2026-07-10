# FinAlly - stop script (Windows PowerShell)
# Stops and removes the container. The named volume (finally-data) is kept so
# the portfolio, watchlist, and trade history survive across restarts.

$Container = "finally"

Write-Host "Stopping FinAlly container..." -ForegroundColor Yellow
docker stop $Container 2>$null | Out-Null
docker rm $Container 2>$null | Out-Null

Write-Host "FinAlly stopped. Data persists in the 'finally-data' volume." -ForegroundColor Green
Write-Host "To remove all saved data: docker volume rm finally-data" -ForegroundColor Cyan
