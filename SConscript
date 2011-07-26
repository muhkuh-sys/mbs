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
import flex_zip
import gcc_symbol_template
import gen_random_seq
import hash
import hexdump
import objimport
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

  'python path/to/setup.py'

from your project's root folder to setup the project environment. Usually
this will be

  'python mbs/setup.py'


This will also download all missing tools.
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
# Create the default environment.
#
env_default = Environment()
env_default.Decider('MD5')


#----------------------------------------------------------------------------
#
# Add the Compiler to the environment.
#
strGccVersion = None
try:
	# Allow the user to specify the GCC version with the MBS_GCC_VERSION veriable.
	strGccVersion = MBS_GCC_VERSION
except NameError:
	# The default is to take the first available GCC version from the tools.
	for strName in TOOLS:
		if strName.startswith('gcc')==True:
			strGccVersion = strName
			break
if strGccVersion!=None:
	gcc_arm = scons_common.get_tool(strGccVersion)
	gcc_arm.ApplyToEnv(env_default)
	env_default.Replace(CCFLAGS = Split(default_ccflags))
	env_default.Replace(LIBS = ['m', 'c', 'gcc'])
	env_default.Replace(LINKFLAGS = ['-nostdlib', '-static', '-Map=${TARGET}.map'])


#----------------------------------------------------------------------------
#
# Add Asciidoc to the environment.
#
strAsciidocVersion = None
try:
	# Allow the user to specify the Asciidoc version with the MBS_ASCIIDOC_VERSION veriable.
	strAsciidocVersion = MBS_ASCIIDOC_VERSION
except NameError:
	# The default is to take the first available Asciidoc version from the tools.
	for strName in TOOLS:
		if strName.startswith('asciidoc')==True:
			strAsciidocVersion = strName
			break
if strAsciidocVersion!=None:
	asciidoc = scons_common.get_tool(strAsciidocVersion)
	asciidoc.ApplyToEnv(env_default)


#----------------------------------------------------------------------------
#
# Add all other tools to the default environment.
#
bootblock.ApplyToEnv(env_default)
build_properties.ApplyToEnv(env_default)
data_array.ApplyToEnv(env_default)
diff.ApplyToEnv(env_default)
flex_zip.ApplyToEnv(env_default)
gcc_symbol_template.ApplyToEnv(env_default)
gen_random_seq.ApplyToEnv(env_default)
hash.ApplyToEnv(env_default)
hexdump.ApplyToEnv(env_default)
objimport.ApplyToEnv(env_default)
scons_common.ApplyToEnv(env_default)
svnversion.ApplyToEnv(env_default)
uuencode.ApplyToEnv(env_default)
Export('env_default')

