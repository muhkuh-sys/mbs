# -*- coding: utf-8 -*-


# ${NOTE}


import os
import os.path

# Make sure that the target folder exists.
if os.path.exists('targets')!=True:
    os.mkdir('targets')
# Move the SCons database to the targets folder.
SCons.SConsign.DB_Name = 'targets/.sconsign'

# Define where all the depacked tools are.
TOOLS=${TOOLS}

# Define the project version.
PROJECT_VERSION='${PROJECT_VERSION}'

# Define the root of the build system.
MBS_DIR='${MBS_DIR}'
