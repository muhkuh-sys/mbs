# -*- coding: utf-8 -*-

import argparse
import array
import ast
import base64
import binascii
import elf_support
import hashlib
import math
import os
import os.path
import re
import string
import subprocess
import tempfile
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
        elif (self.__atTemporaryConstants is not None) and (node.id in self.__atTemporaryConstants):
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
        if isinstance(tInput, basestring):
            tXml = xml.dom.minidom.parse(tInput)
        elif isinstance(tInput, xml.dom.minidom.Document):
            tXml = tInput
        else:
            raise Exception('Unknown input document: %s' % repr(tInput))

        # Loop over all children.
        for tOptionsNode in tXml.documentElement.childNodes:
            # Is this a node element with the name 'Options'?
            if (tOptionsNode.nodeType == tOptionsNode.ELEMENT_NODE) and (tOptionsNode.localName == 'Options'):
                # Loop over all children.
                for tOptionNode in tOptionsNode.childNodes:
                    # Is this a node element with the name 'Options'?
                    if (tOptionNode.nodeType == tOptionNode.ELEMENT_NODE) and (tOptionNode.localName == 'Option'):
                        # Get the ID.
                        strOptionId = tOptionNode.getAttribute('id')
                        if strOptionId == '':
                            raise Exception('Missing id attribute!')
                        if strOptionId in self.m_atPatchDefinitions:
                            raise Exception('ID %s double defined!' % strOptionId)

                        strOptionValue = tOptionNode.getAttribute('value')
                        if strOptionValue == '':
                            raise Exception('Missing value attribute!')
                        ulOptionValue = int(strOptionValue, 0)

                        # Loop over all children.
                        atElements = []
                        for tElementNode in tOptionNode.childNodes:
                            # Is this a node element with the name 'Element'?
                            if (tElementNode.nodeType == tElementNode.ELEMENT_NODE) and (tElementNode.localName == 'Element'):
                                # Get the ID.
                                strElementId = tElementNode.getAttribute('id')
                                if strElementId == '':
                                    raise Exception('Missing id attribute!')

                                # Get the size attribute.
                                strSize = tElementNode.getAttribute('size')
                                if strSize == '':
                                    raise Exception('Missing size attribute!')
                                ulSize = int(strSize, 0)

                                # Get the type attribute.
                                strType = tElementNode.getAttribute('type')
                                if strType == '':
                                    raise Exception('Missing type attribute!')
                                ulType = int(strType, 0)

                                atElements.append((strElementId, ulSize, ulType))
                        atDesc = dict({})
                        atDesc['value'] = ulOptionValue
                        atDesc['elements'] = atElements
                        self.m_atPatchDefinitions[strOptionId] = atDesc

            elif (tOptionsNode.nodeType == tOptionsNode.ELEMENT_NODE) and (tOptionsNode.localName == 'Definitions'):
                # Loop over all children.
                for tDefinitionNode in tOptionsNode.childNodes:
                    if (tDefinitionNode.nodeType == tDefinitionNode.ELEMENT_NODE) and (tDefinitionNode.localName == 'Definition'):
                        # Get the name.
                        strDefinitionName = tDefinitionNode.getAttribute('name')
                        if strDefinitionName == '':
                            raise Exception('Missing name attribute!')
                        if strDefinitionName in self.m_atConstants:
                            raise Exception('Name "%s" double defined!' % strDefinitionName)

                        strDefinitionValue = tDefinitionNode.getAttribute('value')
                        if strDefinitionValue == '':
                            raise Exception('Missing value attribute!')
                        ulDefinitionValue = int(strDefinitionValue, 0)

                        self.m_atConstants[strDefinitionName] = ulDefinitionValue

    def resolve_constants(self, tAstNode):
        return self.m_cAstConstResolver.visit(tAstNode)

    def get_patch_definition(self, strOptionId):
        if strOptionId not in self.m_atPatchDefinitions:
            raise Exception('The option ID %s was not found!' % strOptionId)

        return self.m_atPatchDefinitions[strOptionId]

    def setTemporaryConstants(self, atConstants):
        self.m_cAstConstResolver.setTemporaryConstants(atConstants)

# ----------------------------------------------------------------------------
#
# The option compiler builds an option chunk.
#


