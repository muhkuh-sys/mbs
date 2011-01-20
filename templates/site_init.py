# -*- coding: utf-8 -*-


# ${NOTE}


# Define where all the depacked tools are.
TOOLS=${TOOLS}

# Define the project version.
PROJECT_VERSION='${PROJECT_VERSION}'

# Define the root of the build system.
MBS_DIR='${MBS_DIR}'

# Add the modules from the build system.
SCons.Script.Main._load_site_scons_dir(Dir('${MBS_DIR}'), 'site_scons')
