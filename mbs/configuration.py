# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------#
#   Copyright (C) 2012 by Christoph Thelen                                #
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

import os.path
import platform
import string
import xml.etree.ElementTree


def read_tool(tNode):
	strGroup = tNode.findtext('group')
	strName = tNode.findtext('name')
	strPackage = tNode.findtext('package')
	strVersion = tNode.findtext('version')
	strTyp = tNode.findtext('typ')
	
	tTemplate = string.Template(strPackage)
	
	return dict({
		'group': strGroup,
		'name': strName,
		'package': tTemplate.safe_substitute(dict({ 'platform': platform.system().lower() })),
		'version': strVersion,
		'typ': strTyp
	})


def read_config_paths(aCfg, tXml):
	strPath = tXml.findtext('paths/marker')
	if strPath!=None:
		aCfg['marker_path'] = os.path.abspath(os.path.expanduser(strPath))
	
	strPath = tXml.findtext('paths/repository')
	if strPath!=None:
		aCfg['repository_path'] = os.path.abspath(os.path.expanduser(strPath))
	
	strPath = tXml.findtext('paths/depack')
	if strPath!=None:
		aCfg['depack_path'] = os.path.abspath(os.path.expanduser(strPath))


def read_user_config(strConfigPath, aCfg):
	strRealPath = os.path.abspath(os.path.expanduser(strConfigPath))
	if os.path.isfile(strRealPath)==True:
		tXml = xml.etree.ElementTree.ElementTree()
		tXml.parse(strRealPath)
		
		read_config_paths(aCfg, tXml)
		
		iInsertPos = 0
		for tNode in tXml.findall('repositories/repository'):
			# Insert the user repositories before the default entries.
			aCfg['repositories'].insert(iInsertPos, tNode.text)
			iInsertPos += 1


def read_project_config(strConfigPath, aCfg):
	if os.path.isfile(strConfigPath)==True:
		tXml = xml.etree.ElementTree.ElementTree()
		tXml.parse(strConfigPath)
		
		aCfg['project_version_major'] = long(tXml.findtext('project_version/major'))
		aCfg['project_version_minor'] = long(tXml.findtext('project_version/minor'))
		aCfg['project_version_micro'] = long(tXml.findtext('project_version/micro'))
		
		strPath = tXml.findtext('paths/marker')
		if strPath!=None:
			aCfg['marker_path'] = os.path.abspath(os.path.expanduser(strPath))
		
		strPath = tXml.findtext('paths/repository')
		if strPath!=None:
			aCfg['repository_path'] = os.path.abspath(os.path.expanduser(strPath))
		
		strPath = tXml.findtext('paths/depack')
		if strPath!=None:
			aCfg['depack_path'] = os.path.abspath(os.path.expanduser(strPath))
		
		tElement = tXml.find('repositories')
		if tElement!=None:
			# Replace all other elements?
			strReplace = tElement.get('replace')
			if strReplace in ['true', 'True', 'yes', 'Yes']:
				aCfg['repositories'] = dict({})
			# Insert the projects repositories before all other entries.
			iInsertPos = 0
			for tNode in tXml.findall('repositories/repository'):
				aCfg['repositories'].insert(iInsertPos, tNode.text)
				iInsertPos += 1
		
		aCfg['scons'] = read_tool(tXml.find('scons'))
		
		aTools = []
		for tNode in tXml.findall('tools/tool'):
			aTools.append(read_tool(tNode))
		aCfg['tools'] = aTools
	
		tElement = tXml.find('filters')
		if tElement!=None:
			strReplace = tElement.get('replace')
			if strReplace in ['true', 'True', 'yes', 'Yes']:
				aCfg['filter'] = dict({})
			
			for tNode in tXml.findall('filters/filter'):
				strTemplate = tNode.findtext('template')
				strDst = tNode.findtext('destination')
				if strTemplate!=None and strDst!=None:
					aCfg['filter'][strDst] = strTemplate
	return aCfg



def create():
	# Set the defaults.
	aCfg = dict({
		'marker_path': os.path.abspath(os.path.expanduser('~/.mbs/depack')),
		'repository_path': os.path.abspath(os.path.expanduser('~/.mbs/repository')),
		'depack_path': os.path.abspath(os.path.expanduser('~/.mbs/depack')),
		'repositories': ['http://downloads.sourceforge.net/project/muhkuh/mbs', 'https://dl.bintray.com/muhkuh/Muhkuh'],
		'filter': dict({
			'scons.bat': 'templates/scons.bat',
			'scons.sh': 'templates/scons.sh',
			'site_scons/site_init.py': 'templates/site_init.py'
			})
		})

	return aCfg

