# Raspberry Pi
$PI_USER = "pi"
$PI_HOST = "192.168.0.91"

Write-Host "=== Stop JellyLab ==="
ssh $PI_USER@$PI_HOST "sudo systemctl stop jellylab"

Write-Host "=== Uploading ==="
scp app.py                           $PI_USER@${PI_HOST}:~/Projects/JellyLab/
scp config.py                        $PI_USER@${PI_HOST}:~/Projects/JellyLab/

scp -r camera                        $PI_USER@${PI_HOST}:~/Projects/JellyLab/
scp -r sensors                       $PI_USER@${PI_HOST}:~/Projects/JellyLab/
scp -r managers                      $PI_USER@${PI_HOST}:~/Projects/JellyLab/
scp -r utils                         $PI_USER@${PI_HOST}:~/Projects/JellyLab/
scp -r templates                     $PI_USER@${PI_HOST}:~/Projects/JellyLab/
scp -r static                        $PI_USER@${PI_HOST}:~/Projects/JellyLab/

if ($LASTEXITCODE -ne 0) {
    Write-Host "Upload failed!"
    exit
}

Write-Host "=== Start JellyLab ==="
ssh $PI_USER@$PI_HOST "sudo systemctl start jellylab"

Write-Host "=== Status ==="
ssh $PI_USER@$PI_HOST "systemctl status jellylab --no-pager"

Write-Host "=== Log ==="
ssh $PI_USER@$PI_HOST "journalctl -u jellylab -n 30 --no-pager"
