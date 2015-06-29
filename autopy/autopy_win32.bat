@echo off
rem This script searches a suitable python interpreter.

setlocal ENABLEEXTENSIONS


rem First try the registry
set strPath=
set strVersionMaj=
set KEY_NAME="HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Python.exe"
FOR /F "usebackq tokens=3" %%A IN (`reg query %KEY_NAME%`) DO (
	set strPath=%%A
)
if defined strPath (
	FOR /F "usebackq" %%B in (`%strPath% -c "import sys; print sys.version_info.major"`) DO (
		set strVersionMaj=%%B
	)
)
if "%strVersionMaj%" == "2" (
	set strPythonPath=%strPath%
)


rem Try a known location.
if not defined strPythonPath (
	set strPath=
	set strVersionMaj=
	set strPath=C:\Python27\python.exe
	FOR /F "usebackq" %%B in (`%strPath% -c "import sys; print sys.version_info.major"`) DO (
		set strVersionMaj=%%B
	)
	if "%strVersionMaj%" == "2" (
		set strPythonPath=%strPath%
	)
)


rem Found a python version?
if not defined strPythonPath (
	echo "No suitable Python interpreter found!"
	exit /b
)


rem Call the Python interpreter.
%strPythonPath% %*
endlocal