class OptionCompiler:
    # This is a list of the compiled options.
    __strOptions = None

    # This is the patch definitions object.
    __cPatchDefinitions = None

    def __init__(self, tPatchDefinitions):
        self.__strOptions = ''
        self.__cPatchDefinitions = tPatchDefinitions

    def __parse_numeric_expression(self, strExpression):
        tAstNode = ast.parse(strExpression, mode='eval')
        tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
        ulResult = eval(compile(tAstResolved, 'lala', mode='eval'))
        # TODO: is this really necessary? Maybe ast.literal_eval throws
        # something already.
        if ulResult is None:
            raise Exception('Invalid number: "%s"' % strExpression)
        return ulResult

    def __get_data(self, tDataNode, uiElementSizeInBytes):
        # Collect all text nodes and CDATA sections.
        atText = []
        # Loop over all children.
        for tTextNode in tDataNode.childNodes:
            # Is this a node element with the name 'Options'?
            if (tTextNode.nodeType == tDataNode.TEXT_NODE) or (tTextNode.nodeType == tDataNode.CDATA_SECTION_NODE):
                atText.append(tTextNode.data)
        # Join all text chunks.
        strText = ''.join(atText)
        # Split the text by comma.
        atTextElements = string.split(strText, ',')

        # Process all data elements.
        atData = []
        for strElementRaw in atTextElements:
            strElement = string.strip(strElementRaw)

            # Parse the data.
            ulValue = self.__parse_numeric_expression(strElement)

            # Generate the data entry.
            atBytes = [chr((ulValue >> (iCnt << 3)) & 0xff) for iCnt in range(0, uiElementSizeInBytes)]
            atData.append(''.join(atBytes))
        return ''.join(atData)

    # NOTE: This function is also used from outside for SpiMacro parsing.
    def get_spi_macro_data(self, tDataNode):
        # Collect all text nodes and CDATA sections.
        atText = []
        # Loop over all children.
        for tTextNode in tDataNode.childNodes:
            # Is this a node element with the name 'Options'?
            if (tTextNode.nodeType == tTextNode.TEXT_NODE) or (tTextNode.nodeType == tTextNode.CDATA_SECTION_NODE):
                atText.append(tTextNode.data)
        # Join all text chunks.
        strText = ''.join(atText)

        # Split the text by newlines.
        atLines = string.split(strText, '\n')
        # Split the lines by comma.
        atRawElements = []
        for strLine in atLines:
            atRawElements.extend(string.split(strLine, ','))

        # Loop over all lines.
        ulAddress = 0
        atLabels = dict({})
        atElements = []
        for strRawElement in atRawElements:
            # Remove empty lines and comments.
            strElement = string.strip(strRawElement)
            if (len(strElement) > 0) and (strElement[0] != '#'):
                # Does the element contain a colon?
                atTmp = string.split(strElement, ':')
                if len(atTmp) == 1:
                    # The line does not contain a colon.
                    # This counts as one byte.
                    ulAddress += 1
                    atElements.append(atTmp[0])
                elif len(atTmp) != 2:
                    raise Exception('The line contains more than one colon!')
                else:
                    if len(atTmp[0]) == 0:
                        raise Exception('The line contains no data before the colon!')

                    # The line contains a label definition.
                    strLabelName = atTmp[0]
                    if strLabelName in atLabels:
                        raise Exception('Label double defined: %s' % strLabelName)
                    atLabels[strLabelName] = ulAddress

                    if len(atTmp[1]) != 0:
                        # The line contains also data.
                        ulAddress += 1
                        atElements.append(string.strip(atTmp[0]))

        # Set the labels as temporary constants.
        self.__cPatchDefinitions.setTemporaryConstants(atLabels)

        # Process all data elements.
        atData = []
        for strElement in atElements:
            # Parse the data.
            tAstNode = ast.parse(strElement, mode='eval')
            tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
            ast.dump(tAstResolved)
            ulValue = eval(compile(tAstResolved, 'lala', mode='eval'))

            # Generate the data entry.
            atData.append(chr(ulValue))

        # Remove the labels as temporary constants.
        self.__cPatchDefinitions.setTemporaryConstants([])

        return ''.join(atData)

    def __get_ddr_macro_data(self, tDataNode):
        # Collect the DDR macro in this array.
        atDdrMacro = []

        # Loop over all children.
        for tNode in tDataNode.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'WritePhy':
                    strValue = tNode.getAttribute('register')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ucRegister = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception('Invalid register for WritePhy: 0x%02x' % ucRegister)
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' % ulData)

                    # Append the new element.
                    atDdrMacro.append(chr(self.__cPatchDefinitions.m_atConstants['DDR_SETUP_COMMAND_WritePhy']))
                    atDdrMacro.append(chr(ucRegister))
                    atDdrMacro.append(chr(ulData & 0xff))
                    atDdrMacro.append(chr((ulData >> 8) & 0xff))
                    atDdrMacro.append(chr((ulData >> 16) & 0xff))
                    atDdrMacro.append(chr((ulData >> 24) & 0xff))

                elif tNode.localName == 'WriteCtrl':
                    strValue = tNode.getAttribute('register')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ucRegister = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception('Invalid register for WritePhy: 0x%02x' % ucRegister)
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' % ulData)

                    # Append the new element.
                    atDdrMacro.append(chr(self.__cPatchDefinitions.m_atConstants['DDR_SETUP_COMMAND_WriteCtrl']))
                    atDdrMacro.append(chr(ucRegister))
                    atDdrMacro.append(chr(ulData & 0xff))
                    atDdrMacro.append(chr((ulData >> 8) & 0xff))
                    atDdrMacro.append(chr((ulData >> 16) & 0xff))
                    atDdrMacro.append(chr((ulData >> 24) & 0xff))

                elif tNode.localName == 'Delay':
                    strValue = tNode.getAttribute('ticks')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulTicks = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ulTicks < 0) or (ulTicks > 0xffffffff):
                        raise Exception('Invalid value for Delay: 0x%08x' % ulTicks)

                    # Append the new element.
                    atDdrMacro.append(chr(self.__cPatchDefinitions.m_atConstants['DDR_SETUP_COMMAND_DelayTicks']))
                    atDdrMacro.append(chr(ulTicks & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 8) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 16) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 24) & 0xff))

                elif tNode.localName == 'PollPhy':
                    strValue = tNode.getAttribute('register')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ucRegister = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('mask')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulMask = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('ticks')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulTicks = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception('Invalid register for WritePhy: 0x%02x' % ucRegister)
                    if (ulMask < 0) or (ulMask > 0xffffffff):
                        raise Exception('Invalid mask for WritePhy: 0x%08x' % ulMask)
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' % ulData)
                    if (ulTicks < 0) or (ulTicks > 0xffffffff):
                        raise Exception('Invalid value for Delay: 0x%08x' % ulTicks)

                    # Append the new element.
                    atDdrMacro.append(chr(self.__cPatchDefinitions.m_atConstants['DDR_SETUP_COMMAND_PollPhy']))
                    atDdrMacro.append(chr(ucRegister))
                    atDdrMacro.append(chr(ulMask & 0xff))
                    atDdrMacro.append(chr((ulMask >> 8) & 0xff))
                    atDdrMacro.append(chr((ulMask >> 16) & 0xff))
                    atDdrMacro.append(chr((ulMask >> 24) & 0xff))
                    atDdrMacro.append(chr(ulData & 0xff))
                    atDdrMacro.append(chr((ulData >> 8) & 0xff))
                    atDdrMacro.append(chr((ulData >> 16) & 0xff))
                    atDdrMacro.append(chr((ulData >> 24) & 0xff))
                    atDdrMacro.append(chr(ulTicks & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 8) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 16) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 24) & 0xff))

                elif tNode.localName == 'PollCtrl':
                    strValue = tNode.getAttribute('register')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ucRegister = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('mask')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulMask = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('ticks')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
                    ulTicks = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception('Invalid register for WritePhy: 0x%02x' % ucRegister)
                    if (ulMask < 0) or (ulMask > 0xffffffff):
                        raise Exception('Invalid mask for WritePhy: 0x%08x' % ulMask)
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' % ulData)
                    if (ulTicks < 0) or (ulTicks > 0xffffffff):
                        raise Exception('Invalid value for Delay: 0x%08x' % ulTicks)

                    # Append the new element.
                    atDdrMacro.append(chr(self.__cPatchDefinitions.m_atConstants['DDR_SETUP_COMMAND_PollCtrl']))
                    atDdrMacro.append(chr(ucRegister))
                    atDdrMacro.append(chr(ulMask & 0xff))
                    atDdrMacro.append(chr((ulMask >> 8) & 0xff))
                    atDdrMacro.append(chr((ulMask >> 16) & 0xff))
                    atDdrMacro.append(chr((ulMask >> 24) & 0xff))
                    atDdrMacro.append(chr(ulData & 0xff))
                    atDdrMacro.append(chr((ulData >> 8) & 0xff))
                    atDdrMacro.append(chr((ulData >> 16) & 0xff))
                    atDdrMacro.append(chr((ulData >> 24) & 0xff))
                    atDdrMacro.append(chr(ulTicks & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 8) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 16) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 24) & 0xff))

                else:
                    raise Exception('Unknown child node: %s' % tNode.localName)

        # Combine all macro data.
        strDdrMacro = ''.join(atDdrMacro)
        sizDdrMacro = len(strDdrMacro)

        # Prepend the size information.
        atData = []
        atData.append(chr(sizDdrMacro & 0xff))
        atData.append(chr((sizDdrMacro >> 8) & 0xff))
        atData.extend(atDdrMacro)

        # Return the data.
        return atData

    def __getOptionData(self, tOptionNode):
        atData = []

        # Loop over all children.
        for tDataNode in tOptionNode.childNodes:
            # Is this a node element with the name 'Options'?
            if tDataNode.nodeType == tDataNode.ELEMENT_NODE:
                if tDataNode.localName == 'U08':
                    strData = self.__get_data(tDataNode, 1)
                    atData.append(strData)
                elif tDataNode.localName == 'U16':
                    strData = self.__get_data(tDataNode, 2)
                    atData.append(strData)
                elif tDataNode.localName == 'U32':
                    strData = self.__get_data(tDataNode, 4)
                    atData.append(strData)
                elif tDataNode.localName == 'SPIM':
                    strData = self.get_spi_macro_data(tDataNode)
                    atData.append(strData)
                elif tDataNode.localName == 'DDR':
                    strData = self.__get_ddr_macro_data(tDataNode)
                    atData.append(strData)
                else:
                    raise Exception('Unexpected node: %s', tDataNode.localName)

        return atData

    def __processChunkOptions(self, tChunkNode):
        atOptionData = []

        # Loop over all children.
        for tOptionNode in tChunkNode.childNodes:
            # Is this a node element with the name 'Options'?
            if tOptionNode.nodeType == tOptionNode.ELEMENT_NODE:
                if tOptionNode.localName == 'Option':
                    # Get the ID.
                    strOptionId = tOptionNode.getAttribute('id')
                    if strOptionId == '':
                        raise Exception('Missing id attribute!')

                    if strOptionId == 'RAW':
                        # Get the offset attribute.
                        strOffset = tOptionNode.getAttribute('offset')
                        if strOffset == '':
                            raise Exception('Missing offset attribute!')
                        ulOffset = self.__parse_numeric_expression(strOffset)

                        # Get all data elements.
                        atData = self.__getOptionData(tOptionNode)

                        # To make things easier this routine expects only one element.
                        if len(atData) != 1:
                            raise Exception('A RAW element must have only one child element. This is just a limitation of the parser, so improve it if you really need it.')

                        # The data size must fit into 1 byte.
                        sizElement = len(atData[0])
                        if sizElement > 255:
                            raise Exception('The RAW tag does not accept more than 255 bytes.')

                        ucOptionValue = 0xfe
                        atOptionData.append(chr(ucOptionValue))
                        atOptionData.append(chr(sizElement))
                        atOptionData.append(chr(ulOffset & 0xff))
                        atOptionData.append(chr((ulOffset >> 8) & 0xff))
                        atOptionData.extend(atData[0])

                    else:
                        atOptionDesc = self.__cPatchDefinitions.get_patch_definition(strOptionId)
                        ulOptionValue = atOptionDesc['value']
                        atElements = atOptionDesc['elements']

                        # Get all data elements.
                        atData = self.__getOptionData(tOptionNode)

                        # Compare the data elements with the element sizes.
                        sizElements = len(atElements)
                        if len(atData) != sizElements:
                            raise Exception('The number of data elements for the option %s differs. The model requires %d, but %d were found.' % (strOptionId, sizElements, len(atData)))

                        atOptionData.append(chr(ulOptionValue))

                        # Compare the size of all elements.
                        for iCnt in range(0, sizElements):
                            sizElement = len(atData[iCnt])
                            (strElementId, ulSize, ulType) = atElements[iCnt]
                            if ulType == 0:
                                if sizElement != ulSize:
                                    raise Exception('The length of the data element %s for the option %s differs. The model requires %d bytes, but %d were found.' % (strElementId, strOptionId, ulSize, sizElement))
                            elif ulType == 1:
                                if sizElement >= ulSize:
                                    raise Exception('The length of the data element %s for the option %s exceeds the available space. The model reserves %d bytes, which must include a length information, but %d were found.' % (strElementId, strOptionId, ulSize, sizElement))
                            elif ulType == 2:
                                if sizElement >= ulSize:
                                    raise Exception('The length of the data element %s for the option %s exceeds the available space. The model reserves %d bytes, but %d were found.' % (strElementId, strOptionId, ulSize, sizElement))
                            else:
                                raise Exception('Unknown Type %d' % ulType)

                        # Write all elements.
                        for iCnt in range(0, sizElements):
                            sizElement = len(atData[iCnt])
                            (strElementId, ulSize, ulType) = atElements[iCnt]
                            if ulType == 0:
                                atOptionData.extend(atData[iCnt])
                            elif ulType == 1:
                                # Add a size byte.
                                atOptionData.append(chr(sizElement))
                                atOptionData.extend(atData[iCnt])
                            elif ulType == 2:
                                # Add 16 bit size information.
                                atOptionData.append(chr(sizElement & 0xff))
                                atOptionData.append(chr((sizElement >> 8) & 0xff))
                                atOptionData.extend(atData[iCnt])
                            else:
                                raise Exception('Unknown Type %d' % ulType)
                else:
                    raise Exception('Unexpected node: %s', tOptionNode.localName)

        return ''.join(atOptionData)

    def process(self, tSource):
        # Clear the output data.
        self.__strOptions = ''

        if not isinstance(tSource, xml.dom.minidom.Node):
            raise Exception('The input must be of the type xml.dom.minidom.Node, but it is not!')

        self.__strOptions = self.__processChunkOptions(tSource)

    def tostring(self):
        """ Return the compiled options as a string. """
        return self.__strOptions

    def write(self, strTargetPath):
        """ Write all compiled options to the file strTargetPath . """
        tFile = open(strTargetPath, 'wb')

        tFile.write(self.tostring())
        tFile.close()

# ---------------------------------------------------------------------------


