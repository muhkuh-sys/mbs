# -*- coding: utf-8 -*-

# ***************************************************************************
# *   Copyright (C) 2019 by Hilscher GmbH                                   *
# *   netXsupport@hilscher.com                                              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU General Public License for more details.                          *
# *                                                                         *
# *   You should have received a copy of the GNU General Public License     *
# *   along with this program; if not, write to the                         *
# *   Free Software Foundation, Inc.,                                       *
# *   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.             *
# ***************************************************************************

import ast
import xml.dom.minidom

# ----------------------------------------------------------------------------
#
# This class replaces literal values in AST expressions with a dictionary.
#


class RewriteName(ast.NodeTransformer):
    __atConstants = None
    __atTemporaryConstants = None

    def setConstants(self, atConstants):
        self.__atConstants = atConstants

    def setTemporaryConstants(self, atConstants):
        self.__atTemporaryConstants = atConstants

    def visit_Name(self, node):
        tNode = None
        if node.id in self.__atConstants:
            tValue = self.__atConstants[node.id]
            tNode = ast.copy_location(ast.Num(n=tValue), node)
        elif(
            self.__atTemporaryConstants is not None and
            node.id in self.__atTemporaryConstants
        ):
            tValue = self.__atTemporaryConstants[node.id]
            tNode = ast.copy_location(ast.Num(n=tValue), node)
        else:
            raise Exception('Unknown constant %s.' % node.id)
        return tNode

# ----------------------------------------------------------------------------


class PatchDefinitions:
    # This is a dictionary with all the data from the patch definition.
    m_atPatchDefinitions = None

    # This is a dictionary of all constants. They are read from the patch
    # definition.
    m_atConstants = None

    m_cAstConstResolver = None

    def __init__(self):
        self.m_atPatchDefinitions = dict({})
        self.m_atConstants = dict({})
        self.m_cAstConstResolver = RewriteName()
        self.m_cAstConstResolver.setConstants(self.m_atConstants)

    def read_patch_definition(self, tInput):
        # A string must be the filename of the XML.
        if isinstance(tInput, ("".__class__, u"".__class__)):
            tXml = xml.dom.minidom.parse(tInput)
        elif isinstance(tInput, xml.dom.minidom.Document):
            tXml = tInput
        else:
            raise Exception('Unknown input document: %s' % repr(tInput))

        # Loop over all children.
        for tOptionsNode in tXml.documentElement.childNodes:
            # Is this a node element with the name 'Options'?
            if(
                tOptionsNode.nodeType == tOptionsNode.ELEMENT_NODE and
                tOptionsNode.localName == 'Options'
            ):
                # Loop over all children.
                for tOptionNode in tOptionsNode.childNodes:
                    # Is this a node element with the name 'Options'?
                    if(
                        tOptionNode.nodeType == tOptionNode.ELEMENT_NODE and
                        tOptionNode.localName == 'Option'
                    ):
                        # Get the ID.
                        strOptionId = tOptionNode.getAttribute('id')
                        if strOptionId == '':
                            raise Exception('Missing id attribute!')
                        if strOptionId in self.m_atPatchDefinitions:
                            raise Exception('ID %s double defined!' %
                                            strOptionId)

                        strOptionValue = tOptionNode.getAttribute('value')
                        if strOptionValue == '':
                            raise Exception('Missing value attribute!')
                        ulOptionValue = int(strOptionValue, 0)

                        # Loop over all children.
                        atElements = []
                        for tElmNode in tOptionNode.childNodes:
                            # Is this a node element with the name 'Element'?
                            if(
                                tElmNode.nodeType == tElmNode.ELEMENT_NODE and
                                tElmNode.localName == 'Element'
                            ):
                                # Get the ID.
                                strElementId = tElmNode.getAttribute('id')
                                if strElementId == '':
                                    raise Exception('Missing id attribute!')

                                # Get the size attribute.
                                strSize = tElmNode.getAttribute('size')
                                if strSize == '':
                                    raise Exception('Missing size attribute!')
                                ulSize = int(strSize, 0)

                                # Get the type attribute.
                                strType = tElmNode.getAttribute('type')
                                if strType == '':
                                    raise Exception('Missing type attribute!')
                                ulType = int(strType, 0)

                                atElements.append(
                                    (strElementId, ulSize, ulType)
                                )
                        atDesc = dict({})
                        atDesc['value'] = ulOptionValue
                        atDesc['elements'] = atElements
                        self.m_atPatchDefinitions[strOptionId] = atDesc

            elif(
                tOptionsNode.nodeType == tOptionsNode.ELEMENT_NODE and
                tOptionsNode.localName == 'Definitions'
            ):
                # Loop over all children.
                for tDefNode in tOptionsNode.childNodes:
                    if(
                        tDefNode.nodeType == tDefNode.ELEMENT_NODE and
                        tDefNode.localName == 'Definition'
                    ):
                        # Get the name.
                        strDefinitionName = tDefNode.getAttribute('name')
                        if strDefinitionName == '':
                            raise Exception('Missing name attribute!')
                        if strDefinitionName in self.m_atConstants:
                            raise Exception('Name "%s" double defined!' %
                                            strDefinitionName)

                        strDefinitionValue = tDefNode.getAttribute(
                            'value'
                        )
                        if strDefinitionValue == '':
                            raise Exception('Missing value attribute!')
                        ulDefValue = int(strDefinitionValue, 0)

                        self.m_atConstants[strDefinitionName] = ulDefValue

    def resolve_constants(self, tAstNode):
        return self.m_cAstConstResolver.visit(tAstNode)

    def get_patch_definition(self, strOptionId):
        if strOptionId not in self.m_atPatchDefinitions:
            raise Exception('The option ID %s was not found!' % strOptionId)

        return self.m_atPatchDefinitions[strOptionId]

    def setTemporaryConstants(self, atConstants):
        self.m_cAstConstResolver.setTemporaryConstants(atConstants)
