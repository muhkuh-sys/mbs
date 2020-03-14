# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------- #
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
# ----------------------------------------------------------------------- #

import time
import sys


class ProgressOutput:
    # This is the minimum time between 2 flushes in seconds.
    m_tTimeMinimumFlushIntervall = 1.0
    m_tTimeLastFlushTime = 0

    # This is the size for one dot.
    m_sizDot = None

    # This is the total size of the file. 0 means the total size is unknown.
    m_sizTotal = 0

    # This is an internal state variable which records what has been printed
    # on a line yet.
    # 0 means it is a blank line
    # >0 is the number of dots printed.
    m_uiDotsPrintedInCurrentLine = 0
    m_uiDotsPerLine = 50
    # This is the download position at the start of the line in bytes.
    m_uiLinePositionStart = 0

    m_sizCurrent = None

    def __init__(self, sizTotal):
        # Set the size for one dot according to the total size.
        print('sizTotal', sizTotal)
        if sizTotal == 0:
            # Unknown total size -> default to 2048.
            sizDot = 2048
        else:
            # Try to get a maximum of 20 lines at a maximum of 1MB dots.
            sizMaxLines = 20
            sizDot = sizTotal / self.m_uiDotsPerLine / sizMaxLines
            if sizDot > 1024 * 1024:
                sizDot = 1024 * 1024
            elif sizDot < 2048:
                sizDot = 2048
        self.m_sizDot = sizDot
        self.m_sizTotal = sizTotal
        self.m_tTimeLastFlushTime = time.time()
        self.m_uiDotsPrintedInCurrentLine = None
        self.m_sizCurrent = 0
        self.m_uiLinePositionStart = 0
        self.update(0)

    def update(self, sizData):
        # Print dots or header?
        fPrintDots = (sizData > 0) or (self.m_sizCurrent == 0)
        # Loop over all dots line by line.
        while fPrintDots is True:
            # Print a header if this is the start of the line.
            if self.m_uiDotsPrintedInCurrentLine is None:
                # Only print the percent information if the total size is
                # known.
                if self.m_sizTotal != 0:
                    # Get the new percentage.
                    uiPercent = 100.0 * self.m_sizCurrent / self.m_sizTotal
                    sys.stdout.write('% 3d%% ' % uiPercent)
                else:
                    sys.stdout.write('     ')
                self.m_uiDotsPrintedInCurrentLine = 0

            # Get the end position of the line in bytes.
            sizLineEnd = (
                self.m_uiLinePositionStart +
                self.m_uiDotsPerLine*self.m_sizDot
            )
            sizDownloaded = self.m_sizCurrent + sizData
            if sizLineEnd > sizDownloaded:
                sizLineEnd = sizDownloaded
            sizChunk = sizLineEnd - self.m_sizCurrent

            # Get the number of bytes in this line.
            sizDotBytes = sizLineEnd - self.m_uiLinePositionStart
            # Get the number of new dots in this line.
            sizDots = (
                int(sizDotBytes / self.m_sizDot) -
                self.m_uiDotsPrintedInCurrentLine
            )
            # Print the new dots.
            sys.stdout.write('.'*sizDots)
            # Update the number of dots printed in this line.
            self.m_uiDotsPrintedInCurrentLine += sizDots

            # Print end of line if the maximum number of dots reached.
            if self.m_uiDotsPrintedInCurrentLine >= self.m_uiDotsPerLine:
                # Terminate the line.
                sys.stdout.write('\n')
                # A line feed is also a flush.
                self.m_tTimeLastFlushTime = time.time()
                # The next line has no dots yet.
                self.m_uiDotsPrintedInCurrentLine = None
                # Set the new line start position.
                self.m_uiLinePositionStart += (
                    self.m_uiDotsPerLine*self.m_sizDot
                )

            self.m_sizCurrent += sizChunk
            sizData -= sizChunk
            # Print more?
            fPrintDots = (sizData > 0)

        # Flush the output stream.
        tLastFlush = time.time() - self.m_tTimeLastFlushTime
        if tLastFlush >= self.m_tTimeMinimumFlushIntervall:
            sys.stdout.flush()

    def finish(self):
        if self.m_uiDotsPrintedInCurrentLine is not None:
            # Terminate the line.
            sys.stdout.write('\n')


def _tst(sizTotal, *args):
    tProgress = ProgressOutput(sizTotal)
    for (sizChunk, tDelay) in args:
        time.sleep(tDelay)
        tProgress.update(sizChunk)
    tProgress.finish()


if __name__ == "__main__":
    print('10 dots with 1 second delay')
    _tst(
        20480,
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1)
    )

    _tst(
        20480,
        (2048, 1),
        (4096, 2),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1),
        (2048, 1)
    )
