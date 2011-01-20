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

import scons_common

import build_properties

build_properties.Read()

#----------------------------------------------------------------------------
#
# set help text
#
Help("""
	This SConstruct file is part of a Muhkuh buildsystem project. Run
	
	  'python setup.py'
	
	to setup the project environment and download missing tools.
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


#----------------------------------------------------------------------------
# Only execute this part if the help text is not requested.
# This keeps the help message functional even if no include path for the
# compiler definitions was specified.
if not GetOption('help'):
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
	# Set some fancy options.
	env_default['Asciidoc_backend'] = 'xhtml11'
	env_default['Asciidoc_attributes'] = dict({'numbered':True, 'toc':True, 'toclevels':4})
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
	
	
	#----------------------------------------------------------------------------
	#
	# Create the legacy environments for the different asics.
	#
	env_netx500_old_default = env_default.Clone()
	env_netx500_old_default.Append(CCFLAGS = ['-mcpu=arm926ej-s'])
	env_netx500_old_default.Replace(LIBPATH = ['${GCC_DIR}/arm-elf/lib/arm926ej-s', '${GCC_DIR}/lib/gcc/arm-elf/${GCC_VERSION}/arm926ej-s'])
	Export('env_netx500_old_default')
	
	env_netx50_old_default = env_default.Clone()
	env_netx50_old_default.Append(CCFLAGS = ['-mcpu=arm966e-s'])
	env_netx50_old_default.Replace(LIBPATH = ['${GCC_DIR}/arm-elf/lib/arm966e-s', '${GCC_DIR}/lib/gcc/arm-elf/${GCC_VERSION}/arm966e-s'])
	Export('env_netx50_old_default')
	
