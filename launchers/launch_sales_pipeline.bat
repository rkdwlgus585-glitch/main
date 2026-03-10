@echo off
:: [ROLE] REAL_LAUNCHER - sales pipeline with passthrough args
setlocal
cd /d "%~dp0.."
python ..\ALL\sales_pipeline.py %*
