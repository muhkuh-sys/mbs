# -*- coding: utf-8 -*-

import Tkinter
import tkFont
import version

from xml.etree.ElementTree import ElementTree
from xml.etree.ElementTree import SubElement
from xml.etree.ElementTree import XML


class App:
	# Do not propagate changes of the version text field.
	fArtificialVersionTextChange = False
	# Do not propagate changes of the version radio button.
	fArtificialVersionRadioChange = False

	strVersion_SNAPSHOT = 'SNAPSHOT'
	# TODO: generate these version numbers from the latest version.
	strVersion_Minor = '1.20.0'
	strVersion_Major = '2.0.0'

	def __init__(self, tMaster, tNode):
		self.tFont_GAVLabel = tkFont.Font(family='Helvetica', size=16)
		self.tFont_ActionSelector = tkFont.Font(family='Helvetica', size=10)
		self.tFont_VersionButton = tkFont.Font(family='Courier', size=10)

		strValue = tNode.get('file')
		if strValue==None:
			raise Exception('One of the Target nodes has no file attribute!')
		else:
			self.strXmlFile = strValue.strip()
			if self.strXmlFile=='':
				raise Exception('One of the Target nodes has an empty file attribute!')

		strValue = tNode.findtext('ArtifactID')
		if strValue==None:
			raise Exception('One of the Target nodes has no ArtifactID child!')
		else:
			self.strXmlArtifactID = strValue.strip()
			if self.strXmlArtifactID=='':
				raise Exception('One of the Target nodes has an empty ArtifactID child!')

		strValue = tNode.findtext('GroupID')
		if strValue==None:
			raise Exception('One of the Target nodes has no GroupID child!')
		else:
			self.strXmlGroupID = strValue.strip()
			if self.strXmlGroupID=='':
				raise Exception('One of the Target nodes has an empty GroupID child!')

		strValue = tNode.findtext('Packaging')
		if strValue==None:
			raise Exception('One of the Target nodes has no Packaging child!')
		else:
			self.strXmlPackaging = strValue.strip()
			if self.strXmlPackaging=='':
				raise Exception('One of the Target nodes has an empty Packaging child!')


		self.tFrame = Tkinter.Frame(tMaster, borderwidth=1)
		self.tFrame.grid_columnconfigure(3, weight=1)
