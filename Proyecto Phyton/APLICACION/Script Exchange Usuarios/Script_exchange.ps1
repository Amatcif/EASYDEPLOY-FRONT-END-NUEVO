param(
    [string]$CsvPath = $(Join-Path $PSScriptRoot 'matriz_usuarios.csv')
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$ErrorActionPreference = 'Continue'

$created = New-Object System.Collections.Generic.List[object]
$failed = New-Object System.Collections.Generic.List[object]

function Write-Step {
    param([string]$Message)
    Write-Output $Message
}

function Add-Failed {
    param([string]$Email, [string]$Name, [string]$Reason)
    $script:failed.Add([pscustomobject]@{
        Email = $Email
        Name = $Name
        Reason = $Reason
    }) | Out-Null
    Write-Output "[FALLIDO] $Email -> $Reason"
}

function Initialize-ExchangeShell {
    if (Get-Command New-Mailbox -ErrorAction SilentlyContinue) { return $true }
    if (Get-Command Enable-Mailbox -ErrorAction SilentlyContinue) { return $true }

    try {
        if ($env:ExchangeInstallPath) {
            $remote = Join-Path $env:ExchangeInstallPath 'bin\RemoteExchange.ps1'
            if (Test-Path $remote) {
                . $remote
                Connect-ExchangeServer -auto -ClientApplication:ManagementShell -ErrorAction SilentlyContinue | Out-Null
            }
        }
    } catch { }

    if (Get-Command Enable-Mailbox -ErrorAction SilentlyContinue) { return $true }

    try { Add-PSSnapin Microsoft.Exchange.Management.PowerShell.SnapIn -ErrorAction SilentlyContinue } catch { }
    return [bool](Get-Command Enable-Mailbox -ErrorAction SilentlyContinue)
}

function Escape-LdapFilterValue {
    param([string]$Value)
    if ($null -eq $Value) { return '' }
    $text = [string]$Value
    $text = $text.Replace('\', '\5c')
    $text = $text.Replace('*', '\2a')
    $text = $text.Replace('(', '\28')
    $text = $text.Replace(')', '\29')
    $text = $text.Replace(([string][char]0), '\00')
    return $text
}

function ConvertTo-DomainDn {
    param([string]$DomainName)
    $parts = @($DomainName.Split('.') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
    if ($parts.Count -eq 0) { throw "Dominio no valido: $DomainName" }
    return (($parts | ForEach-Object { 'DC=' + $_ }) -join ',')
}

function Get-WriteDomainController {
    param([string]$DomainName)
    try {
        $domain = Get-ADDomain -Identity $DomainName -ErrorAction Stop
        if ($domain.PDCEmulator) { return [string]$domain.PDCEmulator }
    } catch { }

    $dc = Get-ADDomainController -DomainName $DomainName -Discover -Writable -ErrorAction Stop
    return [string]$dc.HostName
}

function Test-AdObjectExists {
    param([string]$Identity, [string]$Server)
    try {
        $null = Get-ADObject -Identity $Identity -Server $Server -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Resolve-TargetContainerDn {
    param(
        [string]$RawOu,
        [string]$DomainName,
        [string]$Server
    )

    $domainDn = ConvertTo-DomainDn -DomainName $DomainName
    $defaultContainer = "CN=Users,$domainDn"
    $raw = ([string]$RawOu).Trim()
    $domainShort = ($DomainName.Split('.')[0])

    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $defaultContainer
    }

    # Si el usuario escribe solo ET, et.ms.esp, Users o User, se fuerza el contenedor correcto de usuarios.
    if ($raw -ieq $domainShort -or $raw -ieq $DomainName -or $raw -ieq 'Users' -or $raw -ieq 'User') {
        return $defaultContainer
    }

    # Distinguished Name directo: OU=Usuarios,DC=et,DC=ms,DC=esp o CN=Users,DC=...
    if ($raw -match '(?i)(^|,)(OU|CN|DC)=') {
        if (Test-AdObjectExists -Identity $raw -Server $Server) { return $raw }
        throw "No existe en Active Directory la ruta DN indicada: $raw"
    }

    # Ruta canonica: et.ms.esp/Users, et.ms.esp/User, et.ms.esp/OU1/OU2
    $canonical = $raw -replace '\\', '/'
    if ($canonical.Contains('/')) {
        $parts = @($canonical.Split('/') | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($parts.Count -eq 0) { return $defaultContainer }

        $canonicalDomain = $DomainName
        $containerParts = $parts
        if ($parts[0] -match '\.') {
            $canonicalDomain = $parts[0]
            if ($parts.Count -gt 1) {
                $containerParts = @($parts[1..($parts.Count - 1)])
            } else {
                $containerParts = @()
            }
        }

        if ($containerParts.Count -eq 0) { return $defaultContainer }

        $candidateDomainDn = ConvertTo-DomainDn -DomainName $canonicalDomain
        $dnParts = New-Object System.Collections.Generic.List[string]
        for ($i = $containerParts.Count - 1; $i -ge 0; $i--) {
            $part = [string]$containerParts[$i]
            if ($part -ieq 'Users' -or $part -ieq 'User') {
                $dnParts.Add('CN=Users') | Out-Null
            } else {
                $dnParts.Add(('OU=' + $part)) | Out-Null
            }
        }
        $candidate = (($dnParts.ToArray()) -join ',') + ',' + $candidateDomainDn
        if (Test-AdObjectExists -Identity $candidate -Server $Server) { return $candidate }
        throw "No existe la OrganizationalUnit/contenedor indicado: $raw. Usa por ejemplo $DomainName/Users o una OU real."
    }

    # Nombre simple de OU/contenedor: se acepta solo si es unico en el dominio.
    $escaped = Escape-LdapFilterValue $raw
    $matches = @(Get-ADObject -LDAPFilter "(|(&(objectClass=organizationalUnit)(ou=$escaped))(&(objectClass=container)(cn=$escaped)))" -SearchBase $domainDn -Server $Server -ErrorAction SilentlyContinue | Select-Object -First 2)
    if ($matches.Count -eq 1) { return [string]$matches[0].DistinguishedName }
    if ($matches.Count -gt 1) { throw "La ruta '$raw' es ambigua. Escribe la ruta completa, por ejemplo $DomainName/Users." }

    throw "No existe la OrganizationalUnit/contenedor '$raw'. Usa por ejemplo $DomainName/Users."
}

function New-SamAccountName {
    param([string]$Email)
    $local = ($Email -split '@')[0]
    $clean = $local -replace '[^A-Za-z0-9._-]', ''
    $clean = $clean.Trim('._-')
    if ([string]::IsNullOrWhiteSpace($clean)) {
        $clean = 'user' + ([guid]::NewGuid().ToString('N').Substring(0, 8))
    }
    if ($clean.Length -gt 20) { $clean = $clean.Substring(0, 20) }
    return $clean
}

function Try-SyncAdReplication {
    param([string]$Server)
    try {
        $repadmin = Get-Command repadmin.exe -ErrorAction SilentlyContinue
        if ($repadmin) {
            Write-Output "[INFO] Solicitando sincronizacion AD desde $Server..."
            & repadmin.exe /syncall $Server /AdeP 2>$null | Out-String | ForEach-Object { $_.TrimEnd() } | Where-Object { $_ } | Write-Output
        }
    } catch { }
}

try {
    if (-not (Test-Path -LiteralPath $CsvPath)) {
        throw "No existe el archivo de usuarios: $CsvPath"
    }

    $users = @(Import-Csv -LiteralPath $CsvPath)
    if ($users.Count -eq 0) {
        throw 'El archivo de usuarios no contiene filas.'
    }

    Write-Step 'Inicializando Exchange Management Shell...'
    if (-not (Initialize-ExchangeShell)) {
        throw 'No se han podido cargar los cmdlets de Exchange. Ejecuta esta tarea en la MV de Exchange con Exchange instalado.'
    }

    try { Import-Module ActiveDirectory -ErrorAction Stop } catch {
        throw 'No se pudo cargar el modulo ActiveDirectory. Instala RSAT-ADDS-Tools o ejecuta desde un servidor con herramientas AD.'
    }

    Write-Output "[INFO] Usuarios a procesar: $($users.Count)"
    $usedDcs = New-Object System.Collections.Generic.HashSet[string]

    foreach ($user in $users) {
        $email = ([string]$user.Email).Trim().ToLowerInvariant()
        $firstName = ([string]$user.FirstName).Trim()
        $ou = ([string]$user.OrganizationalUnit).Trim()
        $plainPassword = [string]$user.Password

        Write-Output "[USUARIO] $email"

        if ([string]::IsNullOrWhiteSpace($email) -or [string]::IsNullOrWhiteSpace($firstName) -or [string]::IsNullOrWhiteSpace($plainPassword)) {
            Add-Failed -Email $email -Name $firstName -Reason 'Datos incompletos: Email, FirstName y Password son obligatorios.'
            continue
        }
        if ($email -notmatch '^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$') {
            Add-Failed -Email $email -Name $firstName -Reason 'Email no valido.'
            continue
        }

        try {
            $domainName = ($email -split '@', 2)[1]
            $writeDc = Get-WriteDomainController -DomainName $domainName
            $null = $usedDcs.Add($writeDc)
            $targetContainerDn = Resolve-TargetContainerDn -RawOu $ou -DomainName $domainName -Server $writeDc
            $sam = New-SamAccountName -Email $email
            $alias = $sam

            Write-Output "[AD] Controlador usado: $writeDc"
            Write-Output "[AD] Contenedor destino: $targetContainerDn"

            $escapedEmail = Escape-LdapFilterValue $email
            $escapedSam = Escape-LdapFilterValue $sam
            $domainDn = ConvertTo-DomainDn -DomainName $domainName
            $existingAd = Get-ADUser -LDAPFilter "(|(userPrincipalName=$escapedEmail)(mail=$escapedEmail)(sAMAccountName=$escapedSam))" -SearchBase $domainDn -Server $writeDc -Properties mail,userPrincipalName,distinguishedName -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($existingAd) {
                Add-Failed -Email $email -Name $firstName -Reason "Ya existe un usuario en AD: $($existingAd.DistinguishedName)"
                continue
            }

            $existingRecipient = Get-Recipient -Identity $email -DomainController $writeDc -ErrorAction SilentlyContinue
            if ($existingRecipient) {
                Add-Failed -Email $email -Name $firstName -Reason 'Ya existe un destinatario o buzon en Exchange.'
                continue
            }

            $securePassword = ConvertTo-SecureString $plainPassword -AsPlainText -Force
            New-ADUser `
                -Name $firstName `
                -DisplayName $firstName `
                -GivenName $firstName `
                -UserPrincipalName $email `
                -SamAccountName $sam `
                -Path $targetContainerDn `
                -AccountPassword $securePassword `
                -Enabled $true `
                -ChangePasswordAtLogon $false `
                -Server $writeDc `
                -ErrorAction Stop

            $adUser = Get-ADUser -Identity $sam -Server $writeDc -Properties DistinguishedName,UserPrincipalName,mail,Enabled -ErrorAction Stop
            if (-not $adUser) { throw 'New-ADUser no devolvio un usuario verificable.' }
            Write-Output "[OK] Usuario AD creado: $($adUser.DistinguishedName)"

            try {
                Enable-Mailbox -Identity $adUser.DistinguishedName -Alias $alias -DomainController $writeDc -ErrorAction Stop | Out-Null
            } catch {
                throw "Usuario AD creado, pero no se pudo habilitar el buzon: $($_.Exception.Message)"
            }

            try {
                Set-Mailbox -Identity $adUser.DistinguishedName -PrimarySmtpAddress $email -EmailAddressPolicyEnabled $false -DomainController $writeDc -ErrorAction Stop | Out-Null
            } catch {
                Write-Output "[AVISO] Buzon habilitado, pero no se pudo fijar PrimarySmtpAddress manualmente: $($_.Exception.Message)"
            }

            try {
                Set-ADUser -Identity $adUser.DistinguishedName -EmailAddress $email -Server $writeDc -ErrorAction SilentlyContinue
            } catch { }

            $mailbox = Get-Mailbox -Identity $email -DomainController $writeDc -ErrorAction Stop
            if (-not $mailbox) { throw 'No se pudo verificar el buzon despues de habilitarlo.' }

            $created.Add([pscustomobject]@{ Email = $email; Name = $firstName; DistinguishedName = $adUser.DistinguishedName; DomainController = $writeDc }) | Out-Null
            Write-Output "[OK] Buzon Exchange habilitado: $email"
        } catch {
            Add-Failed -Email $email -Name $firstName -Reason $_.Exception.Message
        }
    }

    foreach ($dc in $usedDcs) { Try-SyncAdReplication -Server $dc }

    Write-Output ''
    Write-Output '=== RESUMEN EASY DEPLOY EXCHANGE ==='
    Write-Output "Creados: $($created.Count)"
    foreach ($item in $created) {
        Write-Output "CREADO|$($item.Email)|$($item.Name)"
        Write-Output "ADPATH|$($item.Email)|$($item.DistinguishedName)|$($item.DomainController)"
    }
    Write-Output "Fallidos: $($failed.Count)"
    foreach ($item in $failed) {
        Write-Output "FALLIDO|$($item.Email)|$($item.Name)|$($item.Reason)"
    }

    if ($failed.Count -gt 0) { exit 1 }
    exit 0
} catch {
    Write-Output "[ERROR] $($_.Exception.Message)"
    exit 10
}
