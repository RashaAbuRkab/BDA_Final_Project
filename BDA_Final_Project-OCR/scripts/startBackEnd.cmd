@echo off
setlocal

set "WORKINGDIRECTORY=C:\Users\hp\Desktop\All\college\Fourth_year\Second_term\Big_Data\BDA_Final_Project-OCR\BDA_Final_Project-main"

set "VENV=D:\WPy64-3.13.12.0\notebooks\envs\bigdata"

cd /d "%WORKINGDIRECTORY%"
call "%VENV%\Scripts\activate.bat"

rem optional sanity checks
python -V
where python

rem To start Jupyter or any other service in this venv
::jupyter notebook

uvicorn backend.main:app --reload