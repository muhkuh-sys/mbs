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
import string
import xml.dom.minidom
import os

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
            if(
                tTextNode.nodeType == tDataNode.TEXT_NODE or
                tTextNode.nodeType == tDataNode.CDATA_SECTION_NODE
            ):
                atText.append(tTextNode.data)
        # Join all text chunks.
        strText = ''.join(atText)
        # Split the text by comma.
        atTextElements = strText.split(',')

        # Process all data elements.
        atData = []
        for strElementRaw in atTextElements:
            strElement = strElementRaw.strip()

            # Parse the data.
            ulValue = self.__parse_numeric_expression(strElement)

            # Generate the data entry.
            atBytes = [
                chr((ulValue >> (iCnt << 3)) & 0xff)
                for iCnt in range(0, uiElementSizeInBytes)
            ]
            atData.append(''.join(atBytes))
        return ''.join(atData)

    # NOTE: This function is also used from outside for SpiMacro parsing.
    def get_spi_macro_data(self, tDataNode):
        # Collect all text nodes and CDATA sections.
        atText = []
        # Loop over all children.
        for tTextNode in tDataNode.childNodes:
            # Is this a node element with the name 'Options'?
            if(
                tTextNode.nodeType == tTextNode.TEXT_NODE or
                tTextNode.nodeType == tTextNode.CDATA_SECTION_NODE
            ):
                atText.append(tTextNode.data)
        # Join all text chunks.
        strText = ''.join(atText)

        # Split the text by newlines.
        atLines = strText.split('\n')
        # Split the lines by comma.
        atRawElements = []
        for strLine in atLines:
            atRawElements.extend(strLine.split(','))

        # Loop over all lines.
        ulAddress = 0
        atLabels = dict({})
        atElements = []
        for strRawElement in atRawElements:
            # Remove empty lines and comments.
            strElement = strRawElement.strip()
            if (len(strElement) > 0) and (strElement[0] != '#'):
                # Does the element contain a colon?
                atTmp = strElement.split(':')
                if len(atTmp) == 1:
                    # The line does not contain a colon.
                    # This counts as one byte.
                    ulAddress += 1
                    atElements.append(atTmp[0])
                elif len(atTmp) != 2:
                    raise Exception('The line contains more than one colon!')
                else:
                    if len(atTmp[0]) == 0:
                        raise Exception(
                            'The line contains no data before the colon!'
                        )

                    # The line contains a label definition.
                    strLabelName = atTmp[0]
                    if strLabelName in atLabels:
                        raise Exception('Label double defined: %s' %
                                        strLabelName)
                    atLabels[strLabelName] = ulAddress

                    if len(atTmp[1]) != 0:
                        # The line contains also data.
                        ulAddress += 1
                        atElements.append(atTmp[0].strip())

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
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ucRegister = eval(compile(
                        tAstResolved,
                        'lala',
                        mode='eval'
                    ))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception(
                            'Invalid register for WritePhy: 0x%02x' %
                            ucRegister
                        )
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' %
                                        ulData)

                    # Append the new element.
                    atDdrMacro.append(chr(
                        self.__cPatchDefinitions.m_atConstants[
                            'DDR_SETUP_COMMAND_WritePhy'
                        ]
                    ))
                    atDdrMacro.append(chr(ucRegister))
                    atDdrMacro.append(chr(ulData & 0xff))
                    atDdrMacro.append(chr((ulData >> 8) & 0xff))
                    atDdrMacro.append(chr((ulData >> 16) & 0xff))
                    atDdrMacro.append(chr((ulData >> 24) & 0xff))

                elif tNode.localName == 'WriteCtrl':
                    strValue = tNode.getAttribute('register')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ucRegister = eval(compile(
                        tAstResolved,
                        'lala',
                        mode='eval'
                    ))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception(
                            'Invalid register for WritePhy: 0x%02x' %
                            ucRegister
                        )
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' %
                                        ulData)

                    # Append the new element.
                    atDdrMacro.append(chr(
                        self.__cPatchDefinitions.m_atConstants[
                            'DDR_SETUP_COMMAND_WriteCtrl'
                        ]
                    ))
                    atDdrMacro.append(chr(ucRegister))
                    atDdrMacro.append(chr(ulData & 0xff))
                    atDdrMacro.append(chr((ulData >> 8) & 0xff))
                    atDdrMacro.append(chr((ulData >> 16) & 0xff))
                    atDdrMacro.append(chr((ulData >> 24) & 0xff))

                elif tNode.localName == 'Delay':
                    strValue = tNode.getAttribute('ticks')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulTicks = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ulTicks < 0) or (ulTicks > 0xffffffff):
                        raise Exception('Invalid value for Delay: 0x%08x' %
                                        ulTicks)

                    # Append the new element.
                    atDdrMacro.append(chr(
                        self.__cPatchDefinitions.m_atConstants[
                            'DDR_SETUP_COMMAND_DelayTicks'
                        ]
                    ))
                    atDdrMacro.append(chr(ulTicks & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 8) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 16) & 0xff))
                    atDdrMacro.append(chr((ulTicks >> 24) & 0xff))

                elif tNode.localName == 'PollPhy':
                    strValue = tNode.getAttribute('register')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ucRegister = eval(compile(
                        tAstResolved,
                        'lala',
                        mode='eval'
                    ))

                    strValue = tNode.getAttribute('mask')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulMask = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('ticks')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulTicks = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception(
                            'Invalid register for WritePhy: 0x%02x' %
                            ucRegister
                        )
                    if (ulMask < 0) or (ulMask > 0xffffffff):
                        raise Exception('Invalid mask for WritePhy: 0x%08x' %
                                        ulMask)
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' %
                                        ulData)
                    if (ulTicks < 0) or (ulTicks > 0xffffffff):
                        raise Exception('Invalid value for Delay: 0x%08x' %
                                        ulTicks)

                    # Append the new element.
                    atDdrMacro.append(chr(
                        self.__cPatchDefinitions.m_atConstants[
                            'DDR_SETUP_COMMAND_PollPhy'
                        ]
                    ))
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
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ucRegister = eval(compile(
                        tAstResolved,
                        'lala',
                        mode='eval'
                    ))

                    strValue = tNode.getAttribute('mask')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulMask = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('data')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulData = eval(compile(tAstResolved, 'lala', mode='eval'))

                    strValue = tNode.getAttribute('ticks')
                    tAstNode = ast.parse(strValue, mode='eval')
                    tAstResolved = self.__cPatchDefinitions.resolve_constants(
                        tAstNode
                    )
                    ulTicks = eval(compile(tAstResolved, 'lala', mode='eval'))

                    if (ucRegister < 0) or (ucRegister > 0xff):
                        raise Exception(
                            'Invalid register for WritePhy: 0x%02x' %
                            ucRegister
                        )
                    if (ulMask < 0) or (ulMask > 0xffffffff):
                        raise Exception('Invalid mask for WritePhy: 0x%08x' %
                                        ulMask)
                    if (ulData < 0) or (ulData > 0xffffffff):
                        raise Exception('Invalid data for WritePhy: 0x%08x' %
                                        ulData)
                    if (ulTicks < 0) or (ulTicks > 0xffffffff):
                        raise Exception('Invalid value for Delay: 0x%08x' %
                                        ulTicks)

                    # Append the new element.
                    atDdrMacro.append(chr(
                        self.__cPatchDefinitions.m_atConstants[
                            'DDR_SETUP_COMMAND_PollCtrl'
                        ]
                    ))
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
                    raise Exception('Unknown child node: %s' %
                                    tNode.localName)

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
                elif tDataNode.localName == 'File':
                    strFileName = tDataNode.getAttribute('name')
                    if len(strFileName) == 0:
                        raise Exception(
                            "The file node has no name attribute!"
                        )

                    strAbsFilePath = None
                    if os.access(strFileName, os.R_OK) is True:
                        strAbsFilePath = os.path.abspath(strFileName)

                    if strAbsFilePath is None:
                        raise Exception('File %s not found!' % strFileName)

                    tBinFile = open(strAbsFilePath, 'rb')
                    strData = tBinFile.read()
                    tBinFile.close()
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

                        # To make things easier this routine expects only
                        # one element.
                        if len(atData) != 1:
                            raise Exception(
                                'A RAW element must have only one child '
                                'element. This is just a limitation of the '
                                'parser, so improve it if you really need '
                                'it.'
                            )

                        # A raw option entry contains 4 bytes header and 
                        # up to 255 bytes data.
                        # If the data is longer than 255 bytes, we split it 
                        # into multiple raw entries.
                        # The max. size of the data chunk is 2048 bytes.
                        # The max. size of the payload data is 2048-8*4 bytes.
                        iMaxSize = 2048-8*4
                        strData = atData[0]
                        iOffset = 0
                        sizData = len(strData)

                        if sizData > iMaxSize:
                            raise Exception('The RAW option must not contain more than %d bytes.' % (iMaxSize))
                            
                        while sizData>0:
                            # Get a chunk of data
                            sizChunk = min(255, sizData)
                            strChunk=strData[iOffset:iOffset+sizChunk] 
                            
                            # Write it as a raw option
                            ucOptionIdRaw = 0xfe
                            atOptionData.append(chr(ucOptionIdRaw))
                            atOptionData.append(chr(sizChunk))
                            atOptionData.append(chr(ulOffset & 0xff))
                            atOptionData.append(chr((ulOffset >> 8) & 0xff))
                            atOptionData.extend(strChunk)

                            iOffset+=sizChunk
                            sizData-=sizChunk
                            ulOffset+=sizChunk

                    else:
                        atOptionDesc = (
                            self.__cPatchDefinitions.get_patch_definition(
                                strOptionId
                            )
                        )
                        ulOptionValue = atOptionDesc['value']
                        atElements = atOptionDesc['elements']

                        # Get all data elements.
                        atData = self.__getOptionData(tOptionNode)

                        # Compare the data elements with the element sizes.
                        sizElements = len(atElements)
                        if len(atData) != sizElements:
                            raise Exception(
                                'The number of data elements for the option '
                                '%s differs. The model requires %d, but %d '
                                'were found.' % (
                                    strOptionId,
                                    sizElements,
                                    len(atData)
                                )
                            )

                        atOptionData.append(chr(ulOptionValue))

                        # Compare the size of all elements.
                        for iCnt in range(0, sizElements):
                            sizElement = len(atData[iCnt])
                            (strElementId, ulSize, ulType) = atElements[iCnt]
                            if ulType == 0:
                                if sizElement != ulSize:
                                    raise Exception(
                                        'The length of the data element %s '
                                        'for the option %s differs. The '
                                        'model requires %d bytes, but %d '
                                        'were found.' % (
                                            strElementId,
                                            strOptionId,
                                            ulSize,
                                            sizElement
                                        )
                                    )
                            elif ulType == 1:
                                if sizElement >= ulSize:
                                    raise Exception(
                                        'The length of the data element %s '
                                        'for the option %s exceeds the '
                                        'available space. The model reserves '
                                        '%d bytes, which must include a '
                                        'length information, but %d were '
                                        'found.' % (
                                            strElementId,
                                            strOptionId,
                                            ulSize,
                                            sizElement
                                        )
                                    )
                            elif ulType == 2:
                                if sizElement > ulSize:
                                    raise Exception(
                                        'The length of the data element %s '
                                        'for the option %s exceeds the '
                                        'available space. The model reserves '
                                        '%d bytes, but %d were '
                                        'found.' % (
                                            strElementId,
                                            strOptionId,
                                            ulSize,
                                            sizElement
                                        )
                                    )
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
                                atOptionData.append(chr(
                                    (sizElement >> 8) & 0xff
                                ))
                                atOptionData.extend(atData[iCnt])
                            else:
                                raise Exception('Unknown Type %d' % ulType)
                else:
                    raise Exception('Unexpected node: %s' %
                                    tOptionNode.localName)

        return ''.join(atOptionData)

    def process(self, tSource):
        # Clear the output data.
        self.__strOptions = ''

        if not isinstance(tSource, xml.dom.minidom.Node):
            raise Exception('The input must be of the type '
                            'xml.dom.minidom.Node, but it is not!')

        self.__strOptions = self.__processChunkOptions(tSource)

    def tostring(self):
        """ Return the compiled options as a string. """
        return self.__strOptions

    def write(self, strTargetPath):
        """ Write all compiled options to the file strTargetPath . """
        tFile = open(strTargetPath, 'wb')

        tFile.write(self.tostring())
        tFile.close()
