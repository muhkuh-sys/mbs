# -*- coding: utf-8 -*-

import hashlib
import os
import os.path
import sqlite3
import xml.dom.minidom


class SnippetLibrary:
    # The filename for the database.
    __strDatabasePath = None

    # The database connection.
    __tDb = None

    # The list of folders to scan recursively for snippets.
    __astrSnippetFolders = ['targets/snippets']

    # The snippet library was already scanned if this flag is set.
    __fSnipLibIsAlreadyScanned = None

    def __init__(self, strDatabasePath):
        self.__strDatabasePath = strDatabasePath

        # The connection to the database is not open yet.
        self.__tDb = None

        # The snippet library was not scanned yet.
        self.__fSnipLibIsAlreadyScanned = False

    def __xml_get_all_text(self, tNode):
        astrText = []
        for tChild in tNode.childNodes:
            if (tChild.nodeType == tChild.TEXT_NODE) or (tChild.nodeType == tChild.CDATA_SECTION_NODE):
                astrText.append(str(tChild.data))
        return ''.join(astrText)

    def __xml_get_node(self, tBaseNode, strTagName):
        tNode = None
        for tChildNode in tBaseNode.childNodes:
            if tChildNode.nodeType == tChildNode.ELEMENT_NODE:
                if tChildNode.localName == strTagName:
                    tNode = tChildNode
                    break

        return tNode

    def __get_snip_hash(self, strAbsPath):
        # Get the SHA384 hash.
        tFile = open(strAbsPath, 'rb')
        tHash = hashlib.sha384()
        fEof = False
        while fEof==False:
            strData = tFile.read(2048)
            tHash.update(strData)
            if len(strData)<2048:
                fEof = True
        strDigest = tHash.hexdigest()
        tFile.close()

        # Return the hash.
        return strDigest

    def __db_open(self):
        tDb = self.__tDb
        if tDb is None:
            tDb = sqlite3.connect(self.__strDatabasePath)
            self.__tDb = tDb

        # Create the table if the do not exist yet.
        tCursor = tDb.cursor()
        tCursor.execute('CREATE TABLE IF NOT EXISTS snippets (id INTEGER PRIMARY KEY, path TEXT NOT NULL, hash TEXT NOT NULL, groupid TEXT NOT NULL, artifact TEXT NOT NULL, version TEXT NOT NULL, clean INTEGER DEFAULT 0)')
        tDb.commit()

    def __snippet_get_gav(self, strPath):
        strGroup = None
        strArtifact = None
        strVersion = None

        # Parse the snippet.
        try:
            tXml = xml.dom.minidom.parse(strPath)
        except xml.dom.DOMException as tException:
            # Invalid XML, ignore.
            strArtifact = 'No valid XML: %s' % repr(tException)
            tXml = None

        if tXml!=None:
            # Search for the "Info" node.
            tInfoNode = self.__xml_get_node(self, tXml.documentElement, 'Info')
            if tInfoNode is None:
                # No Info node -> ignore the file.
                strArtifact = 'It has no "Info" node.'
            else:
                # Get the "group", "artifact" and "version" attributes.
                strGroup = tInfoNode.getAttribute('group')
                strArtifact = tInfoNode.getAttribute('artifact')
                strVersion = tInfoNode.getAttribute('version')
                if len(strGroup)==0:
                    strGroup = None
                    strArtifact = 'The "group" attribute of an "Info" node must not be empty.'
                elif len(strArtifact)==0:
                    strGroup = None
                    strArtifact = 'The "artifact" attribute of an "Info" node must not be empty.'
                elif len(strVersion)==0:
                    strGroup = None
                    strArtifact = 'The "version" attribute of an "Info" node must not be empty.'

        # Return the group, artifact and version.
        return strGroup, strArtifact, strVersion

    def __sniplib_scan(self, strSnipLibFolder):
        # Mark all files to be deleted. This flag will be cleared for all files which are present.
        tCursor = self.__tDb.cursor()
        tCursor.execute('UPDATE snippets SET clean=1')
        self.__tDb.commit()

        # Search all files recursively.
        for strRoot, astrDirs, astrFiles in os.walk(strSnipLibFolder, followlinks=True):
            # Process all files in this folder.
            for strFile in astrFiles:
                # Get the extension of the file.
                strDummy, strExt = os.path.splitext(strFile)
                if strExt=='.xml':
                    # Get the absolute path for the file.
                    strAbsPath = os.path.join(strRoot, strFile)

                    # Get the stamp of the snip.
                    strDigest = self.__get_snip_hash(strAbsPath)

                    # Search the snippet in the database.
                    tCursor.execute('SELECT id,hash FROM snippets WHERE path=?', (strAbsPath, ))
                    atResults = tCursor.fetchone()
                    if atResults is None:
                        # The snippet is not present in the database yet.
                        strGroup, strArtifact, strVersion = self.__snippet_get_gav(strAbsPath)
                        if strGroup is None:
                            print 'Warning: Ignoring file "%s". %s' % (strAbsPath, strArtifact)

                        # Make a new entry.
                        tCursor = self.__tDb.cursor()
                        tCursor.execute('INSERT INTO snippets (path, hash, groupid, artifact, version) VALUES (?, ?, ?, ?, ?)', (strAbsPath, strDigest, strGroup, strArtifact, strVersion))
                    else:
                        # Compare the hash of the file.
                        if atResults[1] == strDigest:
                            # Found the file. Do not delete it from the database.
                            tCursor.execute('UPDATE snippets SET clean=0 WHERE id=?', (atResults[0], ))

        # Remove all entries which are marked for clean.
        tCursor.execute('DELETE FROM snippets WHERE clean!=0')
        self.__tDb.commit()

    def find(self, strGroup, strArtifact, strVersion):
        # Open the connection to the database.
        self.__db_open()

        # Scan the SnipLib.
        if self.__fSnipLibIsAlreadyScanned!=True:
            for strSnipLibPath in self.__astrSnippetFolders:
                self.__sniplib_scan(strSnipLibPath)

        # Search for a direct match. This is possible when a version was specified.
        tCursor = self.__tDb.cursor()
        atResult = None
        if len(strVersion)!=0:
            tCursor.execute('SELECT path FROM snippets WHERE groupid=? AND artifact=? AND version=?', (strGroup, strArtifact, strVersion))
            atResult = tCursor.fetchone()

        if atResult is None:
            # Search for all snippets with this group and artifact.
            tCursor.execute('SELECT path FROM snippets WHERE groupid=? AND artifact=?', (strGroup, strArtifact))
            atResults = tCursor.fetchall()
            print 'find best match'
            print repr(atResults)
            raise Exception('Not yet.')

        if atResult is None:
            # No matching snippet found.
            raise Exception('No matching snippet found for G="%s", A="%s", V="%s".' % (strGroup, strArtifact, strVersion))

        # Try to parse the snippet file.
        strAbsPath = atResult[0]
        try:
            tXml = xml.dom.minidom.parse(strAbsPath)
        except xml.dom.DOMException as tException:
            # Invalid XML, ignore.
            raise Exception('Failed to parse the snippet: %s' % repr(tException))

        # Find the "Snippet" node.
        tRootNode = tXml.documentElement
        tSnippetNode = self.__xml_get_node(tRootNode, 'Snippet')
        if tSnippetNode is None:
            raise Exception('The snippet definition "%s" has no "Snippet" node.' % strAbsPath)

        return tSnippetNode
