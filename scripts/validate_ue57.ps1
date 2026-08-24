[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EngineRoot,
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\")).Path
$projectRoot = Join-Path $repoRoot "validation\UEKnowledgeValidation"
$uproject = Join-Path $projectRoot "UEKnowledgeValidation.uproject"
$registryPath = Join-Path $repoRoot "validation\fixture-registry.json"
$buildBat = Join-Path $EngineRoot "Engine\Build\BatchFiles\Build.bat"
$editor = Join-Path $EngineRoot "Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$buildVersionPath = Join-Path $EngineRoot "Engine\Build\Build.version"

foreach ($path in @($uproject, $registryPath, $buildBat, $editor, $buildVersionPath)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required UE validation path is missing: $path"
    }
}

$version = Get-Content -LiteralPath $buildVersionPath -Raw | ConvertFrom-Json
if ("$($version.MajorVersion).$($version.MinorVersion).$($version.PatchVersion)" -ne "5.7.4") {
    throw "Expected UE 5.7.4, found $($version.MajorVersion).$($version.MinorVersion).$($version.PatchVersion)"
}
if ([int]$version.Changelist -ne 51494982) {
    throw "Expected UE Changelist 51494982, found $($version.Changelist)"
}

$registry = Get-Content -LiteralPath $registryPath -Raw | ConvertFrom-Json
if ([int]$registry.schema_version -ne 2) {
    throw "Unsupported UE fixture registry schema"
}
if ("$($registry.engine.version)" -ne "5.7.4" -or [int]$registry.engine.changelist -ne 51494982) {
    throw "UE fixture registry does not target UE 5.7.4 / 51494982"
}
$fixtureRoot = (Resolve-Path $projectRoot).Path
$registryHash = (Get-FileHash -LiteralPath $registryPath -Algorithm SHA256).Hash.ToLowerInvariant()
$fixtureRecords = @()
$seenFixtureIds = @{}
foreach ($fixture in @($registry.fixtures)) {
    $id = "$($fixture.id)"
    $relative = "$($fixture.source)".Replace("/", "\")
    if (-not $id -or $seenFixtureIds.ContainsKey($id)) {
        throw "Fixture registry contains a missing or duplicate id"
    }
    $seenFixtureIds[$id] = $true
    $fixturePath = Join-Path $projectRoot $relative
    if (-not (Test-Path -LiteralPath $fixturePath -PathType Leaf)) {
        throw "Fixture source is missing: $relative"
    }
    $resolvedFixture = (Resolve-Path -LiteralPath $fixturePath).Path
    if (-not $resolvedFixture.StartsWith($fixtureRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Fixture source escapes the validation project: $relative"
    }
    $fixtureRecords += [ordered]@{
        id = $id
        source = $relative.Replace("\", "/")
        sha256 = (Get-FileHash -LiteralPath $resolvedFixture -Algorithm SHA256).Hash.ToLowerInvariant()
        symbols = @($fixture.symbols)
        covers_claims = @($fixture.covers_claims)
    }
}

if (-not $Output) {
    $Output = Join-Path $repoRoot "validation\artifacts\ue57"
}
$Output = [IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path $Output | Out-Null

$cleanArgs = @(
    "UEKnowledgeValidationEditor",
    "Win64",
    "Development",
    "-Project=$uproject",
    "-Clean",
    "-WaitMutex"
)
$buildCleanExit = 0
& $buildBat @cleanArgs
$buildCleanExit = $LASTEXITCODE
if ($buildCleanExit -ne 0) {
    throw "UEKnowledgeValidationEditor clean failed with exit code $buildCleanExit"
}

$buildArgs = @(
    "UEKnowledgeValidationEditor",
    "Win64",
    "Development",
    "-Project=$uproject",
    "-WaitMutex"
)
& $buildBat @buildArgs
$buildExit = $LASTEXITCODE
if ($buildExit -ne 0) {
    throw "UEKnowledgeValidationEditor build failed with exit code $buildExit"
}

$expectedFailureRecords = @()
$validationRoot = (Resolve-Path (Join-Path $repoRoot "validation")).Path
foreach ($probe in @($registry.expected_failures)) {
    $probeId = "$($probe.id)"
    $probeProjectRelative = "$($probe.project)".Replace("/", "\")
    $probeTarget = "$($probe.target)"
    $probeSourceRelative = "$($probe.source)".Replace("/", "\")
    $probeDiagnostic = "$($probe.diagnostic)"
    if (-not $probeId -or -not $probeProjectRelative -or -not $probeTarget -or -not $probeSourceRelative -or -not $probeDiagnostic) {
        throw "Expected-failure registry entries require id, project, target, source, and diagnostic"
    }
    $probeProject = [IO.Path]::GetFullPath((Join-Path $validationRoot $probeProjectRelative))
    $probeSource = [IO.Path]::GetFullPath((Join-Path $validationRoot $probeSourceRelative))
    if (-not $probeProject.StartsWith($validationRoot, [StringComparison]::OrdinalIgnoreCase) -or
        -not $probeSource.StartsWith($validationRoot, [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $probeProject -PathType Leaf) -or
        -not (Test-Path -LiteralPath $probeSource -PathType Leaf)) {
        throw "Expected-failure fixture path is missing or escapes validation/: $probeId"
    }
    $probeArgs = @(
        $probeTarget,
        "Win64",
        "Development",
        "-Project=$probeProject",
        "-WaitMutex"
    )
    $probeOutput = @(& $buildBat @probeArgs 2>&1 | ForEach-Object { "$_" })
    $probeExit = $LASTEXITCODE
    $probeText = $probeOutput -join "`n"
    $matched = $probeText -match $probeDiagnostic
    if ($probeExit -eq 0) {
        throw "Expected-failure probe compiled successfully: $probeId"
    }
    if (-not $matched) {
        throw "Expected-failure probe did not match its registered diagnostic: $probeId"
    }
    $expectedFailureRecords += [ordered]@{
        id = $probeId
        state = "ExpectedFailure"
        exit_code = [int]$probeExit
        diagnostic = $probeDiagnostic
        fixture_sha256 = (Get-FileHash -LiteralPath $probeSource -Algorithm SHA256).Hash.ToLowerInvariant()
        matched = $true
    }
}
$allExpectedFailuresPassed = $expectedFailureRecords.Count -eq @($registry.expected_failures).Count -and
    (@($expectedFailureRecords | Where-Object { -not $_.matched -or $_.exit_code -eq 0 }).Count -eq 0)

$execCmds = "Automation RunTests UEKnowledgeValidation; Quit"
$reportDir = Join-Path $Output "automation"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
& $editor $uproject "-unattended" "-nop4" "-nosplash" "-NullRHI" "-NoSound" `
    "-ExecCmds=$execCmds" "-TestExit=Automation Test Queue Empty" `
    "-ReportExportPath=$reportDir"
$testExit = $LASTEXITCODE
$reports = @(Get-ChildItem -LiteralPath $reportDir -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".json", ".xml", ".log") } |
    ForEach-Object {
        [IO.Path]::GetRelativePath($reportDir, $_.FullName).Replace("\\", "/")
    })

$automationIndex = Join-Path $reportDir "index.json"
$testRecords = @()
$registryTests = @{}
foreach ($registeredTest in @($registry.tests)) {
    $registryTests["$($registeredTest.id)"] = $registeredTest
}
if (Test-Path -LiteralPath $automationIndex -PathType Leaf) {
    $automationPayload = Get-Content -LiteralPath $automationIndex -Raw | ConvertFrom-Json
    foreach ($test in @($automationPayload.tests)) {
        $registered = $registryTests["$($test.fullTestPath)"]
        if ($null -eq $registered) {
            throw "Automation test is not declared in fixture registry: $($test.fullTestPath)"
        }
        $testRecords += [ordered]@{
            id = "$($test.fullTestPath)"
            state = "$($test.state)"
            duration = [double]$test.duration
            warnings = [int]$test.warnings
            errors = [int]$test.errors
            assertions = @($registered.assertions)
            covers_claims = @($registered.covers_claims)
        }
    }
}
$allTestsPassed = $testRecords.Count -gt 0 -and (@($testRecords | Where-Object { $_.state -ne "Success" }).Count -eq 0)
$allTestsClean = $testRecords.Count -gt 0 -and (@($testRecords | Where-Object { $_.warnings -ne 0 -or $_.errors -ne 0 }).Count -eq 0)
$compileRecords = @($fixtureRecords | ForEach-Object {
    [ordered]@{
        id = $_.id
        state = if ($buildExit -eq 0) { "Success" } else { "Failure" }
        fixture_sha256 = $_.sha256
        symbols = @($_.symbols)
        covers_claims = @($_.covers_claims)
    }
})
$fixtureHashes = [ordered]@{}
foreach ($fixture in $fixtureRecords) {
    $fixtureHashes[$fixture.id] = $fixture.sha256
}
$validationIds = @($compileRecords.id + $testRecords.id | Sort-Object -Unique)
$reportHashes = [ordered]@{}
foreach ($report in @(Get-ChildItem -LiteralPath $reportDir -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".json", ".xml", ".log") })) {
    $relative = [IO.Path]::GetRelativePath($reportDir, $report.FullName).Replace("\", "/")
    $reportHashes[$relative] = (Get-FileHash -LiteralPath $report.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}

$evidence = [ordered]@{
    schema_version = 1
    validation = "UEKnowledgeValidation"
    engine = [ordered]@{
        version = "$($version.MajorVersion).$($version.MinorVersion).$($version.PatchVersion)"
        changelist = [int]$version.Changelist
        # Keep evidence portable and free of machine-specific paths.
        root = "<UE_ENGINE_ROOT>"
    }
    build_exit_code = $buildExit
    automation_exit_code = $testExit
    reports = $reports
    report_sha256 = $reportHashes
    fixture_registry_sha256 = $registryHash
    fixture_hashes = $fixtureHashes
    compile_validations = $compileRecords
    tests = $testRecords
    expected_failures = $expectedFailureRecords
    validation_ids = $validationIds
    passed = ($buildExit -eq 0 -and $testExit -eq 0 -and $reports.Count -gt 0 -and $allTestsPassed -and $allTestsClean -and $allExpectedFailuresPassed)
    generated_at = [DateTime]::UtcNow.ToString("o")
}
$evidencePath = Join-Path $Output "ue57-validation-evidence.json"
$evidence | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $evidencePath -Encoding utf8
Write-Output ($evidence | ConvertTo-Json -Depth 6)
if (-not $evidence.passed) {
    exit 1
}
