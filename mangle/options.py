# Copyright (C) 2010  Alex Yatskov
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from PyQt6 import QtWidgets, uic

from .image import ImageFlags
from .util import get_ui_path


class DialogOptions(QtWidgets.QDialog):
    def __init__(self, parent, book):
        super().__init__(parent)
        
        uic.loadUi(get_ui_path('ui/options.ui'), self)
        self.accepted.connect(self.onAccept)
        
        self.book = book
        self.moveOptionsToDialog()
    
    
    def onAccept(self):
        self.moveDialogToOptions()
    
    
    # Get options from current book (like a loaded one) and set the dialog values
    def moveOptionsToDialog(self):
        self.lineEditTitle.setText(self.book.title or 'Untitled')
        self.comboBoxDevice.setCurrentIndex(max(self.comboBoxDevice.findText(self.book.device), 0))
        self.comboBoxFormat.setCurrentIndex(max(self.comboBoxFormat.findText(self.book.outputFormat), 0))
        self.checkboxOverwrite.setChecked(self.book.overwrite)
        self.checkboxOrient.setChecked(self.book.imageFlags & ImageFlags.Orient)
        self.checkboxResize.setChecked(self.book.imageFlags & ImageFlags.Resize)
        self.checkboxStretch.setChecked(self.book.imageFlags & ImageFlags.Stretch)
        self.checkboxQuantize.setChecked(self.book.imageFlags & ImageFlags.Quantize)
        self.checkboxFrame.setChecked(self.book.imageFlags & ImageFlags.Frame)
        self.checkboxAutoCrop.setChecked(self.book.imageFlags & ImageFlags.AutoCrop)
        self.checkboxWebtoon.setChecked(self.book.imageFlags & ImageFlags.Webtoon)
    
    
    # Save parameters set on the dialogs to the book object if need
    def moveDialogToOptions(self):
        # First get dialog values
        title = self.lineEditTitle.text()
        device = self.comboBoxDevice.currentText()
        output_format = self.comboBoxFormat.currentText()
        overwrite = self.checkboxOverwrite.isChecked()
        
        # Now compute flags
        image_flags = 0
        if self.checkboxOrient.isChecked():
            image_flags |= ImageFlags.Orient
        if self.checkboxResize.isChecked():
            image_flags |= ImageFlags.Resize
        if self.checkboxStretch.isChecked():
            image_flags |= ImageFlags.Stretch
        if self.checkboxQuantize.isChecked():
            image_flags |= ImageFlags.Quantize
        if self.checkboxFrame.isChecked():
            image_flags |= ImageFlags.Frame
        if self.checkboxSplit.isChecked():
            image_flags |= ImageFlags.SplitRightLeft
        if self.checkboxSplitInverse.isChecked():
            image_flags |= ImageFlags.SplitLeftRight
        if self.checkboxAutoCrop.isChecked():
            image_flags |= ImageFlags.AutoCrop
        if self.checkboxWebtoon.isChecked():
            image_flags |= ImageFlags.Webtoon
        
        # If we did modify a value, update the book and only if we did change something to not
        # warn for nothing the user
        modified = (
                self.book.title != title or
                self.book.device != device or
                self.book.overwrite != overwrite or
                self.book.imageFlags != image_flags or
                self.book.outputFormat != output_format
        )
        
        if modified:
            self.book.modified = True
            self.book.title = title
            self.book.device = device
            self.book.overwrite = overwrite
            self.book.imageFlags = image_flags
            self.book.outputFormat = output_format