#		self.tFrame.pack(fill=Tkinter.X, expand=1)

		self.tCheckVar = Tkinter.BooleanVar()
		tCheckButton = Tkinter.Checkbutton(self.tFrame, variable=self.tCheckVar, command=self.select)
		tCheckButton.grid(row=0, column=0, rowspan=3)

		tLabel0 = Tkinter.Label(self.tFrame, font=self.tFont_GAVLabel, text='%s.%s'%(self.strXmlGroupID, self.strXmlArtifactID))
		tLabel0.grid(row=0, column=1, columnspan=3, sticky=Tkinter.W)

		astrActions = ['Compare with', 'def', 'ghi']
		tActionVar = Tkinter.StringVar()
		tActionVar.set(astrActions[0])
		tAction0 = Tkinter.OptionMenu(self.tFrame, tActionVar, *astrActions)
		tAction0.grid(row=1, column=1, rowspan=2)

		tActionButton = Tkinter.Button(self.tFrame, text='Go', command=self.button_action)
		tActionButton.grid(row=1, column=2, rowspan=2)

		self.tVersionCanvas = Tkinter.Canvas(self.tFrame)
		self.tVersionCanvas.grid(row=1, column=3, sticky=Tkinter.W+Tkinter.E)

		# Create the scrollbar.
		self.tScrollbarX = Tkinter.Scrollbar(self.tFrame, orient=Tkinter.HORIZONTAL, command=self.tVersionCanvas.xview)
		self.tScrollbarX.grid(row=2, column=3, sticky=Tkinter.E+Tkinter.W)

		self.tVersionCanvas.configure(xscrollcommand=self.tScrollbarX.set)


		self.tVersionFrame = Tkinter.Frame(self.tVersionCanvas, borderwidth=2, relief=Tkinter.SUNKEN)
		tCanvasWindow = self.tVersionCanvas.create_window(0, 0, window=self.tVersionFrame, anchor=Tkinter.N+Tkinter.W)

		tRadioVar = Tkinter.IntVar()
		for iCnt in range(20):
			if (iCnt&3)==0:
				tState = Tkinter.DISABLED
			else:
				tState = Tkinter.NORMAL

			tRadio = Tkinter.Radiobutton(self.tVersionFrame, font=self.tFont_VersionButton, indicatoron=0, state=tState, text='1.%d.0'%iCnt, value=iCnt, variable=tRadioVar)
			tRadio.pack(side=Tkinter.LEFT)
		# Remember the radio button of the latest version to select it later.
		self.tLastRadio = tRadio

		# Update display to get correct dimensions
		self.tVersionFrame.update_idletasks()
		# Set the height of the canvas to the height of the frame. Set the scrollregion to the width of the frame.
		self.tVersionCanvas.configure(height=self.tVersionFrame.winfo_reqheight(), scrollregion=(0, 0, self.tVersionFrame.winfo_width(), self.tVersionFrame.winfo_height()))
		# Scroll to the right end of the area. This displays the latest version.
		self.tVersionCanvas.xview_moveto(1.0)

		# Add the three radiobuttons for "SNAPSHOT", "Minor" and "Major".
		self.tRadioSnapshotVar = Tkinter.StringVar()
		tRadio = Tkinter.Radiobutton(self.tFrame, command=self.select_version, indicatoron=1, state=tState, value=self.strVersion_SNAPSHOT, variable=self.tRadioSnapshotVar)
		tRadio.grid(row=0, column=4, rowspan=3)
		tRadio = Tkinter.Radiobutton(self.tFrame, command=self.select_version, indicatoron=1, state=tState, value=self.strVersion_Minor, variable=self.tRadioSnapshotVar)
		tRadio.grid(row=0, column=5, rowspan=3)
		tRadio = Tkinter.Radiobutton(self.tFrame, command=self.select_version, indicatoron=1, state=tState, value=self.strVersion_Major, variable=self.tRadioSnapshotVar)
		tRadio.grid(row=0, column=6, rowspan=3)

		self.tVersionVar = Tkinter.StringVar()
		tValidateCommand = (tMaster.register(self.version_validate), '%P')
		tVersionText = Tkinter.Entry(self.tFrame, exportselection=0, textvariable=self.tVersionVar, validate='key', validatecommand=tValidateCommand)
		tVersionText.grid(row=0, column=7, rowspan=3)


	def version_validate(self, strNewValue):
		# This function is callen when the version text is changed.
		if self.fArtificialVersionTextChange==False:
			# Is this one of the known versions?
			strNewSelection = ''
			if strNewValue==self.strVersion_SNAPSHOT or strNewValue==self.strVersion_Minor or strNewValue==self.strVersion_Major:
				strNewSelection = strNewValue

			self.fArtificialVersionRadioChange = True
			self.tRadioSnapshotVar.set(strNewSelection)
			self.fArtificialVersionRadioChange = False
		return True


	def select(self):
		print self.tCheckVar.get()


	def select_version(self):
		if self.fArtificialVersionRadioChange==False:
			# Replace the version text with the current selection.
			strVersion = self.tRadioSnapshotVar.get()
			self.fArtificialVersionTextChange = True
			self.tVersionVar.set(strVersion)
			self.fArtificialVersionTextChange = False


	def button_action(self):
		print 'Go clicked!'


	def show(self, fVisible):
		if fVisible==True:
			self.tFrame.pack(fill=Tkinter.X, expand=1)
		else:
			self.tFrame.pack_forget()



# Read the artifact list.
tXml = ElementTree()
tXml.parse('targets/artifacts2.xml')



tMainWindow = Tkinter.Tk()

# Process all Target nodes.
aApps = []
for tNode in tXml.findall('Project/Targets/Target'):
	tApp = App(tMainWindow, tNode)
	aApps.append(tApp)

# Update display to get correct dimensions
tMainWindow.update_idletasks()

tMainWindow.pack_propagate(0)

iCnt = 0
for tApp in aApps:
	tApp.tLastRadio.select()
	if (iCnt&1)==0:
		tApp.show(True)
	else:
		tApp.show(False)

	iCnt = iCnt + 1

tMainWindow.mainloop()

