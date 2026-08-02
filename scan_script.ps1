$outputFile = "C:\LocalAI_Workstation\module_mapping_scan.txt"

Write-Output "--- 1. 全机搜尋底線版與無底線版檔名 ---" | Out-File $outputFile
$targets = @(
  "process_video.py","processvideo.py",
  "vad_chunker.py","vadchunker.py",
  "error_analyzer.py","erroranalyzer.py",
  "config.py",
  "stt_runner.py","sttrunner.py",
  "merge_transcript.py","mergetranscript.py",
  "markdown_formatter.py","markdownformatter.py",
  "run_workflow.py","runworkflow.py"
)
Get-ChildItem "C:\LocalAI_Workstation" -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $targets -contains $_.Name } |
  Sort-Object Name, FullName |
  Select-Object Name, FullName, DirectoryName, Length, LastWriteTime | Format-Table -AutoSize | Out-File $outputFile -Append

Write-Output "`n--- 2. 逐一统计每种名称出现次数 ---" | Out-File $outputFile -Append
$targets | ForEach-Object {
  $count = (Get-ChildItem "C:\LocalAI_Workstation" -Recurse -File -Filter $_ -ErrorAction SilentlyContinue | Measure-Object).Count
  [PSCustomObject]@{ Name = $_; Count = $count }
} | Format-Table -AutoSize | Out-File $outputFile -Append

Write-Output "`n--- 3. 找出最可能的“完整模块组”目录 ---" | Out-File $outputFile -Append
$groups = Get-ChildItem "C:\LocalAI_Workstation" -Recurse -File -ErrorAction SilentlyContinue | Group-Object DirectoryName

$wantSets = @(
  @("run_workflow.py","process_video.py","vad_chunker.py","stt_runner.py","merge_transcript.py","markdown_formatter.py","error_analyzer.py","config.py"),
  @("runworkflow.py","processvideo.py","vadchunker.py","sttrunner.py","mergetranscript.py","markdownformatter.py","erroranalyzer.py","config.py")
)

foreach ($g in $groups) {
  $names = $g.Group.Name
  foreach ($set in $wantSets) {
    $missing = $set | Where-Object { $_ -notin $names }
    if ($missing.Count -le 2) {
      [PSCustomObject]@{
        Directory = $g.Name
        Present = ($set | Where-Object { $_ -in $names }) -join ", "
        Missing = $missing -join ", "
      } | Format-Table -AutoSize | Out-File $outputFile -Append
    }
  }
}

Write-Output "`n--- 4. 撷取无底线档案 (processvideo.py 等) 前 80 行 ---" | Out-File $outputFile -Append
$alts = @("processvideo.py","vadchunker.py","erroranalyzer.py")
Get-ChildItem "C:\LocalAI_Workstation" -Recurse -File -ErrorAction SilentlyContinue |
  Where-Object { $alts -contains $_.Name } |
  Select-Object -First 10 |
  ForEach-Object {
    Write-Output "===== FILE: $($_.FullName) =====" | Out-File $outputFile -Append
    Get-Content $_.FullName -TotalCount 80 -Encoding UTF8 | Out-File $outputFile -Append
  }

Write-Output "`n--- 5. 撷取目前 scripts_v6\run_workflow.py 前 100 行 ---" | Out-File $outputFile -Append
Get-Content "C:\LocalAI_Workstation\scripts_v6\run_workflow.py" -TotalCount 100 -Encoding UTF8 | Out-File $outputFile -Append
