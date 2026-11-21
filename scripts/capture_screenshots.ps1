param(
  [string]$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe",
  [string]$ScratchDir = "C:\Users\alase\.gemini\antigravity\brain\59bf335f-058f-479b-ae36-cfba82f29eb2\scratch",
  [string]$DestDir = "D:\Align final\Align\docs\screenshots"
)

$pages = @(
  @{ Name = "landing"; Path = "/" },
  @{ Name = "login"; Path = "/login" },
  @{ Name = "register"; Path = "/register" },
  @{ Name = "discover"; Path = "/discover" },
  @{ Name = "communities"; Path = "/communities" },
  @{ Name = "events"; Path = "/events" },
  @{ Name = "settings"; Path = "/settings" }
)

$viewports = @(
  @{ Name = "desktop"; Size = "1440,900" },
  @{ Name = "mobile"; Size = "390,844" }
)

$themes = @("dark", "light")

New-Item -ItemType Directory -Path $ScratchDir -Force | Out-Null
New-Item -ItemType Directory -Path $DestDir -Force | Out-Null

foreach ($page in $pages) {
  foreach ($vp in $viewports) {
    foreach ($th in $themes) {
      $fileName = "$($page.Name)_$($vp.Name)_$($th).png"
      $scratchFile = "$ScratchDir\$fileName"
      $sep = if ($page.Path.Contains("?")) { "&" } else { "?" }
      $url = "http://localhost:5173$($page.Path)$($sep)theme=$th"
      
      Write-Host "Capturing $fileName from $url at $($vp.Size) ($th)..."
      
      $args = @(
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--force-prefers-color-scheme=$th",
        "--window-size=$($vp.Size)",
        "--virtual-time-budget=2000",
        "--screenshot=$scratchFile",
        $url
      )
      
      Start-Process -FilePath $ChromePath -ArgumentList $args -Wait
      
      if (Test-Path $scratchFile) {
        $destFile = "$DestDir\$fileName"
        Copy-Item -Path $scratchFile -Destination $destFile -Force
        $len = (Get-Item $destFile).Length
        Write-Host " Saved: $fileName ($len bytes)"
      } else {
        Write-Warning " Failed to capture: $fileName"
      }
    }
  }
}

Write-Host "Screenshot capture complete!"
