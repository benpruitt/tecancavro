# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, Cédric Krier
# Copyright (c) 2014, B2CK
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from sql import Values


class TestValues(unittest.TestCase):
    def test_single_values(self):
        values = Values([[1]])
        self.assertEqual(str(values), 'VALUES (%s)')
        self.assertEqual(values.params, (1,))

    def test_many_values(self):
        values = Values([[1, 2], [3, 4]])
        self.assertEqual(str(values), 'VALUES (%s, %s), (%s, %s)')
        self.assertEqual(values.params, (1, 2, 3, 4))

    def test_select(self):
        values = Values([[1], [2], [3]])
        query = values.select()
        self.assertEqual(str(query),
            'SELECT * FROM (VALUES (%s), (%s), (%s)) AS "a"')
        self.assertEqual(query.params, (1, 2, 3))

    def test_union(self):
        values = Values([[1]])
        values |= Values([[2]])
        self.assertEqual(str(values), 'VALUES (%s) UNION VALUES (%s)')
        self.assertEqual(values.params, (1, 2))
