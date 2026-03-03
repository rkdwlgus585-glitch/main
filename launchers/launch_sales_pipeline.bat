@echo off
:: [ROLE] REAL_LAUNCHER - sales pipeline with passthrough args
setlocal
cd /d "%~dp0.."
python sales_pipeline.py %*