class HbootImage:
    # This is the list of override items for the header.
    __atHeaderOverride = None

    # This is a list with all chunks.
    __atChunks = None

    # This is the environment.
    __tEnv = None

    # This is a list of all include paths.
    __astrIncludePaths = None

    # This is a dictionary of all resolved files.
    __astrKnownFiles = None

    __cPatchDefinitions = None

    __uiNetxType = None
    __tImageType = None
    __astrToImageType = None
    __IMAGE_TYPE_REGULAR = 0
    __IMAGE_TYPE_INTRAM = 1
    __IMAGE_TYPE_SECMEM = 2
    __sizHashDw = None

    __XmlKeyromContents = None
    __cfg_openssl = 'openssl'

    # This is the revision for the netX10, netX51 and netX52 Secmem zone.
    __SECMEM_ZONE2_REV1_0 = 0x81

    # The magic cookies for the different chips.
    __MAGIC_COOKIE_NETX56 = 0xf8beaf00
    __MAGIC_COOKIE_NETX4000 = 0xf3beaf00

    def __init__(self, tEnv, uiNetxType, strKeyromFile):
        # Do not override anything in the pre-calculated header yet.
        self.__atHeaderOverride = [None] * 16

        # No chunks yet.
        self.__atChunks = None

        # Set the environment.
        self.__tEnv = tEnv

        # No files yet.
        self.__atKnownFiles = dict({})

        self.__cPatchDefinitions = None

        self.__uiNetxType = uiNetxType
        self.__tImageType = None
        self.__sizHashDw = None

        self.__astrToImageType = dict({
            'REGULAR': self.__IMAGE_TYPE_REGULAR,
            'INTRAM': self.__IMAGE_TYPE_INTRAM,
            'SECMEM': self.__IMAGE_TYPE_SECMEM
        })

        # Initialize the include paths from the environment.
        self.__astrIncludePaths = []
        if 'HBOOT_INCLUDE' in tEnv:
            tIncl = tEnv['HBOOT_INCLUDE']
            if isinstance(tIncl, basestring):
                self.__astrIncludePaths.append(tIncl)
            else:
                self.__astrIncludePaths.extend(tIncl)

        # Read the keyrom file if specified.
        if strKeyromFile is not None:
            # Parse the XML file.
            tFile = open(strKeyromFile, 'rt')
            strXml = tFile.read()
            tFile.close()
            self.__XmlKeyromContents = xml.etree.ElementTree.fromstring(strXml)

    def __get_tag_id(self, cId0, cId1, cId2, cId3):
        # Combine the 4 ID characters to a 32 bit value.
        ulId = ord(cId0) | (ord(cId1) << 8) | (ord(cId2) << 16) | (ord(cId3) << 24)
        return ulId

    def __xml_get_all_text(self, tNode):
        astrText = []
        for tChild in tNode.childNodes:
            if (tChild.nodeType == tChild.TEXT_NODE) or (tChild.nodeType == tChild.CDATA_SECTION_NODE):
                astrText.append(str(tChild.data))
        return ''.join(astrText)

    def __build_standard_header(self, atChunks):

        ulMagicCookie = None
        if self.__uiNetxType == 56:
            ulMagicCookie = self.__MAGIC_COOKIE_NETX56
        elif self.__uiNetxType == 4000:
            ulMagicCookie = self.__MAGIC_COOKIE_NETX4000
        else:
            raise Exception('Missing platform configuration: no standard header configured, please update the HBOOT image compiler.')

        # Get the hash for the image.
        tHash = hashlib.sha224()
        tHash.update(atChunks.tostring())
        aulHash = array.array('I', tHash.digest())

        # Get the parameter0 value.
        # For now only the lower 4 bits are defined. They set the number of
        # hash DWORDs minus 1.
        ulParameter0 = self.__sizHashDw - 1

        # Build the boot block.
        aBootBlock = array.array('I', [0] * 16)
        aBootBlock[0x00] = ulMagicCookie    # Magic cookie.
        aBootBlock[0x01] = 0                # reserved
        aBootBlock[0x02] = 0                # reserved
        aBootBlock[0x03] = 0                # reserved
        aBootBlock[0x04] = len(atChunks)        # chunks dword size
        aBootBlock[0x05] = 0                # reserved
        aBootBlock[0x06] = self.__get_tag_id('M', 'O', 'O', 'H')   # 'MOOH' signature
        aBootBlock[0x07] = ulParameter0         # Image parameters.
        aBootBlock[0x08] = aulHash[0]           # chunks hash
        aBootBlock[0x09] = aulHash[1]           # chunks hash
        aBootBlock[0x0a] = aulHash[2]           # chunks hash
        aBootBlock[0x0b] = aulHash[3]           # chunks hash
        aBootBlock[0x0c] = aulHash[4]           # chunks hash
        aBootBlock[0x0d] = aulHash[5]           # chunks hash
        aBootBlock[0x0e] = aulHash[6]           # chunks hash
        aBootBlock[0x0f] = 0x00000000           # simple header checksum

        return aBootBlock

    def __combine_headers(self, atHeaderStandard):
        """ Combine the override elements with the standard header """
        aCombinedHeader = array.array('I', [0] * 16)

        ulBootblockChecksum = 0
        for iCnt in range(0, 15):
            if self.__atHeaderOverride[iCnt] is None:
                ulData = atHeaderStandard[iCnt]
            else:
                ulData = self.__atHeaderOverride[iCnt]
            aCombinedHeader[iCnt] = ulData
            ulBootblockChecksum += ulData
            ulBootblockChecksum &= 0xffffffff
        ulBootblockChecksum = (ulBootblockChecksum - 1) ^ 0xffffffff

        # Does an override element exist for the checksum?
        if self.__atHeaderOverride[0x0f] is None:
            ulData = ulBootblockChecksum
        else:
            # Override the checksum.
            ulData = self.__atHeaderOverride[0x0f]
        aCombinedHeader[0x0f] = ulData

        return aCombinedHeader

    def __find_file(self, strFilePath):
        strAbsFilePath = None

        # Is this a file reference?
        if strFilePath[0] == '@':
            strFileId = strFilePath[1:]
            if strFileId in self.__atKnownFiles:
                tFile = self.__atKnownFiles[strFileId]
                if isinstance(tFile, basestring):
                    strAbsFilePath = tFile
                else:
                    strAbsFilePath = tFile.get_path()
        else:
            # Try the current working directory first.
            if os.access(strFilePath, os.R_OK) == True:
                strAbsFilePath = os.path.abspath(strFilePath)
            else:
                # Loop over all include folders.
                for strIncludePath in self.__astrIncludePaths:
                    strPath = os.path.abspath(os.path.join(strIncludePath, strFilePath))
                    if os.access(strPath, os.R_OK) == True:
                        strAbsFilePath = strPath
                        break

        return strAbsFilePath

    def __parse_numeric_expression(self, strExpression):
        tAstNode = ast.parse(strExpression, mode='eval')
        tAstResolved = self.__cPatchDefinitions.resolve_constants(tAstNode)
        ulResult = eval(compile(tAstResolved, 'lala', mode='eval'))
        # TODO: is this really necessary? Maybe ast.literal_eval throws
        # something already.
        if ulResult is None:
            raise Exception('Invalid number: "%s"' % strExpression)
        return ulResult

    def __parse_header_options(self, tOptionsNode):
        # Loop over all child nodes.
        for tValueNode in tOptionsNode.childNodes:
            if tValueNode.nodeType == tValueNode.ELEMENT_NODE:
                if tValueNode.localName == 'Value':
                    # Found a value node. It must have an index attribute which
                    # evaluates to a number between 0 and 15.
                    strIndex = tValueNode.getAttribute('index')
                    if len(strIndex) == 0:
                        raise Exception('The Value node has no index attribute!')
                    ulIndex = self.__parse_numeric_expression(strIndex)

                    # The index must be >=0 and <16.
                    if (ulIndex < 0) or (ulIndex > 15):
                        raise Exception('The index exceeds the valid range of [0..15]: %d' % ulIndex)

                    # Get the data.
                    strData = self.__xml_get_all_text(tValueNode)
                    if len(strData) == 0:
                        raise Exception('The Value node has no content!')

                    ulData = self.__parse_numeric_expression(strData)
                    # The data must be an unsigned 32bit number.
                    if (ulData < 0) or (ulIndex > 0xffffffff):
                        raise Exception('The data exceeds the valid range of an unsigned 32bit number: %d' % ulData)

                    # Is the index already modified?
                    if not self.__atHeaderOverride[ulIndex] is None:
                        raise Exception('The value at index %d is already set to 0x%08x!' % (ulIndex, ulData))

                    # Set the value.
                    self.__atHeaderOverride[ulIndex] = ulData
                else:
                    raise Exception('Unexpected node: %s', tValueNode.localName)

    def __append_32bit(self, atData, ulValue):
        atData.append(ulValue & 0xff)
        atData.append((ulValue >> 8) & 0xff)
        atData.append((ulValue >> 16) & 0xff)
        atData.append((ulValue >> 24) & 0xff)

    def __crc16(self, strData):
        usCrc = 0
        for uiCnt in range(0, len(strData)):
            ucByte = ord(strData[uiCnt])
            usCrc = (usCrc >> 8) | ((usCrc & 0xff) << 8)
            usCrc ^= ucByte
            usCrc ^= (usCrc & 0xff) >> 4
            usCrc ^= (usCrc & 0x0f) << 12
            usCrc ^= ((usCrc & 0xff) << 4) << 1
        return usCrc

    def __build_chunk_options(self, tChunkNode):
        atChunk = None

        # Compile the options definition to a string of bytes.
        tOptionCompiler = OptionCompiler(self.__cPatchDefinitions)
        tOptionCompiler.process(tChunkNode)
        strData = tOptionCompiler.tostring()

        # Return the plain option chunk for SECMEM images.
        # Add a header otherwise.
        if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
            atChunk = array.array('B')
            atChunk.fromstring(strData)
        else:
            if self.__uiNetxType == 56:
                # Pad the option chunk plus a CRC16 to 32 bit size.
                strPadding = chr(0x00) * ((4 - ((len(strData) + 2) % 4)) & 3)
                strChunk = strData + strPadding

                # Get the CRC16 for the chunk.
                usCrc = self.__crc16(strChunk)
                strChunk += chr((usCrc >> 8) & 0xff)
                strChunk += chr(usCrc & 0xff)

                aulData = array.array('I')
                aulData.fromstring(strChunk)

                atChunk = array.array('I')
                atChunk.append(self.__get_tag_id('O', 'P', 'T', 'S'))
                atChunk.append(len(aulData))
                atChunk.extend(aulData)

            elif self.__uiNetxType == 4000:
                # Pad the option chunk to 32 bit size.
                strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
                strChunk = strData + strPadding

                aulData = array.array('I')
                aulData.fromstring(strChunk)

                atChunk = array.array('I')
                atChunk.append(self.__get_tag_id('O', 'P', 'T', 'S'))
                atChunk.append(len(aulData) + self.__sizHashDw)
                atChunk.extend(aulData)

                # Get the hash for the chunk.
                tHash = hashlib.sha384()
                tHash.update(atChunk.tostring())
                strHash = tHash.digest()
                aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
                atChunk.extend(aulHash)

        return atChunk

    def __get_data_contents(self, tDataNode, atData):
        strData = None
        pulLoadAddress = None

        # Look for a child node named "File".
        for tNode in tDataNode.childNodes:
            # Is this a node element?
            if tNode.nodeType == tNode.ELEMENT_NODE:
                # Is this a "File" node?
                if tNode.localName == 'File':
                    # Get the file name.
                    strFileName = tNode.getAttribute('name')
                    if len(strFileName) == 0:
                        raise Exception("The file node has no name attribute!")

                    # Search the file in the current working folder and all
                    # include paths.
                    strAbsFilePath = self.__find_file(strFileName)
                    if strAbsFilePath is None:
                        raise Exception('File %s not found!' % strFileName)

                    # Is this an ELF file?
                    strRoot, strExtension = os.path.splitext(strAbsFilePath)
                    if strExtension == '.elf':
                        # Extract the segments.
                        atSegments = elf_support.get_segment_table(self.__tEnv, strAbsFilePath)
                        # Get the estimated binary size from the segments.
                        ulEstimatedBinSize = elf_support.get_estimated_bin_size(atSegments)
                        # Do not create files larger than 512MB.
                        if ulEstimatedBinSize >= 0x20000000:
                            raise Exception("The resulting file seems to extend 512MBytes. Too scared to continue!")

                        pulLoadAddress = elf_support.get_load_address(atSegments)

                        # Extract the binary.
                        tBinFile, strBinFileName = tempfile.mkstemp()
                        os.close(tBinFile)
                        subprocess.check_call([self.__tEnv['OBJCOPY'], '-O', 'binary', strAbsFilePath, strBinFileName])

                        # Get the application data.
                        tBinFile = open(strBinFileName, 'rb')
                        strData = tBinFile.read()
                        tBinFile.close()

                        # Remove the temp file.
                        os.remove(strBinFileName)

                    elif strExtension == '.bin':
                        strLoadAddress = tNode.getAttribute('load_address')
                        if len(strLoadAddress) == 0:
                            raise Exception('The File node points to a binary file and has no load_address attribute!')

                        pulLoadAddress = self.__parse_numeric_expression(strLoadAddress)

                        tBinFile = open(strAbsFilePath, 'rb')
                        strData = tBinFile.read()
                        tBinFile.close()

                    else:
                        raise Exception('The File node points to a file with an unknown extension: %s' % strExtension)
                # Is this a node element with the name 'Hex'?
                elif tNode.localName == 'Hex':
                    # Get the address.
                    strAddress = tNode.getAttribute('address')
                    if len(strAddress) == 0:
                        raise Exception("The file node has no address attribute!")

                    pulLoadAddress = self.__parse_numeric_expression(strAddress)

                    # Get the text in this node and parse it as hex data.
                    strDataHex = self.__xml_get_all_text(tNode)
                    if strDataHex is None:
                        raise Exception('No text in node "Hex" found!')

                    strDataHex = self.__remove_all_whitespace(strDataHex)
                    strData = binascii.unhexlify(strDataHex)
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        # Check if all parameters are there.
        if strData is None:
            raise Exception('No data specified!')
        if pulLoadAddress is None:
            raise Exception('No load address specified!')

        atData['data'] = strData
        atData['load_address'] = pulLoadAddress

    def __build_chunk_data(self, tChunkNode):
        # Get the data block.
        atData = {}
        self.__get_data_contents(tChunkNode, atData)
        strData = atData['data']
        pulLoadAddress = atData['load_address']

        # Pad the application size to a multiple of DWORDs.
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('D', 'A', 'T', 'A'))
        aulChunk.append(len(aulData) + 1 + self.__sizHashDw)
        aulChunk.append(pulLoadAddress)
        aulChunk.extend(aulData)

        # Get the hash for the chunk.
        tHash = hashlib.sha384()
        tHash.update(aulChunk.tostring())
        strHash = tHash.digest()
        aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
        aulChunk.extend(aulHash)

        return aulChunk

    def __get_execute_data(self, tExecuteNode, atData):
        pfnExecFunction = None
        ulR0 = None
        ulR1 = None
        ulR2 = None
        ulR3 = None

        # Look for a child node named "File".
        for tNode in tExecuteNode.childNodes:
            # Is this a node element?
            if tNode.nodeType == tNode.ELEMENT_NODE:
                # Is this a "File" node?
                if tNode.localName == 'File':
                    # Is there already an exec function?
                    if pfnExecFunction is not None:
                        raise Exception('More than one execution address specified!')

                    # Get the file name.
                    strFileName = tNode.getAttribute('name')
                    if len(strFileName) == 0:
                        raise Exception("The file node has no name attribute!")

                    # Search the file in the current working folder and all
                    # include paths.
                    strAbsFilePath = self.__find_file(strFileName)
                    if strAbsFilePath is None:
                        raise Exception('File %s not found!' % strFileName)

                    # Is this an ELF file?
                    strRoot, strExtension = os.path.splitext(strAbsFilePath)
                    if strExtension != '.elf':
                        raise Exception('The execute chunk has a file child which points to a non-elf file. How to get the execute address from this?')

                    strStartSymbol = tNode.getAttribute('start')
                    if len(strStartSymbol) == 0:
                        strStartSymbol = 'start'

                    # Get all symbols.
                    atSymbols = elf_support.get_symbol_table(self.__tEnv, strAbsFilePath)
                    if strStartSymbol not in atSymbols:
                        raise Exception('The symbol for the start startaddress "%s" could not be found!' % strStartSymbol)
                    pfnExecFunction = long(atSymbols[strStartSymbol])
                elif tNode.localName == 'Address':
                    # Is there already an exec function?
                    if pfnExecFunction is not None:
                        raise Exception('More than one execution address specified!')

                    pfnExecFunction = self.__parse_numeric_expression(self.__xml_get_all_text(tNode))
                elif tNode.localName == 'R0':
                    ulR0 = self.__parse_numeric_expression(self.__xml_get_all_text(tNode))
                elif tNode.localName == 'R1':
                    ulR1 = self.__parse_numeric_expression(self.__xml_get_all_text(tNode))
                elif tNode.localName == 'R2':
                    ulR2 = self.__parse_numeric_expression(self.__xml_get_all_text(tNode))
                elif tNode.localName == 'R3':
                    ulR3 = self.__parse_numeric_expression(self.__xml_get_all_text(tNode))
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        if pfnExecFunction is None:
            raise Exception('No execution address specified!')
        if ulR0 is None:
            ulR0 = 0
        if ulR1 is None:
            ulR1 = 0
        if ulR2 is None:
            ulR2 = 0
        if ulR3 is None:
            ulR3 = 0

        atData['pfnExecFunction'] = pfnExecFunction
        atData['ulR0'] = ulR0
        atData['ulR1'] = ulR1
        atData['ulR2'] = ulR2
        atData['ulR3'] = ulR3

    def __build_chunk_execute(self, tChunkNode):
        __atData = {
            # The key index must be set by the user.
            'pfnExecFunction': None,
            'ulR0': None,
            'ulR1': None,
            'ulR2': None,
            'ulR3': None
        }
        self.__get_execute_data(tChunkNode, __atData)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('E', 'X', 'E', 'C'))
        aulChunk.append(5 + self.__sizHashDw)
        aulChunk.append(__atData['pfnExecFunction'])
        aulChunk.append(__atData['ulR0'])
        aulChunk.append(__atData['ulR1'])
        aulChunk.append(__atData['ulR2'])
        aulChunk.append(__atData['ulR3'])

        # Get the hash for the chunk.
        tHash = hashlib.sha384()
        tHash.update(aulChunk.tostring())
        strHash = tHash.digest()
        aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
        aulChunk.extend(aulHash)

        return aulChunk

    def __build_chunk_execute_ca9(self, tChunkNode):
        __atCore0 = {
            # The key index must be set by the user.
            'pfnExecFunction': 0,
            'ulR0': 0,
            'ulR1': 0,
            'ulR2': 0,
            'ulR3': 0
        }
        __atCore1 = {
            # The key index must be set by the user.
            'pfnExecFunction': 0,
            'ulR0': 0,
            'ulR1': 0,
            'ulR2': 0,
            'ulR3': 0
        }

        # Look for a child node named "File".
        for tCoreNode in tChunkNode.childNodes:
            # Is this a node element?
            if tCoreNode.nodeType == tCoreNode.ELEMENT_NODE:
                # Is this a 'Core0' node?
                if tCoreNode.localName == 'Core0':
                    self.__get_execute_data(tCoreNode, __atCore0)

                # Is this a 'Core1' node?
                elif tCoreNode.localName == 'Core1':
                    self.__get_execute_data(tCoreNode, __atCore1)

                else:
                    raise Exception('Unexpected node: %s', tCoreNode.localName)

        if (__atCore0['pfnExecFunction'] == 0) and (__atCore1['pfnExecFunction'] == 0):
            raise Exception('No core is started with the ExecuteCA9 chunk!')

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('E', 'X', 'A', '9'))
        aulChunk.append(10 + self.__sizHashDw)
        aulChunk.append(__atCore0['pfnExecFunction'])
        aulChunk.append(__atCore0['ulR0'])
        aulChunk.append(__atCore0['ulR1'])
        aulChunk.append(__atCore0['ulR2'])
        aulChunk.append(__atCore0['ulR3'])
        aulChunk.append(__atCore1['pfnExecFunction'])
        aulChunk.append(__atCore1['ulR0'])
        aulChunk.append(__atCore1['ulR1'])
        aulChunk.append(__atCore1['ulR2'])
        aulChunk.append(__atCore1['ulR3'])

        # Get the hash for the chunk.
        tHash = hashlib.sha384()
        tHash.update(aulChunk.tostring())
        strHash = tHash.digest()
        aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
        aulChunk.extend(aulHash)

        return aulChunk

    def __build_chunk_spi_macro(self, tChunkNode):
        # Get the device.
        strDeviceName = tChunkNode.getAttribute('device')
        if len(strDeviceName) == 0:
            raise Exception('The SPI macro node has no device attribute!')

        # Parse the data.
        ulDevice = self.__parse_numeric_expression(strDeviceName)

        tOptionCompiler = OptionCompiler(self.__cPatchDefinitions)
        strMacroData = tOptionCompiler.get_spi_macro_data(tChunkNode)

        # Prepend the device and the size.
        sizMacro = len(strMacroData)
        if sizMacro > 255:
            raise Exception('The SPI macro is too long. The header can only indicate up to 255 bytes.')
        strData = chr(ulDevice) + chr(sizMacro) + strMacroData

        # Pad the macro to a multiple of dwords.
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('S', 'P', 'I', 'M'))
        aulChunk.append(len(aulData) + self.__sizHashDw)
        aulChunk.extend(aulData)

        # Get the hash for the chunk.
        tHash = hashlib.sha384()
        tHash.update(aulChunk.tostring())
        strHash = tHash.digest()
        aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
        aulChunk.extend(aulHash)

        return aulChunk

    def __build_chunk_skip(self, tChunkNode):
        # Get the device.
        strAbsolute = tChunkNode.getAttribute('absolute')
        sizAbsolute = len(strAbsolute)
        strRelative = tChunkNode.getAttribute('relative')
        sizRelative = len(strRelative)

        sizSkip = 0

        if (sizAbsolute == 0) and (sizRelative == 0):
            raise Exception('The skip node has no "absolute" or "relative" attribute!')
        elif (sizAbsolute != 0) and (sizRelative != 0):
            raise Exception('The skip node has an "absolute" and a "relative" attribute!')
        elif sizAbsolute != 0:
            # Parse the data.
            sizOffsetNew = self.__parse_numeric_expression(strAbsolute) * 4
            sizOffsetCurrent = len(self.__atChunks) * 4
            if sizOffsetNew < sizOffsetCurrent:
                raise Exception('Skip tries to set the offset back from %d to %d.' % (sizOffsetCurrent, sizOffsetNew))
            sizSkip = (sizOffsetNew - sizOffsetCurrent) / 4
        else:
            # Parse the data.
            sizSkip = self.__parse_numeric_expression(strRelative)
            if sizSkip < 0:
                raise Exception('Skip does not accept a negative value for the relative attribute:' % sizSkip)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('S', 'K', 'I', 'P'))
        aulChunk.append(sizSkip + self.__sizHashDw)

        # Get the hash for the chunk.
        tHash = hashlib.sha384()
        tHash.update(aulChunk.tostring())
        strHash = tHash.digest()
        aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
        aulChunk.extend(aulHash)

        # Append the placeholder for the skip area.
        aulChunk.extend([0xffffffff] * sizSkip)

        return aulChunk

    def __remove_all_whitespace(self, strData):
        astrWhitespace = [' ', '\t', '\n', '\r']
        for strWhitespace in astrWhitespace:
            strData = string.replace(strData, strWhitespace, '')
        return strData

    # This function gets a data block from the OpenSSL output.
    def __openssl_get_data_block(self, strStdout, strID):
        strDataMirror = ''
        tReData = re.compile('^\s+[0-9a-fA-F]{2}(:[0-9a-fA-F]{2})*:?$')
        iState = 0
        for strLine in iter(strStdout.splitlines()):
            if iState == 0:
                if strLine == strID:
                    iState = 1
            elif iState == 1:
                tMatch = tReData.search(strLine)
                if tMatch is None:
                    break
                else:
                    for strData in string.split(strLine, ':'):
                        strDataMirror += string.strip(strData)

        # Skip the first byte and mirror the string.
        strDataMirrorBin = binascii.unhexlify(strDataMirror)
        strDataBin = ''
        for iCnt in range(len(strDataMirrorBin) - 1, 0, -1):
            strDataBin += strDataMirrorBin[iCnt]

        return strDataBin

    def __keyrom_get_key(self, uiIndex):
        # This needs the keyrom data.
        if self.__XmlKeyromContents is None:
            raise Exception('No Keyrom contents specified!')

        # Find the requested key and hash.
        tNode = self.__XmlKeyromContents.find('Entry/[@index="%d"]' % uiIndex)
        if tNode is None:
            raise Exception('Key %d was not found!' % uiIndex)
        tNode_key = tNode.find('Key')
        if tNode_key is None:
            raise Exception('Key %d has no "Key" child!' % uiIndex)
        tNode_hash = tNode.find('Hash')
        if tNode_hash is None:
            raise Exception('Key %d has no "Hash" child!' % uiIndex)

        strKeyBase64 = tNode_key.text

        # Decode the BASE64 data. Now we have the key pair in DER format.
        strKeyDER = base64.b64decode(strKeyBase64)

        return strKeyDER

    def __get_cert_mod_exp(self, tNodeParent, uiIndex):
        __atKnownRsaSizes = {
            0: {'mod': 256, 'exp': 3, 'rsa': 2048},
            1: {'mod': 384, 'exp': 3, 'rsa': 3072},
            2: {'mod': 512, 'exp': 3, 'rsa': 4096}
        }

        # Get the key in DER encoded format.
        strKeyDER = self.__keyrom_get_key(uiIndex)

        # Extract all information from the key.
        tProcess = subprocess.Popen([self.__cfg_openssl, 'rsa', '-inform', 'DER', '-text', '-noout'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (strStdout, strStdErr) = tProcess.communicate(strKeyDER)
        if tProcess.returncode != 0:
            raise Exception('OpenSSL failed with return code %d.' % tProcess.returncode)

        # Extract the public exponent.
        tReExp = re.compile('^publicExponent:\s+(\d+)\s+\(0x([0-9a-fA-F]+)\)$', re.MULTILINE)
        tMatch = tReExp.search(strStdout)
        if tMatch is None:
            raise Exception('Can not find public exponent!')
        ulExp = long(tMatch.group(1))
        ulExpHex = long(tMatch.group(2), 16)
        if ulExp != ulExpHex:
            raise Exception('Decimal version differs from hex version!')
        if (ulExp < 0) or (ulExp > 0xffffff):
            raise Exception('The exponent exceeds the allowed range of a 24bit unsigned integer!')
        strData = chr(ulExp & 0xff) + chr((ulExp >> 8) & 0xff) + chr((ulExp >> 16) & 0xff)
        aucExp = array.array('B', strData)
        sizExp = len(aucExp)

        # Extract the modulus "N".
        strData = self.__openssl_get_data_block(strStdout, 'modulus:')
        aucMod = array.array('B', strData)
        sizMod = len(aucMod)

        uiId = None
        for uiElementId, atAttr in __atKnownRsaSizes.iteritems():
            if (sizMod == atAttr['mod']) and (sizExp == atAttr['exp']):
                # Found the RSA type.
                uiId = uiElementId
                break

        if uiId is None:
            strErr = 'The modulo has a size of %d bytes. The public exponent has a size of %d bytes.\n' % (sizMod, sizExp)
            strErr += 'These values can not be mapped to a RSA bit size. Known sizes are:\n'
            for uiElementId, atAttr in __atKnownRsaSizes.iteritems():
                strErr += '  RSA%d: %d bytes modulo, %d bytes public exponent\n' % (atAttr['rsa'], atAttr['mod'], atAttr['exp'])
            raise Exception(strErr)

        return (uiId, aucMod, aucExp)

    def __cert_parse_binding(self, tNodeParent, strName):
        # The binding is not yet set.
        strBinding = None

        # Loop over all child nodes.
        for tNode in tNodeParent.childNodes:
            if (tNode.nodeType == tNode.ELEMENT_NODE) and (tNode.localName == strName):
                strBinding = self.__xml_get_all_text(tNode)

        if strBinding is None:
            raise Exception('No "%s" node found!' % strName)

        strBinding = self.__remove_all_whitespace(strBinding)
        aucBinding = array.array('B', binascii.unhexlify(strBinding))
        sizBinding = len(aucBinding)

        if sizBinding != 64:
            raise Exception('The binding in node "%s" has an invalid size of %d bytes.' % (strName, sizBinding))

        return aucBinding

    def __root_cert_parse_root_public_key(self, tNodeParent, atData):
        # Get the index.
        strIdx = tNodeParent.getAttribute('idx')
        if len(strIdx) == 0:
            raise Exception('No "idx" attribute found!')
        ulIdx = self.__parse_numeric_expression(strIdx)

        (uiId, aucMod, aucExp) = self.__get_cert_mod_exp(tNodeParent, ulIdx)

        atData['id'] = uiId
        atData['mod'] = aucMod
        atData['exp'] = aucExp
        atData['idx'] = ulIdx

    def __cert_get_key_index(self, tNodeParent, atData):
        # Get the index.
        strIdx = tNodeParent.getAttribute('idx')
        if len(strIdx) == 0:
            raise Exception('No "idx" attribute found!')
        ulIdx = self.__parse_numeric_expression(strIdx)

        atData['idx'] = ulIdx

    def __root_cert_parse_binding(self, tNodeParent, atData):
        atData['mask'] = self.__cert_parse_binding(tNodeParent, 'Mask')
        atData['ref'] = self.__cert_parse_binding(tNodeParent, 'Ref')

    def __root_cert_parse_new_register_values(self, tNodeParent, atData):
        atValues = array.array('B')

        # Loop over all child nodes.
        for tNode in tNodeParent.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'Value':
                    # Get the bit offset and bit size.
                    strBitOffset = tNode.getAttribute('offset')
                    if len(strBitOffset) == 0:
                        raise Exception('No "offset" attribute found!')
                    ulBitOffset = self.__parse_numeric_expression(strBitOffset)
                    if (ulBitOffset < 0) or (ulBitOffset > 511):
                        raise Exception('The offset is out of range: %d' % ulBitOffset)

                    strBitSize = tNode.getAttribute('size')
                    if len(strBitSize) == 0:
                        raise Exception('No "size" attribute found!')
                    ulBitSize = self.__parse_numeric_expression(strBitSize)
                    if (ulBitSize < 1) or (ulBitSize > 128):
                        raise Exception('The size is out of range: %d' % ulBitSize)
                    if (ulBitOffset + ulBitSize) > 512:
                        raise Exception('The area specified by offset %d and size %d exceeds the array.' % (ulBitOffset. ulBitSize))

                    # Get the text in this node and parse it as hex data.
                    strData = self.__xml_get_all_text(tNode)
                    if strData is None:
                        raise Exception('No text in node "Value" found!')

                    strData = self.__remove_all_whitespace(strData)
                    aucData = binascii.unhexlify(strData)
                    sizData = len(aucData)

                    # The bit size must fit into the data.
                    sizReqBytes = int(math.ceil(ulBitSize / 8.0))
                    if sizReqBytes != sizData:
                        strErr = 'The size of the data does not match the requested size in bits.\n'
                        strErr += 'Data size: %d bytes\n' % sizData
                        strErr += 'Requested size: %d bits' % sizReqBytes
                        raise Exception(strErr)

                    # Combine the offset and size.
                    ulBnv = ulBitOffset | ((ulBitSize - 1) * 512)

                    # Append all data to the array.
                    atValues.append(ulBnv & 0xff)
                    atValues.append((ulBnv >> 8) & 0xff)
                    atValues.extend(array.array('B', aucData))

                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        if len(atValues) > 255:
            raise Exception('The new register values are too long!')

        atData['data'] = atValues

    def __root_cert_parse_trusted_path(self, tNodeParent, atData):
        # Get the index.
        strIdx = tNodeParent.getAttribute('idx')
        if len(strIdx) == 0:
            raise Exception('No "idx" attribute found!')
        ulIdx = self.__parse_numeric_expression(strIdx)

        (uiId, aucMod, aucExp) = self.__get_cert_mod_exp(tNodeParent, ulIdx)

        aucMask = self.__cert_parse_binding(tNodeParent, 'Mask')

        atData['mask'] = aucMask
        atData['id'] = uiId
        atData['mod'] = aucMod
        atData['exp'] = aucExp

    def __root_cert_parse_user_content(self, tNodeParent, atData):
        atValues = array.array('B')

        # Loop over all child nodes.
        for tNode in tNodeParent.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'Text':
                    strData = self.__xml_get_all_text(tNode)
                    atValues.extend(array.array('B', strData))
                elif tNode.localName == 'Hex':
                    strData = self.__xml_get_all_text(tNode)
                    strData = binascii.unhexlify(self.__remove_all_whitespace(strData))
                    atValues.extend(array.array('B', strData))
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        atData['data'] = atValues

    def __build_chunk_root_cert(self, tChunkNode):
        # Generate an array with default values where possible.
        __atRootCert = {
            # The RootPublicKey must be set by the user.
            'RootPublicKey': {
                'id': None,
                'mod': None,
                'exp': None,
                'idx': None
            },

            # The Binding must be set by the user.
            'Binding': {
                'mask': None,
                'ref': None
            },

            # The new register values are empty by default.
            'NewRegisterValues': {
                'data': ''
            },

            # The TrustedPathLicense must be set by the user.
            'TrustedPathLicense': {
                'mask': None,
                'id': None,
                'mod': None,
                'exp': None,
            },

            # The TrustedPathCr7Sw must be set by the user.
            'TrustedPathCr7Sw': {
                'mask': None,
                'id': None,
                'mod': None,
                'exp': None,
            },

            # The TrustedPathCa9Sw must be set by the user.
            'TrustedPathCa9Sw': {
                'mask': None,
                'id': None,
                'mod': None,
                'exp': None,
            },

            # The user content is empty by default.
            'UserContent': {
                'data': ''
            }
        }

        # Loop over all children.
        for tNode in tChunkNode.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'RootPublicKey':
                    self.__root_cert_parse_root_public_key(tNode, __atRootCert['RootPublicKey'])
                elif tNode.localName == 'Binding':
                    self.__root_cert_parse_binding(tNode, __atRootCert['Binding'])
                elif tNode.localName == 'NewRegisterValues':
                    self.__root_cert_parse_new_register_values(tNode, __atRootCert['NewRegisterValues'])
                elif tNode.localName == 'TrustedPathLicense':
                    self.__root_cert_parse_trusted_path(tNode, __atRootCert['TrustedPathLicense'])
                elif tNode.localName == 'TrustedPathCr7Sw':
                    self.__root_cert_parse_trusted_path(tNode, __atRootCert['TrustedPathCr7Sw'])
                elif tNode.localName == 'TrustedPathCa9Sw':
                    self.__root_cert_parse_trusted_path(tNode, __atRootCert['TrustedPathCa9Sw'])
                elif tNode.localName == 'UserContent':
                    self.__root_cert_parse_user_content(tNode, __atRootCert['UserContent'])
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        # Check if all required data was set.
        astrErr = []
        if __atRootCert['RootPublicKey']['id'] is None:
            astrErr.append('No "id" set in the RootPublicKey.')
        if __atRootCert['RootPublicKey']['mod'] is None:
            astrErr.append('No "mod" set in the RootPublicKey.')
        if __atRootCert['RootPublicKey']['exp'] is None:
            astrErr.append('No "exp" set in the RootPublicKey.')
        if __atRootCert['RootPublicKey']['idx'] is None:
            astrErr.append('No "idx" set in the RootPublicKey.')
        if __atRootCert['Binding']['mask'] is None:
            astrErr.append('No "mask" set in the Binding.')
        if __atRootCert['Binding']['ref'] is None:
            astrErr.append('No "ref" set in the Binding.')
        if __atRootCert['TrustedPathLicense']['mask'] is None:
            astrErr.append('No "mask" set in the TrustedPathLicense.')
        if __atRootCert['TrustedPathLicense']['id'] is None:
            astrErr.append('No "id" set in the TrustedPathLicense.')
        if __atRootCert['TrustedPathLicense']['mod'] is None:
            astrErr.append('No "mod" set in the TrustedPathLicense.')
        if __atRootCert['TrustedPathLicense']['exp'] is None:
            astrErr.append('No "exp" set in the TrustedPathLicense.')
        if __atRootCert['TrustedPathCr7Sw']['mask'] is None:
            astrErr.append('No "mask" set in the TrustedPathCr7Sw.')
        if __atRootCert['TrustedPathCr7Sw']['id'] is None:
            astrErr.append('No "id" set in the TrustedPathCr7Sw.')
        if __atRootCert['TrustedPathCr7Sw']['mod'] is None:
            astrErr.append('No "mod" set in the TrustedPathCr7Sw.')
        if __atRootCert['TrustedPathCr7Sw']['exp'] is None:
            astrErr.append('No "exp" set in the TrustedPathCr7Sw.')
        if __atRootCert['TrustedPathCa9Sw']['mask'] is None:
            astrErr.append('No "mask" set in the TrustedPathCa9Sw.')
        if __atRootCert['TrustedPathCa9Sw']['id'] is None:
            astrErr.append('No "id" set in the TrustedPathCa9Sw.')
        if __atRootCert['TrustedPathCa9Sw']['mod'] is None:
            astrErr.append('No "mod" set in the TrustedPathCa9Sw.')
        if __atRootCert['TrustedPathCa9Sw']['exp'] is None:
            astrErr.append('No "exp" set in the TrustedPathCa9Sw.')
        if len(astrErr) != 0:
            raise Exception('\n'.join(astrErr))

        # Combine all data to the chunk.
        atData = array.array('B')

        atData.append(__atRootCert['RootPublicKey']['id'])
        atData.extend(__atRootCert['RootPublicKey']['mod'])
        atData.extend(__atRootCert['RootPublicKey']['exp'])
        atData.append((__atRootCert['RootPublicKey']['idx']) & 0xff)
        atData.append(((__atRootCert['RootPublicKey']['idx']) >> 8) & 0xff)

        atData.extend(__atRootCert['Binding']['mask'])
        atData.extend(__atRootCert['Binding']['ref'])

        sizData = len(__atRootCert['NewRegisterValues']['data'])
        atData.append(sizData)
        atData.extend(__atRootCert['NewRegisterValues']['data'])

        atData.extend(__atRootCert['TrustedPathLicense']['mask'])
        atData.append(__atRootCert['TrustedPathLicense']['id'])
        atData.extend(__atRootCert['TrustedPathLicense']['mod'])
        atData.extend(__atRootCert['TrustedPathLicense']['exp'])

        atData.extend(__atRootCert['TrustedPathCr7Sw']['mask'])
        atData.append(__atRootCert['TrustedPathCr7Sw']['id'])
        atData.extend(__atRootCert['TrustedPathCr7Sw']['mod'])
        atData.extend(__atRootCert['TrustedPathCr7Sw']['exp'])

        atData.extend(__atRootCert['TrustedPathCa9Sw']['mask'])
        atData.append(__atRootCert['TrustedPathCa9Sw']['id'])
        atData.extend(__atRootCert['TrustedPathCa9Sw']['mod'])
        atData.extend(__atRootCert['TrustedPathCa9Sw']['exp'])

        sizData = len(__atRootCert['UserContent']['data'])
        atData.append(sizData & 0xff)
        atData.append((sizData >> 8) & 0xff)
        atData.append((sizData >> 16) & 0xff)
        atData.append((sizData >> 32) & 0xff)
        atData.extend(__atRootCert['UserContent']['data'])

        # Get the key in DER encoded format.
        strKeyDER = self.__keyrom_get_key(__atRootCert['RootPublicKey']['idx'])

        # Create a temporary file for the keypair.
        iFile, strPathKeypair = tempfile.mkstemp(suffix='der', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Create a temporary file for the data to sign.
        iFile, strPathSignatureInputData = tempfile.mkstemp(suffix='bin', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Write the DER key to the temporary file.
        tFile = open(strPathKeypair, 'wt')
        tFile.write(strKeyDER)
        tFile.close()

        # Write the data to sign to the temporary file.
        tFile = open(strPathSignatureInputData, 'wb')
        tFile.write(atData.tostring())
        tFile.close()

        strSignature = subprocess.check_output([self.__cfg_openssl, 'dgst', '-sign', strPathKeypair, '-keyform', 'DER', '-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:-1', '-sha384', strPathSignatureInputData])

        # Remove the temp files.
        os.remove(strPathKeypair)
        os.remove(strPathSignatureInputData)

        # Append the signature to the chunk.
        aulSignature = array.array('B', strSignature)
        atData.extend(aulSignature)

        # Pad the data to a multiple of dwords.
        strData = atData.tostring()
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('R', 'C', 'R', 'T'))
        aulChunk.append(len(aulData))
        aulChunk.extend(aulData)

        return aulChunk

    def __build_chunk_license_cert(self, tChunkNode):
        # Generate an array with default values where possible.
        __atCert = {
            # The key index must be set by the user.
            'Key': {
                'idx': None
            },

            # The Binding must be set by the user.
            'Binding': {
                'mask': None,
                'ref': None
            },

            # The new register values are empty by default.
            'NewRegisterValues': {
                'data': ''
            },

            # The user content is empty by default.
            'UserContent': {
                'data': ''
            }
        }

        # Loop over all children.
        for tNode in tChunkNode.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'Key':
                    self.__cert_get_key_index(tNode, __atCert['Key'])
                elif tNode.localName == 'Binding':
                    self.__root_cert_parse_binding(tNode, __atCert['Binding'])
                elif tNode.localName == 'NewRegisterValues':
                    self.__root_cert_parse_new_register_values(tNode, __atCert['NewRegisterValues'])
                elif tNode.localName == 'UserContent':
                    self.__root_cert_parse_user_content(tNode, __atCert['UserContent'])
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        # Check if all required data was set.
        astrErr = []
        if __atCert['Key']['idx'] is None:
            astrErr.append('No "idx" set in the LicenseCert.')
        if __atCert['Binding']['mask'] is None:
            astrErr.append('No "mask" set in the Binding.')
        if __atCert['Binding']['ref'] is None:
            astrErr.append('No "ref" set in the Binding.')
        if len(astrErr) != 0:
            raise Exception('\n'.join(astrErr))

        # Combine all data to the chunk.
        atData = array.array('B')

        atData.extend(__atCert['Binding']['mask'])
        atData.extend(__atCert['Binding']['ref'])

        sizData = len(__atCert['NewRegisterValues']['data'])
        atData.append(sizData)
        atData.extend(__atCert['NewRegisterValues']['data'])

        sizData = len(__atCert['UserContent']['data'])
        atData.append(sizData & 0xff)
        atData.append((sizData >> 8) & 0xff)
        atData.append((sizData >> 16) & 0xff)
        atData.append((sizData >> 32) & 0xff)
        atData.extend(__atCert['UserContent']['data'])

        # Get the key in DER encoded format.
        strKeyDER = self.__keyrom_get_key(__atCert['Key']['idx'])

        # Create a temporary file for the keypair.
        iFile, strPathKeypair = tempfile.mkstemp(suffix='der', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Create a temporary file for the data to sign.
        iFile, strPathSignatureInputData = tempfile.mkstemp(suffix='bin', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Write the DER key to the temporary file.
        tFile = open(strPathKeypair, 'wt')
        tFile.write(strKeyDER)
        tFile.close()

        # Write the data to sign to the temporary file.
        tFile = open(strPathSignatureInputData, 'wb')
        tFile.write(atData.tostring())
        tFile.close()

        strSignature = subprocess.check_output([self.__cfg_openssl, 'dgst', '-sign', strPathKeypair, '-keyform', 'DER', '-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:-1', '-sha384', strPathSignatureInputData])

        # Remove the temp files.
        os.remove(strPathKeypair)
        os.remove(strPathSignatureInputData)

        # Append the signature to the chunk.
        aulSignature = array.array('B', strSignature)
        atData.extend(aulSignature)

        # Pad the data to a multiple of dwords.
        strData = atData.tostring()
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('L', 'C', 'R', 'T'))
        aulChunk.append(len(aulData))
        aulChunk.extend(aulData)

        return aulChunk

    def __build_chunk_cr7sw(self, tChunkNode):
        # Generate an array with default values where possible.
        __atCert = {
            # The key index must be set by the user.
            'Key': {
                'idx': None
            },

            # The Binding must be set by the user.
            'Binding': {
                'mask': None,
                'ref': None
            },

            # The data must be set by the user.
            'Data': {
                'data': None,
                'load_address': None
            },

            # The registers.
            'Execute': {
                'pfnExecFunction': None,
                'ulR0': None,
                'ulR1': None,
                'ulR2': None,
                'ulR3': None
            },

            # The user content is empty by default.
            'UserContent': {
                'data': ''
            }
        }

        # Loop over all children.
        for tNode in tChunkNode.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'Key':
                    self.__cert_get_key_index(tNode, __atCert['Key'])
                elif tNode.localName == 'Binding':
                    self.__root_cert_parse_binding(tNode, __atCert['Binding'])
                elif tNode.localName == 'Data':
                    self.__get_data_contents(tNode, __atCert['Data'])
                elif tNode.localName == 'Execute':
                    self.__get_execute_data(tNode, __atCert['Execute'])
                elif tNode.localName == 'UserContent':
                    self.__root_cert_parse_user_content(tNode, __atCert['UserContent'])
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        # Check if all required data was set.
        astrErr = []
        if __atCert['Key']['idx'] is None:
            astrErr.append('No "idx" set in the LicenseCert.')
        if __atCert['Binding']['mask'] is None:
            astrErr.append('No "mask" set in the Binding.')
        if __atCert['Binding']['ref'] is None:
            astrErr.append('No "ref" set in the Binding.')
        if __atCert['Data']['data'] is None:
            astrErr.append('No "data" set in the Data.')
        if __atCert['Data']['load_address'] is None:
            astrErr.append('No "load_address" set in the Data.')
        if __atCert['Execute']['pfnExecFunction'] is None:
            astrErr.append('No "pfnExecFunction" set in the Execute.')
        if __atCert['Execute']['ulR0'] is None:
            astrErr.append('No "ulR0" set in the Execute.')
        if __atCert['Execute']['ulR1'] is None:
            astrErr.append('No "ulR1" set in the Execute.')
        if __atCert['Execute']['ulR2'] is None:
            astrErr.append('No "ulR2" set in the Execute.')
        if __atCert['Execute']['ulR3'] is None:
            astrErr.append('No "ulR3" set in the Execute.')
        if len(astrErr) != 0:
            raise Exception('\n'.join(astrErr))

        # Combine all data to the chunk.
        atData = array.array('B')

        atData.extend(__atCert['Binding']['mask'])
        atData.extend(__atCert['Binding']['ref'])

        self.__append_32bit(atData, len(__atCert['Data']['data']))
        self.__append_32bit(atData, __atCert['Data']['load_address'])
        atData.extend(array.array('B', __atCert['Data']['data']))

        self.__append_32bit(atData, __atCert['Execute']['pfnExecFunction'])
        self.__append_32bit(atData, __atCert['Execute']['ulR0'])
        self.__append_32bit(atData, __atCert['Execute']['ulR1'])
        self.__append_32bit(atData, __atCert['Execute']['ulR2'])
        self.__append_32bit(atData, __atCert['Execute']['ulR3'])

        self.__append_32bit(atData, len(__atCert['UserContent']['data']))
        atData.extend(__atCert['UserContent']['data'])

        # Get the key in DER encoded format.
        strKeyDER = self.__keyrom_get_key(__atCert['Key']['idx'])

        # Create a temporary file for the keypair.
        iFile, strPathKeypair = tempfile.mkstemp(suffix='der', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Create a temporary file for the data to sign.
        iFile, strPathSignatureInputData = tempfile.mkstemp(suffix='bin', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Write the DER key to the temporary file.
        tFile = open(strPathKeypair, 'wt')
        tFile.write(strKeyDER)
        tFile.close()

        # Write the data to sign to the temporary file.
        tFile = open(strPathSignatureInputData, 'wb')
        tFile.write(atData.tostring())
        tFile.close()

        strSignature = subprocess.check_output([self.__cfg_openssl, 'dgst', '-sign', strPathKeypair, '-keyform', 'DER', '-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:-1', '-sha384', strPathSignatureInputData])

        # Remove the temp files.
        os.remove(strPathKeypair)
        os.remove(strPathSignatureInputData)

        # Append the signature to the chunk.
        aulSignature = array.array('B', strSignature)
        atData.extend(aulSignature)

        # Pad the data to a multiple of dwords.
        strData = atData.tostring()
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('R', '7', 'S', 'W'))
        aulChunk.append(len(aulData))
        aulChunk.extend(aulData)

        return aulChunk

    def __build_chunk_ca9sw(self, tChunkNode):
        # Generate an array with default values where possible.
        __atCert = {
            # The key index must be set by the user.
            'Key': {
                'idx': None
            },

            # The Binding must be set by the user.
            'Binding': {
                'mask': None,
                'ref': None
            },

            # The data must be set by the user.
            'Data': {
                'data': None,
                'load_address': None
            },

            # The registers.
            'Execute_Core0': {
                'pfnExecFunction': None,
                'ulR0': None,
                'ulR1': None,
                'ulR2': None,
                'ulR3': None
            },
            'Execute_Core1': {
                'pfnExecFunction': None,
                'ulR0': None,
                'ulR1': None,
                'ulR2': None,
                'ulR3': None
            },

            # The user content is empty by default.
            'UserContent': {
                'data': ''
            }
        }

        # Loop over all children.
        for tNode in tChunkNode.childNodes:
            if tNode.nodeType == tNode.ELEMENT_NODE:
                if tNode.localName == 'Key':
                    self.__cert_get_key_index(tNode, __atCert['Key'])
                elif tNode.localName == 'Binding':
                    self.__root_cert_parse_binding(tNode, __atCert['Binding'])
                elif tNode.localName == 'Data':
                    self.__get_data_contents(tNode, __atCert['Data'])
                elif tNode.localName == 'Execute':
                    for tRegistersNode in tNode.childNodes:
                        if tRegistersNode.nodeType == tNode.ELEMENT_NODE:
                            if tRegistersNode.localName == 'Core0':
                                self.__get_execute_data(tRegistersNode, __atCert['Execute_Core0'])
                            elif tRegistersNode.localName == 'Core1':
                                self.__get_execute_data(tRegistersNode, __atCert['Execute_Core1'])
                elif tNode.localName == 'UserContent':
                    self.__root_cert_parse_user_content(tNode, __atCert['UserContent'])
                else:
                    raise Exception('Unexpected node: %s', tNode.localName)

        # Check if all required data was set.
        astrErr = []
        if __atCert['Key']['idx'] is None:
            astrErr.append('No "idx" set in the LicenseCert.')
        if __atCert['Binding']['mask'] is None:
            astrErr.append('No "mask" set in the Binding.')
        if __atCert['Binding']['ref'] is None:
            astrErr.append('No "ref" set in the Binding.')
        if __atCert['Data']['data'] is None:
            astrErr.append('No "data" set in the Data.')
        if __atCert['Data']['load_address'] is None:
            astrErr.append('No "load_address" set in the Data.')
        if __atCert['Execute_Core0']['pfnExecFunction'] is None:
            astrErr.append('No "pfnExecFunction" set in the Execute.')
        if __atCert['Execute_Core0']['ulR0'] is None:
            astrErr.append('No "ulR0" set in the Execute.')
        if __atCert['Execute_Core0']['ulR1'] is None:
            astrErr.append('No "ulR1" set in the Execute.')
        if __atCert['Execute_Core0']['ulR2'] is None:
            astrErr.append('No "ulR2" set in the Execute.')
        if __atCert['Execute_Core0']['ulR3'] is None:
            astrErr.append('No "ulR3" set in the Execute.')
        if __atCert['Execute_Core1']['pfnExecFunction'] is None:
            astrErr.append('No "pfnExecFunction" set in the Execute.')
        if __atCert['Execute_Core1']['ulR0'] is None:
            astrErr.append('No "ulR0" set in the Execute.')
        if __atCert['Execute_Core1']['ulR1'] is None:
            astrErr.append('No "ulR1" set in the Execute.')
        if __atCert['Execute_Core1']['ulR2'] is None:
            astrErr.append('No "ulR2" set in the Execute.')
        if __atCert['Execute_Core1']['ulR3'] is None:
            astrErr.append('No "ulR3" set in the Execute.')
        if len(astrErr) != 0:
            raise Exception('\n'.join(astrErr))

        # Combine all data to the chunk.
        atData = array.array('B')

        atData.extend(__atCert['Binding']['mask'])
        atData.extend(__atCert['Binding']['ref'])

        self.__append_32bit(atData, len(__atCert['Data']['data']))
        self.__append_32bit(atData, __atCert['Data']['load_address'])
        atData.extend(array.array('B', __atCert['Data']['data']))

        self.__append_32bit(atData, __atCert['Execute_Core0']['pfnExecFunction'])
        self.__append_32bit(atData, __atCert['Execute_Core0']['ulR0'])
        self.__append_32bit(atData, __atCert['Execute_Core0']['ulR1'])
        self.__append_32bit(atData, __atCert['Execute_Core0']['ulR2'])
        self.__append_32bit(atData, __atCert['Execute_Core0']['ulR3'])
        self.__append_32bit(atData, __atCert['Execute_Core1']['pfnExecFunction'])
        self.__append_32bit(atData, __atCert['Execute_Core1']['ulR0'])
        self.__append_32bit(atData, __atCert['Execute_Core1']['ulR1'])
        self.__append_32bit(atData, __atCert['Execute_Core1']['ulR2'])
        self.__append_32bit(atData, __atCert['Execute_Core1']['ulR3'])

        self.__append_32bit(atData, len(__atCert['UserContent']['data']))
        atData.extend(__atCert['UserContent']['data'])

        # Get the key in DER encoded format.
        strKeyDER = self.__keyrom_get_key(__atCert['Key']['idx'])

        # Create a temporary file for the keypair.
        iFile, strPathKeypair = tempfile.mkstemp(suffix='der', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Create a temporary file for the data to sign.
        iFile, strPathSignatureInputData = tempfile.mkstemp(suffix='bin', prefix='tmp_hboot_image', dir=None, text=False)
        os.close(iFile)

        # Write the DER key to the temporary file.
        tFile = open(strPathKeypair, 'wt')
        tFile.write(strKeyDER)
        tFile.close()

        # Write the data to sign to the temporary file.
        tFile = open(strPathSignatureInputData, 'wb')
        tFile.write(atData.tostring())
        tFile.close()

        strSignature = subprocess.check_output([self.__cfg_openssl, 'dgst', '-sign', strPathKeypair, '-keyform', 'DER', '-sigopt', 'rsa_padding_mode:pss', '-sigopt', 'rsa_pss_saltlen:-1', '-sha384', strPathSignatureInputData])

        # Remove the temp files.
        os.remove(strPathKeypair)
        os.remove(strPathSignatureInputData)

        # Append the signature to the chunk.
        aulSignature = array.array('B', strSignature)
        atData.extend(aulSignature)

        # Pad the data to a multiple of dwords.
        strData = atData.tostring()
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('A', '9', 'S', 'W'))
        aulChunk.append(len(aulData))
        aulChunk.extend(aulData)

        return aulChunk

    def __build_chunk_memory_device_up(self, tChunkNode):
        # Get the device.
        strDevice = tChunkNode.getAttribute('device')

        # Parse the data.
        ulDevice = self.__parse_numeric_expression(strDevice)
        if ulDevice < 0:
            raise Exception('The device attribute does not accept a negative value:' % ulDevice)
        if ulDevice > 0xff:
            raise Exception('The device attribute must not be larger than 0xff:' % ulDevice)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('M', 'D', 'U', 'P'))
        aulChunk.append(1 + self.__sizHashDw)
        aulChunk.append(ulDevice)

        # Get the hash for the chunk.
        tHash = hashlib.sha384()
        tHash.update(aulChunk.tostring())
        strHash = tHash.digest()
        aulHash = array.array('I', strHash[:self.__sizHashDw * 4])
        aulChunk.extend(aulHash)

        return aulChunk

    def set_patch_definitions(self, tInput):
        self.__cPatchDefinitions = PatchDefinitions()
        self.__cPatchDefinitions.read_patch_definition(tInput)

    def parse_image(self, tInput):
        # A string must be the filename of the XML.
        if isinstance(tInput, basestring):
            tXml = xml.dom.minidom.parse(tInput)
            tXmlRootNode = tXml.documentElement
        elif isinstance(tInput, xml.dom.minidom.Node):
            tXmlRootNode = tInput
            # Find the document node.
            tXml = tXmlRootNode
            while tXml.parentNode!=None:
                tXml = tXml.parentNode
        else:
            raise Exception('Unknown input document:', tInput)

        # Preprocess the image.
        self.__preprocess(tXml)

        # Get the type of the image. Default to "REGULAR".
        strType = tXmlRootNode.getAttribute('type')
        if len(strType) != 0:
            if strType not in self.__astrToImageType:
                raise Exception('Invalid image type: "%s"' % strType)
            self.__tImageType = self.__astrToImageType[strType]
        else:
            # Set the default type.
            self.__tImageType = self.__IMAGE_TYPE_REGULAR

        # INTRAM and REGULAR images are DWORD based, SECMEM images are byte
        # based.
        if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
            self.__atChunks = array.array('B')
        else:
            self.__atChunks = array.array('I')

        # Get the hash size. Default to 1 DWORD.
        strHashSize = tXmlRootNode.getAttribute('hashsize')
        if len(strHashSize) != 0:
            uiHashSize = long(strHashSize)
            if (uiHashSize < 1) or (uiHashSize > 12):
                raise Exception('Invalid hash size: %d' % uiHashSize)
            self.__sizHashDw = uiHashSize
        else:
            # Set the default hash size.
            self.__sizHashDw = 1

        # Loop over all children.
        for tImageNode in tXmlRootNode.childNodes:
            # Is this a node element?
            if tImageNode.nodeType == tImageNode.ELEMENT_NODE:
                # Is this a 'Header' node?
                if tImageNode.localName == 'Header':
                    if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                        raise Exception('Header overrides are not allowed in SECMEM images.')
                    self.__parse_header_options(tImageNode)

                elif tImageNode.localName == 'Chunks':
                    # Loop over all nodes, these are the chunks.
                    for tChunkNode in tImageNode.childNodes:
                        if tChunkNode.nodeType == tChunkNode.ELEMENT_NODE:
                            if tChunkNode.localName == 'Options':
                                # Found an option node.
                                atChunk = self.__build_chunk_options(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'Data':
                                # Found a data node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('Data chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_data(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'Execute':
                                # Found an execute node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('Execute chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_execute(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'ExecuteCA9':
                                # Found an execute node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('ExecuteCA9 chunks are not allowed in SECMEM images.')
                                if self.__uiNetxType == 56:
                                    raise Exception('ExecuteCA9 chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_execute_ca9(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'SpiMacro':
                                # Found a SPI macro.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('SpiMacro chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_spi_macro(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'Skip':
                                # Found a skip node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('Skip chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_skip(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'RootCert':
                                # Found a root certificate node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('RootCert chunks are not allowed in SECMEM images.')
                                if self.__uiNetxType == 56:
                                    raise Exception('RootCert chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_root_cert(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'LicenseCert':
                                # Found a license certificate node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('LicenseCert chunks are not allowed in SECMEM images.')
                                if self.__uiNetxType == 56:
                                    raise Exception('LicenseCert chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_license_cert(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'CR7Software':
                                # Found a CR7 software node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('CR7Software chunks are not allowed in SECMEM images.')
                                if self.__uiNetxType == 56:
                                    raise Exception('CR7Software chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_cr7sw(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'CA9Software':
                                # Found a CA9 software node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('CA9Software chunks are not allowed in SECMEM images.')
                                if self.__uiNetxType == 56:
                                    raise Exception('CA9Software chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_ca9sw(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif tChunkNode.localName == 'MemoryDeviceUp':
                                # Found a memory device up node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('MemoryDeviceUp chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_memory_device_up(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            else:
                                raise Exception('Unknown chunk ID: %s', tChunkNode.localName)

    def set_known_files(self, atFiles):
        self.__atKnownFiles.update(atFiles)

    def __crc7(self, strData):
        ucCrc = 0
        for uiByteCnt in range(0, len(strData)):
            ucByte = ord(strData[uiByteCnt])
            for uiBitCnt in range(0, 8):
                ucBit = (ucCrc ^ ucByte) & 0x80
                ucCrc <<= 1
                ucByte <<= 1
                if ucBit != 0:
                    ucCrc ^= 0x07
            ucCrc &= 0xff

        return ucCrc

    def write(self, strTargetPath):
        """ Write all compiled chunks to the file strTargetPath . """

        if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
            # Collect data for zone 2 and 3.
            aucZone2 = None
            aucZone3 = None

            # Get the size of the complete image.
            uiImageSize = self.__atChunks.buffer_info()[1]

            # Up to 29 bytes fit into zone 2.
            if uiImageSize <= 29:
                aucZone2 = array.array('B')
                aucZone3 = array.array('B')

                # Set the length.
                aucZone2.append(uiImageSize)

                # Add the options.
                aucZone2.extend(self.__atChunks)

                # Fill up zone2 to 29 bytes.
                if uiImageSize < 29:
                    aucZone2.extend([0x00] * (29 - uiImageSize))

                # Set the revision.
                aucZone2.append(self.__SECMEM_ZONE2_REV1_0)

                # Set the checksum.
                ucCrc = self.__crc7(aucZone2.tostring())
                aucZone2.append(ucCrc)

                # Clear zone 3.
                aucZone3.extend([0] * 32)

            # Zone 2 and 3 together can hold up to 61 bytes.
            elif uiImageSize <= 61:
                aucTmp = array.array('B')

                # Set the length.
                aucTmp.append(uiImageSize)

                # Add the options.
                aucTmp.extend(self.__atChunks)

                # Fill up the data to 61 bytes.
                if uiImageSize < 61:
                    aucTmp.extend([0x00] * (61 - uiImageSize))

                # Set the revision.
                aucTmp.append(self.__SECMEM_ZONE2_REV1_0)

                # Get the checksum.
                ucCrc = self.__crc7(aucTmp.tostring())

                # Get the first 30 bytes as zone2.
                aucZone2 = aucTmp[0:30]

                # Add the revision.
                aucZone2.append(self.__SECMEM_ZONE2_REV1_0)

                # Add the checksum.
                aucZone2.append(ucCrc)

                # Place the rest of the data into zone3.
                aucZone3 = aucTmp[30:62]

            else:
                raise Exception('The image is too big for a SECMEM. It must be 61 bytes or less, but it has %d bytes.' % uiImageSize)

            # Get a copy of the chunk data.
            atChunks = array.array('B')
            atChunks.extend(aucZone2)
            atChunks.extend(aucZone3)

            # Do not add headers in a SECMEM image.
            atHeader = array.array('B')
        else:
            # Get a copy of the chunk data.
            atChunks = array.array('I', self.__atChunks)

            # Terminate the chunks with a DWORD of 0.
            atChunks.append(0x00000000)

            # Generate the standard header.
            atHeaderStandard = self.__build_standard_header(atChunks)

            # Combine the standard header with the overrides.
            atHeader = self.__combine_headers(atHeaderStandard)

        # Write all components to the output file.
        tFile = open(strTargetPath, 'wb')

        atHeader.tofile(tFile)
        atChunks.tofile(tFile)
        tFile.close()


def main():
    tParser = argparse.ArgumentParser(usage='usage: hboot_image [options]')
    tParser.add_argument('-n', '--netx-type',
                         dest='uiNetxType',
                         required=True,
                         choices=[56, 4000],
                         metavar='NETX',
                         help='Build the image for netx type NETX.')
    tParser.add_argument('-c', '--objcopy',
                         dest='strObjCopy',
                         required=False,
                         default='objcopy',
                         metavar='FILE',
                         help='Use FILE as the objcopy tool.')
    tParser.add_argument('-d', '--objdump',
                         dest='strObjDump',
                         required=False,
                         default='objdump',
                         metavar='FILE',
                         help='Use FILE as the objdump tool.')
    tParser.add_argument('-k', '--keyrom',
                         dest='strKeyRomPath',
                         required=False,
                         default=None,
                         metavar='FILE',
                         help='Read the keyrom data from FILE.')
    tParser.add_argument('-p', '--patch-table',
                         dest='strPatchTablePath',
                         required=False,
                         default=None,
                         metavar='FILE',
                         help='Read the patch table from FILE.')
    tParser.add_argument('-r', '--readelf',
                         dest='strReadElf',
                         required=False,
                         default='readelf',
                         metavar='FILE',
                         help='Use FILE as the readelf tool.')
    tParser.add_argument('-v', '--verbose',
                         dest='fVerbose',
                         required=False,
                         default=False,
                         action='store_const', const=True,
                         help='Be more verbose.')
    tParser.add_argument('-A', '--alias',
                         dest='astrAliases',
                         required=False,
                         action='append',
                         metavar='ALIAS=FILE',
                         help='Add an alias in the form ALIAS=FILE.')
    tParser.add_argument('-I', '--include',
                         dest='astrIncludePaths',
                         required=False,
                         action='append',
                         metavar='PATH',
                         help='Add PATH to the list of include paths.')
    tParser.add_argument('strInputFile',
                         metavar='FILE',
                         help='Read the HBoot definition from FILE.')
    tParser.add_argument('strOutputFile',
                         metavar='FILE',
                         help='Write the HBoot image to FILE.')
    tArgs = tParser.parse_args()

    # Set the default for the patch table here.
    atDefaultPatchTables = {
        56: 'hboot_netx56_patch_table.xml',
        4000: 'hboot_netx4000_patch_table.xml'
    }
    if tArgs.strPatchTablePath is None:
        tArgs.strPatchTablePath = atDefaultPatchTables[tArgs.uiNetxType]

    # Parse all alias definitions.
    atKnownFiles = {}
    if tArgs.astrAliases is not None:
        tPattern = re.compile('([a-zA-Z0-9_]+)=(.+)$')
        for strAliasDefinition in tArgs.astrAliases:
            tMatch = re.match(tPattern, strAliasDefinition)
            if tMatch is None:
                raise Exception('Invalid alias definition: "%s". It must be "ALIAS=FILE" instead.' % strAliasDefinition)
            strAlias = tMatch.group(1)
            strFile = tMatch.group(2)
            if strAlias in atKnownFiles:
                raise Exception('Double defined alias "%s". The old value "%s" should be overwritten with "%s".' % (strAlias, atKnownFiles[strAlias], strFile))
            atKnownFiles[strAlias] = strFile

    # Set an empty list of include paths if nothing was specified.
    if tArgs.astrIncludePaths is None:
        tArgs.astrIncludePaths = []

    tEnv = {'OBJCOPY': tArgs.strObjCopy,
            'OBJDUMP': tArgs.strObjDump,
            'READELF': tArgs.strReadElf,
            'HBOOT_INCLUDE': tArgs.astrIncludePaths}

    # Show all parameters.
    if tArgs.fVerbose:
        print 'netX type:   %d' % tArgs.uiNetxType
        print ''
        print 'Input file:  %s' % tArgs.strInputFile
        print 'Output file: %s' % tArgs.strOutputFile
        print ''
        print 'Patch table: %s' % tArgs.strPatchTablePath
        print ''
        print 'OBJCOPY: %s' % tArgs.strObjCopy
        print 'OBJDUMP: %s' % tArgs.strObjDump
        print 'READELF: %s' % tArgs.strReadElf

        if len(tArgs.astrIncludePaths) == 0:
            print 'No include paths.'
        else:
            print 'Include paths:'
            for strPath in tArgs.astrIncludePaths:
                print '\t%s' % strPath

        if len(atKnownFiles) == 0:
            print 'No alias definitions.'
        else:
            print 'Alias definitions:'
            for strAlias, strFile in atKnownFiles.iteritems():
                print '\t%s = %s' % (strAlias, strFile)

    tCompiler = HbootImage(tEnv, tArgs.uiNetxType, tArgs.strKeyRomPath)
    tCompiler.set_patch_definitions(tArgs.strPatchTablePath)
    tCompiler.set_known_files(atKnownFiles)
    tCompiler.parse_image(tArgs.strInputFile)
    tCompiler.write(tArgs.strOutputFile)

# Call the main routine if this script is started standalone.
if __name__ == '__main__':
    main()
