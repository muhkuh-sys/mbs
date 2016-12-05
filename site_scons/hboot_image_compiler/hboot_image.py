# -*- coding: utf-8 -*-

import array
import ast
import base64
import binascii
import hashlib
import math
import os
import os.path
import re
import string
import subprocess
import tempfile
import xml.dom.minidom

import elf_support
import option_compiler
import patch_definitions
import snippet_library


class ResolveDefines(ast.NodeTransformer):
    __atDefines = None

    def setDefines(self, atDefines):
        self.__atDefines = atDefines

    def visit_Name(self, node):
        tNode = None
        strName = node.id
        if strName in self.__atDefines:
            tValue = self.__atDefines[strName]
            # Check for a set of base types.
            tValueNode = None
            if type(tValue) is int:
                tValueNode = ast.Num(n=tValue)
            elif type(tValue) is long:
                tValueNode = ast.Num(n=tValue)
            elif type(tValue) is str:
                tValueNode = ast.Str(s=tValue)
            else:
                raise Exception('Not implemented type for "%s": %s' % (strName, str(type(tValue))))
            tNode = ast.copy_location(tValueNode, node)
        else:
            raise Exception('Unknown constant "%s".' % node.id)
        return tNode


class HbootImage:
    __fVerbose = False

    # This is the list of override items for the header.
    __atHeaderOverride = None

    # This is a list with all chunks.
    __atChunks = None

    # This is the environment.
    __tEnv = None

    # This is a list of all include paths.
    __astrIncludePaths = None

    # This is a dictionary of all resolved files.
    __atKnownFiles = None

    # This is a dictionary of key/value pairs to do replacements with.
    __atGlobalDefines = None

    __cPatchDefinitions = None

    __cSnippetLibrary = None

    __astrDependencies = None

    __strNetxType = None
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
    __MAGIC_COOKIE_NETX90_MPW = 0xf3beaf00

    __resolver = None

    __ulStartOffset = 0

    __strDevice = None

    def __init__(self, tEnv, strNetxType, **kwargs):
        strPatchDefinition = None
        strKeyromFile = None
        astrIncludePaths = []
        astrSnippetSearchPaths = None
        atKnownFiles = {}
        atGlobalDefines = {}
        fVerbose = False

        # Parse the kwargs.
        for strKey, tValue in kwargs.iteritems():
            if strKey == 'patch_definition':
                strPatchDefinition = tValue

            elif strKey == 'keyrom':
                strKeyromFile = tValue

            elif strKey == 'sniplibs':
                astrSnippetSearchPaths = []
                if tValue is None:
                    pass
                elif isinstance(tValue, basestring):
                    astrSnippetSearchPaths.append(tValue)
                else:
                    astrSnippetSearchPaths.extend(tValue)

            elif strKey == 'includes':
                if tValue is None:
                    pass
                elif isinstance(tValue, basestring):
                    astrIncludePaths.append(tValue)
                else:
                    astrIncludePaths.extend(tValue)

            elif strKey == 'known_files':
                if tValue is None:
                    pass
                else:
                    atKnownFiles.update(tValue)

            elif strKey == 'verbose':
                fVerbose = bool(tValue)

            elif strKey == 'defines':
                atGlobalDefines = dict(tValue)

        # Set the default search path if nothing was specified.
        if astrSnippetSearchPaths is None:
            astrSnippetSearchPaths = ['sniplib']

        self.__fVerbose = fVerbose

        # Do not override anything in the pre-calculated header yet.
        self.__atHeaderOverride = [None] * 16

        # No chunks yet.
        self.__atChunks = None

        # Set the environment.
        self.__tEnv = tEnv

        # Set the known files.
        self.__atKnownFiles = atKnownFiles

        # Set the defines.
        self.__atGlobalDefines = atGlobalDefines

        if self.__fVerbose:
            print '[HBootImage] Configuration: netX type = %s' % strNetxType
            print '[HBootImage] Configuration: patch definitions = "%s"' % strPatchDefinition
            print '[HBootImage] Configuration: Keyrom = "%s"' % str(strKeyromFile)

            if len(astrSnippetSearchPaths) == 0:
                print '[HBootImage] Configuration: No Sniplibs.'
            else:
                for strPath in astrSnippetSearchPaths:
                    print '[HBootImage] Configuration: Sniplib at "%s"' % strPath

            if len(astrIncludePaths) == 0:
                print '[HBootImage] Configuration: No include paths.'
            else:
                for strPath in astrIncludePaths:
                    print '[HBootImage] Configuration: Include path "%s"' % strPath

            if len(atKnownFiles) == 0:
                print '[HBootImage] Configuration: No known files.'
            else:
                for strKey, strPath in atKnownFiles.iteritems():
                    print '[HBootImage] Configuration: Known file "%s" at "%s".' % (strKey, strPath)

        if strPatchDefinition is not None:
            self.__cPatchDefinitions = patch_definitions.PatchDefinitions()
            self.__cPatchDefinitions.read_patch_definition(strPatchDefinition)

        self.__cSnippetLibrary = snippet_library.SnippetLibrary('.sniplib.dblite', astrSnippetSearchPaths, debug=self.__fVerbose)

        self.__strNetxType = strNetxType
        self.__tImageType = None
        self.__sizHashDw = None

        self.__astrToImageType = dict({
            'REGULAR': self.__IMAGE_TYPE_REGULAR,
            'INTRAM': self.__IMAGE_TYPE_INTRAM,
            'SECMEM': self.__IMAGE_TYPE_SECMEM
        })

        # Initialize the include paths from the environment.
        self.__astrIncludePaths = astrIncludePaths

        # Read the keyrom file if specified.
        if strKeyromFile is not None:
            if self.__fVerbose:
                print '[HBootImage] Init: Reading key ROM file "%s".' % strKeyromFile
            # Parse the XML file.
            print repr(strKeyromFile)
            tFile = open(strKeyromFile, 'rt')
            strXml = tFile.read()
            tFile.close()
            self.__XmlKeyromContents = xml.etree.ElementTree.fromstring(strXml)

        self.__resolver = ResolveDefines()

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

    def __parse_re_match(self, tMatch):
        strExpression = tMatch.group(1)
        tAstNode = ast.parse(strExpression, mode='eval')
        tAstResolved = self.__resolver.visit(tAstNode)
        tResult = eval(compile(tAstResolved, 'lala', mode='eval'))
        if tResult is None:
            raise Exception('Invalid expression: "%s"' % strExpression)
        return tResult

    def __plaintext_to_xml_with_replace(self, strPlaintext, atReplace, fIsStandalone):
        # Set all key/value pairs in the local resolver.
        self.__resolver.setDefines(atReplace)

        # Replace all parameter in the snippet.
        strText = re.sub('%%(.+?)%%', self.__parse_re_match, strPlaintext)

        # Parse the text as XML.
        tResult = None
        if fIsStandalone is True:
            tXml = xml.dom.minidom.parseString(strText)
            tResult = tXml
        else:
            tXml = xml.dom.minidom.parseString('<?xml version="1.0" encoding="utf-8"?><Root>%s</Root>' % strText)
            tResult = tXml.documentElement
        return tResult

    def __preprocess_snip(self, tSnipNode):
        # Get the group, artifact and optional revision.
        strGroup = tSnipNode.getAttribute('group')
        if len(strGroup) == 0:
            raise Exception('The "group" attribute of a "Snip" node must not be empty.')
        strArtifact = tSnipNode.getAttribute('artifact')
        if len(strArtifact) == 0:
            raise Exception('The "artifact" attribute of a "Snip" node must not be empty.')
        strVersion = tSnipNode.getAttribute('version')
        if len(strVersion) == 0:
            raise Exception('The "version" attribute of a "Snip" node must not be empty.')

        # Get the name of the snippets for messages.
        strSnipName = 'G="%s",A="%s",V="%s"' % (strGroup, strArtifact, strVersion)

        # Get the parameter.
        atParameter = {}
        for tChildNode in tSnipNode.childNodes:
            if tChildNode.nodeType == tChildNode.ELEMENT_NODE:
                strTag = tChildNode.localName
                if strTag == 'Parameter':
                    # Get the "name" attribute.
                    strName = tChildNode.getAttribute('name')
                    if len(strName) == 0:
                        raise Exception('Snippet %s instanciation failed: a parameter node is missing the "name" attribute!' % strSnipName)
                    # Get the value.
                    strValue = self.__xml_get_all_text(tChildNode)
                    # Was the parameter already defined?
                    if strName in atParameter:
                        raise Exception('Snippet %s instanciation failed: parameter "%s" is defined more than once!' % (strSnipName, strName))
                    else:
                        atParameter[strName] = strValue
                else:
                    raise Exception('Snippet %s instanciation failed: unknown tag "%s" found!' % (strSnipName, strTag))

        # Search the snippet.
        tSnippetAttr = self.__cSnippetLibrary.find(strGroup, strArtifact, strVersion, atParameter)
        strSnippetText = tSnippetAttr[0]
        if strSnippetText is None:
            raise Exception('Snippet not found!')

        # Get the list of key/value pairs for the replacement.
        atReplace = {}
        atReplace.update(self.__atGlobalDefines)
        atReplace.update(tSnippetAttr[1])

        # Replace and convert to XML.
        tSnippetNode = self.__plaintext_to_xml_with_replace(strSnippetText, atReplace, False)

        # Add the snippet file to the dependencies.
        strSnippetAbsFile = tSnippetAttr[2]
        if strSnippetAbsFile not in self.__astrDependencies:
            self.__astrDependencies.append(strSnippetAbsFile)

        # Get the parent node of the "Snip" node.
        tParentNode = tSnipNode.parentNode

        # Replace the "Snip" node with the snippet contents.
        for tNode in tSnippetNode.childNodes:
            tClonedNode = tNode.cloneNode(True)
            tParentNode.insertBefore(tClonedNode, tSnipNode)

        # Remove the old "Snip" node.
        tParentNode.removeChild(tSnipNode)

    def __preprocess_include(self, tIncludeNode):
        # Get the name.
        strIncludeName = tIncludeNode.getAttribute('name')
        if strIncludeName is None:
            raise Exception('The "Include" node has no "name" attribute.')
        if len(strIncludeName) == 0:
            raise Exception('The "name" attribute of an "Include" node must not be empty.')

        # Get the parameter.
        atParameter = {}
        for tChildNode in tIncludeNode.childNodes:
            if tChildNode.nodeType == tChildNode.ELEMENT_NODE:
                strTag = tChildNode.localName
                if strTag == 'Parameter':
                    # Get the "name" attribute.
                    strName = tChildNode.getAttribute('name')
                    if len(strName) == 0:
                        raise Exception('Include failed: a parameter node is missing the "name" attribute!')
                    # Get the value.
                    strValue = self.__xml_get_all_text(tChildNode)
                    # Was the parameter already defined?
                    if strName in atParameter:
                        raise Exception('Include failed: parameter "%s" is defined more than once!' % strIncludeName)
                    else:
                        atParameter[strName] = strValue
                else:
                    raise Exception('Include failed: unknown tag "%s" found!' % strTag)

        # Search the file in the current path and all include paths.
        strAbsIncludeName = self.__find_file(strIncludeName)
        if strAbsIncludeName is None:
            raise Exception('Failed to include file "%s": file not found.' % strIncludeName)

        # Read the complete file as text.
        tFile = open(strAbsIncludeName, 'rt')
        strFileContents = tFile.read()
        tFile.close()

        # Replace and convert to XML.
        atReplace = {}
        atReplace.update(self.__atGlobalDefines)
        atReplace.update(atParameter)
        tNewNode = self.__plaintext_to_xml_with_replace(strFileContents, atReplace, False)

        # Add the include file to the dependencies.
        if strAbsIncludeName not in self.__astrDependencies:
            self.__astrDependencies.append(strAbsIncludeName)

        # Get the parent node of the "Include" node.
        tParentNode = tIncludeNode.parentNode

        # Replace the "Include" node with the include file contents.
        for tNode in tNewNode.childNodes:
            tClonedNode = tNode.cloneNode(True)
            tParentNode.insertBefore(tClonedNode, tIncludeNode)

        # Remove the old "Include" node.
        tParentNode.removeChild(tIncludeNode)

    def __preprocess(self, tXmlDocument):
        if self.__strNetxType == 'NETX90_MPW':
            # The netX90 MPW does not have a 'StartAPP' function yet.
            # Replace it with a snippet.
            atNodes = tXmlDocument.getElementsByTagName('StartAPP')
            for tReplaceNode in atNodes:
                strNewText = '<Snip artifact="start_app_cpu_netx90_mpw" group="org.muhkuh.hboot.sniplib" version="1.0.0"/>'
                tNewXml = xml.dom.minidom.parseString('<?xml version="1.0" encoding="utf-8"?><Root>%s</Root>' % strNewText)
		tParentNode = tReplaceNode.parentNode
                for tChildNode in tNewXml.documentElement.childNodes:
                    tClonedNode = tChildNode.cloneNode(True)
                    tParentNode.insertBefore(tClonedNode, tReplaceNode)
                # Remove the old "StartAPP" node.
                tParentNode.removeChild(tReplaceNode)

        # Look for all 'Snip' nodes repeatedly until the maximum count is
        # reached or no more 'Snip' nodes are found.
        uiMaximumDepth = 100
        uiDepth = 0
        fFoundPreproc = True
        while fFoundPreproc is True:
            atSnipNodes = tXmlDocument.getElementsByTagName('Snip')
            atIncludeNodes = tXmlDocument.getElementsByTagName('Include')
            if (len(atSnipNodes) == 0) and (len(atIncludeNodes) == 0):
                fFoundPreproc = False
            elif uiDepth >= uiMaximumDepth:
                raise Exception('Too many nested preprocessor directives found! The maximum nesting depth is %d.' % uiMaximumDepth)
            else:
                uiDepth += 1
                for tNode in atSnipNodes:
                    self.__preprocess_snip(tNode)
                for tNode in atIncludeNodes:
                    self.__preprocess_include(tNode)

    def __build_standard_header(self, atChunks):

        ulMagicCookie = None
        if self.__strNetxType == 'NETX56':
            ulMagicCookie = self.__MAGIC_COOKIE_NETX56
        elif self.__strNetxType == 'NETX4000_RELAXED':
            ulMagicCookie = self.__MAGIC_COOKIE_NETX4000
	elif self.__strNetxType == 'NETX90_MPW':
	    ulMagicCookie = self.__MAGIC_COOKIE_NETX90_MPW
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
                strAbsFilePath = self.__atKnownFiles[strFileId]
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
                    raise Exception('Unexpected node: %s' % tValueNode.localName)

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
        tOptionCompiler = option_compiler.OptionCompiler(self.__cPatchDefinitions)
        tOptionCompiler.process(tChunkNode)
        strData = tOptionCompiler.tostring()

        # Return the plain option chunk for SECMEM images.
        # Add a header otherwise.
        if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
            atChunk = array.array('B')
            atChunk.fromstring(strData)
        else:
            if self.__strNetxType == 'NETX56':
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

            elif self.__strNetxType == 'NETX4000_RELAXED':
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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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

    def __build_chunk_xip(self, tChunkNode):
        # Get the data block.
        atData = {}
        self.__get_data_contents(tChunkNode, atData)
        strData = atData['data']
        pulLoadAddress = atData['load_address']

        # Get the available XIP areas for the current platform.
        atXIPAreas = None
        if self.__strNetxType == 'NETX56':
            raise Exception('Continue here!')
	elif self.__strNetxType == 'NETX4000_RELAXED':
            raise Exception('Continue here!')
        elif self.__strNetxType == 'NETX90_MPW':
            atXIPAreas = [
                { 'device':'SQIROM',   'start':0x64000000, 'end':0x68000000 },   # SQI flash
                { 'device':'INTFLASH', 'start':0x00100000, 'end':0x00200000 }    # IFLASH0 and 1
            ]

        pulXipStartAddress = None
        for tXipArea in atXIPAreas:
            if (pulLoadAddress >= tXipArea['start']) and (pulLoadAddress < tXipArea['end']):
                if tXipArea['device'] != self.__strDevice:
                    raise Exception('The XIP load address matches the %s device, but the image specifies %s' % (tXipArea['device'], self.__strDevice))
                pulXipStartAddress = tXipArea['start']
                break
        if pulXipStartAddress is None:
            raise Exception('The load address 0x%08x of the XIP block is outside the available XIP regions of the platform.' % pulLoadAddress)

        # Get the requested offset of the data in the XIP area.
        ulOffsetRequested = pulLoadAddress - pulXipStartAddress

        # The requested offset must be the current offset + 8 (4 for the ID and 4 for the length).
        ulOffsetRequestedData = 8

        # Get the current offset in bytes.
        # It is 64 bytes for the header and the size of all chunks.
        # FIXME: If an image starts not at the beginning of the flash, the offset is different. Get the offset from the XML file?
        ulOffsetCurrent = 64 + (len(self.__atChunks) * 4)

        # The requested offset must be the current offset + the data offset
        ulOffsetCurrentData = ulOffsetCurrent + ulOffsetRequestedData
        if ulOffsetRequested != ulOffsetCurrentData:
            raise Exception('The current offset 0x%08x does not match the requested offset 0x%08x of the XIP data.' % (ulOffsetCurrentData, ulOffsetRequested))

        # The load address must be exactly the address where the code starts.
        # Pad the application size to a multiple of DWORDs.
        strPadding = chr(0x00) * ((4 - (len(strData) % 4)) & 3)
        strChunk = strData + strPadding

        # Convert the padded data to an array.
        aulData = array.array('I')
        aulData.fromstring(strChunk)

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('T', 'E', 'X', 'T'))
        aulChunk.append(len(aulData) + self.__sizHashDw)
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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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
                    raise Exception('Unexpected node: %s' % tCoreNode.localName)

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

        tOptionCompiler = option_compiler.OptionCompiler(self.__cPatchDefinitions)
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
        sizSkipParameter = 0

        if (sizAbsolute == 0) and (sizRelative == 0):
            raise Exception('The skip node has no "absolute" or "relative" attribute!')
        elif (sizAbsolute != 0) and (sizRelative != 0):
            raise Exception('The skip node has an "absolute" and a "relative" attribute!')
        elif sizAbsolute != 0:
            # Get the new absolute offset in bytes.
            sizOffsetNew = self.__parse_numeric_expression(strAbsolute) * 4
            # Get the current offset in bytes. Add the size of the ID, the length and the hash.
            sizOffsetCurrent = 64 + (len(self.__atChunks) * 4)
            # Add the size of the SKIP chunk itself to the current position.
            if self.__strNetxType == 'NETX4000_RELAXED':
                sizOffsetCurrent += (1 + 1 + self.__sizHashDw) * 4
            elif self.__strNetxType == 'NETX90_MPW':
                sizOffsetCurrent += (1 + 1 + self.__sizHashDw) * 4
            else:
		raise Exception('Continue here!')

            if sizOffsetNew < sizOffsetCurrent:
                raise Exception('Skip tries to set the offset back from %d to %d.' % (sizOffsetCurrent, sizOffsetNew))

            if self.__strNetxType == 'NETX90_MPW':
                # The netX90 MPW ROM has a bug in the ROM code.
                # The SKIP chunk for SQI flash forwards the offset by the
                # argument - 1.
		if self.__strDevice == 'SQIROM':
                    sizSkip = (sizOffsetNew - sizOffsetCurrent) / 4
                    sizSkipParameter = sizOffsetNew - sizOffsetCurrent + 1 - self.__sizHashDw
                else:
                    sizSkip = (sizOffsetNew - sizOffsetCurrent) / 4
                    sizSkipParameter = sizSkip

	    elif self.__strNetxType == 'NETX4000_RELAXED':
		# The netX4000 relaxed ROM has a bug in the ROM code.
		# The SKIP chunk forwards the offset by the argument - 1.

                # The netX4000 has a lot of XIP areas including SQIROM, SRAM
		# and NAND. Fortunately booting from parallel NOR flash and
		# NAND is unusual. The NAND booter has no ECC support and the
		# parallel NOR flashes are quite unusual in the netX4000 area.
		# That's why we can safely default to SQIROM here and ignore
        	# the rest.
		sizSkip = (sizOffsetNew - sizOffsetCurrent) / 4
		sizSkipParameter = sizOffsetNew - sizOffsetCurrent + 1 - self.__sizHashDw

            else:
                sizSkip = (sizOffsetNew - sizOffsetCurrent) / 4
                sizSkipParameter = sizSkip
        else:
            # Parse the data.
            sizSkip = self.__parse_numeric_expression(strRelative)
            if sizSkip < 0:
                raise Exception('Skip does not accept a negative value for the relative attribute:' % sizSkip)
            sizSkipParameter = sizSkip

        aulChunk = array.array('I')
        aulChunk.append(self.__get_tag_id('S', 'K', 'I', 'P'))
        aulChunk.append(sizSkipParameter + self.__sizHashDw)

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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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
                    raise Exception('Unexpected node: %s' % tNode.localName)

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

    def parse_image(self, tInput):
        # Parsing an image requires the patch definition.
        if self.__cPatchDefinitions is None:
            raise Exception('A patch definition is required for the "parse_image" function, but none was specified!')

        # Initialize the list of dependencies.
        self.__astrDependencies = []

        # Read the complete input file as plain text.
        tFile = open(tInput, 'rt')
        strFileContents = tFile.read()
        tFile.close()

        # Replace and convert to XML.
        tXml = self.__plaintext_to_xml_with_replace(strFileContents, self.__atGlobalDefines, True)
        tXmlRootNode = tXml.documentElement

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

        # Get the start offset. Default to 0.
        ulStartOffset = 0
        strStartOffset = tXmlRootNode.getAttribute('offset')
        if len(strStartOffset) != 0:
            ulStartOffset = long(strStartOffset)
            if ulStartOffset < 0:
                raise Exception('The start offset is invalid: %d' % ulStartOffset)
        self.__ulStartOffset = ulStartOffset

        # Get the device. Default to "UNSPECIFIED".
        astrValidDeviceNames = [
            'UNSPECIFIED',
            'INTFLASH',
            'SQIROM'
        ]
        strDevice = tXmlRootNode.getAttribute('device')
        if len(strDevice) == 0:
            strDevice = 'UNSPECIFIED'
        else:
            # Check the device name.
            if strDevice not in astrValidDeviceNames:
                raise Exception('Invalid device name specified: "%s". Valid names are %s.' % (strDevice, ', '.join(astrValidDeviceNames)))
        self.__strDevice = strDevice

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
                            strChunkName = tChunkNode.localName
                            if strChunkName == 'Options':
                                # Found an option node.
                                atChunk = self.__build_chunk_options(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'Data':
                                # Found a data node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('Data chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_data(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'XIP':
                                # Found an XIP node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('XIP chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_xip(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'Execute':
                                # Found an execute node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('Execute chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_execute(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'ExecuteCA9':
                                # Found an execute node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('ExecuteCA9 chunks are not allowed in SECMEM images.')
                                if self.__strNetxType == 'NETX56':
                                    raise Exception('ExecuteCA9 chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_execute_ca9(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'SpiMacro':
                                # Found a SPI macro.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('SpiMacro chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_spi_macro(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'Skip':
                                # Found a skip node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('Skip chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_skip(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'RootCert':
                                # Found a root certificate node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('RootCert chunks are not allowed in SECMEM images.')
                                if self.__strNetxType == 'NETX56':
                                    raise Exception('RootCert chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_root_cert(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'LicenseCert':
                                # Found a license certificate node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('LicenseCert chunks are not allowed in SECMEM images.')
                                if self.__strNetxType == 'NETX56':
                                    raise Exception('LicenseCert chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_license_cert(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'CR7Software':
                                # Found a CR7 software node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('CR7Software chunks are not allowed in SECMEM images.')
                                if self.__strNetxType == 'NETX56':
                                    raise Exception('CR7Software chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_cr7sw(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'CA9Software':
                                # Found a CA9 software node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('CA9Software chunks are not allowed in SECMEM images.')
                                if self.__strNetxType == 'NETX56':
                                    raise Exception('CA9Software chunks are not allowed on netx56.')
                                atChunk = self.__build_chunk_ca9sw(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            elif strChunkName == 'MemoryDeviceUp':
                                # Found a memory device up node.
                                if self.__tImageType == self.__IMAGE_TYPE_SECMEM:
                                    raise Exception('MemoryDeviceUp chunks are not allowed in SECMEM images.')
                                atChunk = self.__build_chunk_memory_device_up(tChunkNode)
                                self.__atChunks.extend(atChunk)
                            else:
                                raise Exception('Unknown chunk ID: %s' % strChunkName)
                else:
                    raise Exception('Unknown element: %s' % tImageNode.localName)

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

    def dependency_scan(self, strInput):
        tXml = xml.dom.minidom.parse(strInput)

        # Initialize the list of dependencies.
        self.__astrDependencies = []

        # Preprocess the image.
        self.__preprocess(tXml)

        # Scan the complete definition for "File" nodes.
        atFileNodes = tXml.getElementsByTagName('File')
        for tNode in atFileNodes:
            strFileName = tNode.getAttribute('name')
            if strFileName is not None:
                if strFileName[0] == '@':
                    strFileId = strFileName[1:]
                    if strFileId not in self.__atKnownFiles:
                        raise Exception('Unknown reference to file ID "%s".' % strFileName)
                    strFileName = self.__atKnownFiles[strFileId]
                self.__astrDependencies.append(strFileName)

        return self.__astrDependencies
