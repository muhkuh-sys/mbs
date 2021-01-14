#! /bin/bash

# This script searches a suitable python interpreter.

# These are the known locations for the python interpreter.
astrPythonLocations=(
	'python3'
	'python'
)

strPythonPath=''
for strPythonLocation in "${astrPythonLocations[@]}"
do
	echo "[autopy] Trying '${strPythonLocation}'..."
	strPath=$(which ${strPythonLocation})
	if [ -n "${strPath}" ]; then
		# Get the version number from the interpreter.
		strVersion=$(${strPath} --version 2>&1)
		echo "[autopy] Found '${strPythonLocation}' with version '${strVersion}'."
		if [[ "$strVersion" =~ Python\ 3\.[0-9]+\.[0-9]+ ]]; then
			echo "[autopy] Found a python 3.x interpreter: '${strPath}'"
			strPythonPath=${strPath}
			break
		else
			echo "[autopy] Ignoring interpreter as it is not v3.x: '${strPath}'"
		fi
	fi
done

if [ -z "$strPythonPath" ]; then
	echo "No Python interpreter found!"
	exit 1
else
	${strPythonPath} $@
fi
