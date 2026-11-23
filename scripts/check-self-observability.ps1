param(
  [string]$PrometheusUrl = "http://localhost:9090",
  [string]$CollectionUrl = "http://localhost:8001"
)
$ErrorActionPreference = "Stop"
Invoke-RestMethod "$CollectionUrl/health" | Out-Null
Write-Host "PASS Collection health"
Invoke-RestMethod "$PrometheusUrl/-/ready" | Out-Null
Write-Host "PASS Prometheus ready"
$result = Invoke-RestMethod "$PrometheusUrl/api/v1/query?query=up%7Bjob%3D%22logiq-apis%22%2Cinstance%3D%22collection%3A8000%22%7D"
if ($result.data.result.Count -eq 0 -or $result.data.result[0].value[1] -ne "1") { throw "Collection target is not up in Prometheus" }
Write-Host "PASS Prometheus independently scrapes Collection"
