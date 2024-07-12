# Copyright (C) 2012  Cristian Lizana <cristian@lizana.in>
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


import os.path

from reportlab.pdfgen import canvas

from .image import EReaderData


class PDFImage(object):
    def __init__(self, path, title, device):
        output_directory = os.path.dirname(path)
        output_file_name = '%s.pdf' % os.path.basename(path)
        output_path = os.path.join(output_directory, output_file_name)
        # self._current_device = device
        # self.bookTitle = title
        self._page_size = EReaderData.Profiles[device][0]
        # pagesize could be letter or A4 for standardization, but we need to control some image sizes
        self.canvas = canvas.Canvas(output_path, pagesize=self._page_size)
        self.canvas.setAuthor("Poutoux")
        self.canvas.setTitle(title)
        self.canvas.setSubject("Created for " + device)
    
    
    def addImage(self, filename):
        self.canvas.drawImage(filename, 0, 0, width=self._page_size[0], height=self._page_size[1], preserveAspectRatio=True, anchor='c')
        self.canvas.showPage()
    
    
    def __enter__(self):
        return self
    
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    
    def close(self):
        self.canvas.save()
