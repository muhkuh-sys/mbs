# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2011 by Christoph Thelen                                #
#   doc_bacardi@users.sourceforge.net                                     #
#                                                                         #
#   This program is free software; you can redistribute it and/or modify  #
#   it under the terms of the GNU General Public License as published by  #
#   the Free Software Foundation; either version 2 of the License, or     #
#   (at your option) any later version.                                   #
#                                                                         #
#   This program is distributed in the hope that it will be useful,       #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#   GNU General Public License for more details.                          #
#                                                                         #
#   You should have received a copy of the GNU General Public License     #
#   along with this program; if not, write to the                         #
#   Free Software Foundation, Inc.,                                       #
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             #
#-------------------------------------------------------------------------#

# Try to load the global build_properties first.
try:
	import build_properties
except ImportError:
	pass


# Add the local site_scons folder to the search path.
from SCons.Script.Main import _load_site_scons_dir
# NOTE: why do I have to use '#' here?
_load_site_scons_dir(Dir('#'), 'site_scons')

# Import all local modules.
import bootblock
import build_properties
import data_array
import diff
import gen_random_seq
import scons_common
import svnversion
import uuencode


build_properties.Read()

#----------------------------------------------------------------------------
#
# set help text
#
Help("""
This SConstruct file is part of a Muhkuh buildsystem project. Run

  'python path_to_setup.py'

from your project's root folder to setup the project environment. This will
also download all missing tools.
""")

build_properties.GenerateHelp()


#----------------------------------------------------------------------------


default_ccflags = """
	-ffreestanding
	-mlong-calls
	-Wall
	-Wextra
	-Wconversion
	-Wshadow
	-Wcast-qual
	-Wwrite-strings
	-Wcast-align
	-Wpointer-arith
	-Wmissing-prototypes
	-Wstrict-prototypes
	-mapcs
	-g3
	-gdwarf-2
	-std=c99
	-pedantic
"""


# Show summary of the build properties.
build_properties.PrintSummary()


#----------------------------------------------------------------------------
#
# Import the tool definitions.
#
gcc_arm = scons_common.get_tool('gcc-arm-none-eabi-4.5.1_1')
asciidoc = scons_common.get_tool('asciidoc-8.6.3_2')


#----------------------------------------------------------------------------
#
# Create the default environment and apply the compiler.
#
env_default = Environment()
gcc_arm.ApplyToEnv(env_default)
env_default.Decider('MD5')
env_default.Replace(CCFLAGS = Split(default_ccflags))
env_default.Replace(LIBS = ['m', 'c', 'gcc'])
env_default.Replace(LINKFLAGS = ['-nostdlib', '-static', '-Map=${TARGET}.map'])
build_properties.ApplyToEnv(env_default)


#----------------------------------------------------------------------------
#
# Add all other tools to the default environment.
#
asciidoc.ApplyToEnv(env_default)
bootblock.ApplyToEnv(env_default)
data_array.ApplyToEnv(env_default)
diff.ApplyToEnv(env_default)
gen_random_seq.ApplyToEnv(env_default)
scons_common.ApplyToEnv(env_default)
svnversion.ApplyToEnv(env_default)
uuencode.ApplyToEnv(env_default)
Export('env_default')


#----------------------------------------------------------------------------
#
# Create the default environments for the different asics.
#
env_netx500_default = env_default.Clone()
env_netx500_default.Append(CCFLAGS = ['-mcpu=arm926ej-s'])
env_netx500_default.Replace(LIBPATH = ['${GCC_LIBRARY_DIR_ARCHITECTURE}/arm926ej-s', '${GCC_LIBRARY_DIR_COMPILER}/arm926ej-s'])
env_netx500_default.Append(CPPDEFINES = [['ASIC_TYP', '500']])
Export('env_netx500_default')

env_netx50_default = env_default.Clone()
env_netx50_default.Append(CCFLAGS = ['-mcpu=arm966e-s'])
env_netx50_default.Replace(LIBPATH = ['${GCC_LIBRARY_DIR_ARCHITECTURE}/arm966e-s', '${GCC_LIBRARY_DIR_COMPILER}/arm966e-s'])
env_netx50_default.Append(CPPDEFINES = [['ASIC_TYP', '50']])
Export('env_netx50_default')

env_netx10_default = env_default.Clone()
env_netx10_default.Append(CCFLAGS = ['-mcpu=arm966e-s'])
env_netx10_default.Replace(LIBPATH = ['${GCC_LIBRARY_DIR_ARCHITECTURE}/arm966e-s', '${GCC_LIBRARY_DIR_COMPILER}/arm966e-s'])
env_netx10_default.Append(CPPDEFINES = [['ASIC_TYP', '10']])
Export('env_netx10_default')

