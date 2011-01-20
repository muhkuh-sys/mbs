# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2010 by Christoph Thelen                                #
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


import imp
import os
import sys

from SCons.Script import *


#----------------------------------------------------------------------------
#
# Accept 'clean' target like make as an alternative to '-c'. This makes it
# much easier to work with an IDE like KDevelop.
#
if 'clean' in COMMAND_LINE_TARGETS:
	Alias('clean', '.')
	SetOption('clean', 1)


#----------------------------------------------------------------------------
#
# Replace the default exception hander.
#
BUILD_CRASHED = False

print sys.excepthook
def mbs_excepthook(_type, _value, _traceback):
	print '*** Crash ***'
	global BUILD_CRASHED
	BUILD_CRASHED = True
	#sys.__excepthook__(_type, _value, _traceback)

sys.excepthook = mbs_excepthook
print sys.excepthook

#----------------------------------------------------------------------------
#
# Display the complete command line if any command failed.
#
# TODO: GetBuildFailures only reports scons errors. If an exception occured,
#       this list is empty and the function reports a successful build right
#       after the stack dump. How can I detect this here?
#
def display_build_status():
	if BUILD_CRASHED==True:
		print "!!!!!!!!!!!!!!!!"
		print "!!! CRASHED !!!!"
		print "!!!!!!!!!!!!!!!!"
	else:
		from SCons.Script import GetBuildFailures
		bf_all = GetBuildFailures()
		if bf_all:
			# iterate over all failures and print the command
			for bf in bf_all:
				if bf and bf.node and bf.command:
					print 'Failed command for ' + str(bf.node) + ":\n" + ' '.join(bf.command)
			print "!!!!!!!!!!!!!!!"
			print "!!! FAILED !!!!"
			print "!!!!!!!!!!!!!!!"
		else:
			print "Build succeeded."

import atexit
atexit.register(display_build_status)


def get_tool(strToolName):
	global TOOLS
	
	tMod = None
	try:
		strPath = TOOLS[strToolName]
		strModulName = strToolName.replace('-','_').replace('.','_')
		fp,pathname,description = imp.find_module(strModulName, [strPath])
		try:
			tMod = imp.load_module(strModulName, fp, pathname, description)
		finally:
			# Since we may exit via an exception, close fp explicitly.
			if fp:
				fp.close()
	except KeyError:
		pass
	
	if tMod==None:
		raise Exception(strToolName, 'The requested tool is not part of the configuration. Add it to setup.xml and rerun setup.py')
	
	return tMod


def set_build_path(env, build_path, source_path, sources):
	env.VariantDir(build_path, source_path, duplicate=0)
	return [src.replace(source_path, build_path) for src in sources]

