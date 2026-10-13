@echo off
setlocal
pushd "%~dp0.."
set "LAB_PYTHON=%CD%\.venv\Scripts\python.exe"
if not exist "%LAB_PYTHON%" goto no_python
set "MPLBACKEND=Agg"
set "MPLCONFIGDIR=%CD%\.venv\matplotlib-cache"
"%LAB_PYTHON%" -m pytest -q
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/run_gameday.py --client both
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/run_workflows.py --executor both
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/run_slo.py --alerter both
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/run_gameday.py --scenarios configs/scenarios_cache.yaml --client resilient,cached --out reports/cache
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/run_experiments.py
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/plot_timeseries.py --scenario G2_overload_storm
if errorlevel 1 goto failed
"%LAB_PYTHON%" scripts/grade.py --seeds 25,26,27
if errorlevel 1 goto failed
"%LAB_PYTHON%" -c "import json; b=json.load(open('reports/scoreboard.json')); assert b['summary']['automatic'] >= 84, 'Public checks did not all pass'"
if errorlevel 1 goto failed
echo All public checks passed. See reports/REPORT.md and reports/scoreboard.json.
popd
exit /b 0
:no_python
echo Create .venv and install .[dev,plot] first. See reports/REPORT.md.
:failed
popd
exit /b 1
