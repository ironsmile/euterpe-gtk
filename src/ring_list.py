# ring_list.py
#
# Copyright 2023 Doychin Atanasov
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

class RingList:
    '''
    RingList is a limited sized list which evicts its LRU item
    when there is more space during adding new items.

    The list is always kept sorted in LRU fashion. From the most
    recently used down to the least recently used.
    '''
    
    _size = 10
    _cmp = lambda x,y: False
    _list = []

    def __init__(self, size, cmp_func, init_list=[]):
        self._size = size
        self._cmp = cmp_func
        self._list = init_list[:size]

    def add(self, item):
        '''
        Add adds item to the head of the list if it was not
        part of the list already. It there's the same value
        in the list then it moves it to the head.

        In case the list is already at its maximum size then
        the least recently added value is removed.

        Returns True when the list has been modified and
        False when it hasn't been. The latter is only possible
        if item is already at the head of the list.
        '''
        for i, v in enumerate(self._list):
            if not self._cmp(v, item):
                continue

            if i == 0:
                return False

            self._list = self._list[:i] + self._list[i+1:]
            self._list.insert(0, v)
            return True

        self._list.insert(0, item)
        if len(self._list) > self._size:
            self._list = self._list[:-1]
        return True

    def list(self):
        '''
        List returns a copy of the RingList as list where
        elements are ordered from the most recently added to the
        least recently added.
        '''
        return self._list[:]

    def replace(self, new_list):
        '''
        Replace clears the current list and uses new_list as its
        value.
        '''
        self._list = new_list[:self._size]
