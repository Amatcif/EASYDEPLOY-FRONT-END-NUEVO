$ErrorActionPreference = "Stop"

$GitDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $GitDir
$ShortcutDir = Join-Path $GitDir "Accesos con iconos"
$IconsDir = Join-Path $GitDir "icons"

New-Item -ItemType Directory -Force -Path $ShortcutDir | Out-Null

$items = @(
    @{
        Name = "01 GIT - ANTES de Codex"
        Target = "01_GIT_ANTES_DE_CODEX.bat"
        Icon = "git_antes.ico"
        Description = "Guardar checkpoint antes de pedir cambios a Codex"
    },
    @{
        Name = "02 GIT - DESPUES de probar"
        Target = "02_GIT_DESPUES_DE_PROBAR.bat"
        Icon = "git_despues.ico"
        Description = "Guardar checkpoint despues de probar que la app funciona"
    },
    @{
        Name = "03 GIT - VER checkpoints"
        Target = "03_GIT_VER_CHECKPOINTS.bat"
        Icon = "git_ver.ico"
        Description = "Ver lista de checkpoints guardados"
    },
    @{
        Name = "04 GIT - VOLVER a checkpoint"
        Target = "04_GIT_VOLVER_A_CHECKPOINT.bat"
        Icon = "git_volver.ico"
        Description = "Volver a una version anterior del proyecto"
    },
    @{
        Name = "05 GIT - RESTAURAR backup previo"
        Target = "05_GIT_RESTAURAR_BACKUP_PREVIO.bat"
        Icon = "git_backup.ico"
        Description = "Deshacer una vuelta atras restaurando backup previo"
    }
)

$Shell = New-Object -ComObject WScript.Shell

foreach ($item in $items) {
    $targetPath = Join-Path $GitDir $item.Target
    $iconPath = Join-Path $IconsDir $item.Icon
    $shortcutPath = Join-Path $ShortcutDir ($item.Name + ".lnk")

    if (!(Test-Path $targetPath)) {
        Write-Host "No existe: $targetPath" -ForegroundColor Yellow
        continue
    }

    $shortcut = $Shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $targetPath
    $shortcut.WorkingDirectory = $ProjectRoot
    $shortcut.Description = $item.Description
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = $iconPath
    }
    $shortcut.Save()
}

Write-Host ""
Write-Host "Accesos directos creados en:" -ForegroundColor Green
Write-Host $ShortcutDir
Write-Host ""
Write-Host "Puedes usar esos accesos. Los .bat estan dentro de la carpeta GIT y trabajan sobre la carpeta superior del proyecto." -ForegroundColor Green
