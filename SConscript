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


# Build a version number of the form 0xAABBBCCC.
import SCons
aVer = SCons.__version__.split('.')
ulVersion = long(aVer[0])*0x01000000 + long(aVer[1])*0x00001000 + long(aVer[2])

# Add the local site_scons folder to the search path.
from SCons.Script.Main import _load_site_scons_dir
if ulVersion>=0x02001000:
	_load_site_scons_dir(Dir('#targets').get_abspath(), 'site_scons')
	_load_site_scons_dir(Dir('.').get_abspath(), 'site_scons')
else:
	_load_site_scons_dir(Dir('#targets'), 'site_scons')
	_load_site_scons_dir(Dir('#'), 'site_scons')

# Import all local modules.
import build_properties
import scons_common


build_properties.Read()

#----------------------------------------------------------------------------
#
# set help text
#
Help("""
This SConstruct file is part of a Muhkuh buildsystem project. Run

  'python path/to/mbs'

from your project's root folder to setup the project environment. Usually
this will be

  'python mbs/mbs'


This will also download all missing tools.
""")

build_properties.GenerateHelp()


#----------------------------------------------------------------------------

# Show summary of the build properties.
build_properties.PrintSummary()



# Collect the tools in this list.
astrTools = []

#----------------------------------------------------------------------------
#
# Get the Compiler for the default environment.
#
strGccVersion = None
try:
	# Allow the user to specify the GCC version with the MBS_GCC_VERSION veriable.
	strGccVersion = MBS_GCC_VERSION
except NameError:
	# The default is to take the first available GCC version from the tools.
	strGccVersion = scons_common.find_first_tool("^gcc")
if not strGccVersion is None:
	astrTools.append(strGccVersion)

#----------------------------------------------------------------------------
#
# Get the Asciidoc version for the default environment.
#
strAsciidocVersion = None
try:
	# Allow the user to specify the Asciidoc version with the MBS_ASCIIDOC_VERSION veriable.
	strAsciidocVersion = MBS_ASCIIDOC_VERSION
except NameError:
	# The default is to take the first available Asciidoc version from the tools.
	strAsciidocVersion = scons_common.find_first_tool("^asciidoc")
if not strAsciidocVersion is None:
	astrTools.append(strAsciidocVersion)


#----------------------------------------------------------------------------
#
# Create the list of environments.
#
class EnvironmentList:
	pass

atEnv = EnvironmentList()
Export('atEnv')


#----------------------------------------------------------------------------
#
# Create the default environment and append it to the list.
#
env_default = scons_common.CreateEnvironment(env=None, astrToolPatterns=astrTools)
env_default.Replace(MBS_ENVIRONMENT_LIST = atEnv)
setattr(atEnv, 'DEFAULT', env_default)
