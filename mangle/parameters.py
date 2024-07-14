# Copyright 2011-2019 Alex Yatskov
# Copyright 2020+     Gabès Jean (naparuba@gmail.com)
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

from .image import ImageFlags


class Parameters(object):
    DefaultDevice = 'Kobo Libra H2O'
    DefaultImageFlags = 0
    
    images: list[str]
    filename: str | None
    title: str | None
    titleSet: bool
    device: str
    imageFlags: int
    
    
    def __init__(self):
        self.clean()
    
    
    def clean(self):
        self.images = []
        self.filename = None
        self.title = None
        self.titleSet = False
        self.device = self.DefaultDevice
        self.imageFlags = self.DefaultImageFlags


parameters = Parameters()
