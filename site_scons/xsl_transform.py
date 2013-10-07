# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2013 by Christoph Thelen                                #
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

import xslt

import re
import os.path

import SCons
import SCons.Node.FS
from SCons.Script import *



xslt_include_re = re.compile(r'<xsl:include\s+href="(\S+)"\s*/>', re.M)

def xslt_scan(node, env, path):
	contents = node.get_text_contents()
	astrIncludes = xslt_include_re.findall(contents)
	
	astrInc = []
	for strInc in astrIncludes:
		if os.path.isabs(strInc):
			strIncPath = strInc
		else:
			strIncPath = os.path.abspath(os.path.join(os.path.dirname(node.get_path()), strInc))
		astrInc.append(strIncPath)
	return env.File(astrInc)



def xslt_action(target, source, env):
	tProc = xslt.XSLTProcessor()
	tProc.setStylesheet(source[1].get_path())
	astrMsgs = []
	strResult = tProc.transform(source[0].get_path(), messages=astrMsgs)
	
	# Show all messages.
	for strMsg in astrMsgs:
		print '[MSG]: %s' % strMsg
	
	# Write the transformed data to the target file.
	file_target = open(target[0].get_path(), 'wt')
	file_target.write(strResult)
	file_target.close()
	
	return 0


def xslt_emitter(target, source, env):
	# The list of sources must contain exactly 2 elements.
	# The first one is the XML file.
	# The second one is the XSLT file.
	if len(source)!=2:
		raise Exception('The XSLT builder needs exactly 2 sources: the XML file and the XSLT file.')
	
	return target, source


def xslt_string(target, source, env):
	return 'XSLT %s' % target[0].get_path()


def ApplyToEnv(env):
	#----------------------------------------------------------------------------
	#
	# Add xslt builder.
	#
	
	xslt_act = SCons.Action.Action(xslt_action, xslt_string)
	xslt_bld = Builder(action=xslt_act, emitter=xslt_emitter)
	env['BUILDERS']['XSLT'] = xslt_bld
	
	# Add the XSLT scanner.
	xslt_scanner = Scanner(function = xslt_scan, skeys = ['.xsl', '.xslt'])
	env.Append(SCANNERS = xslt_scanner)



