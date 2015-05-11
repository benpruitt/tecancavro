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

from sql import Table, Union


class TestUnion(unittest.TestCase):
    q1 = Table('t1').select()
    q2 = Table('t2').select()
    q3 = Table('t3').select()

    def test_union2(self):
        query = Union(self.q1, self.q2)
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b"')
        self.assertEqual(query.params, ())

        query = self.q1 | self.q2
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b"')
        self.assertEqual(query.params, ())

    def test_union3(self):
        query = Union(self.q1, self.q2, self.q3)
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(query.params, ())

        query = Union(Union(self.q1, self.q2), self.q3)
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(query.params, ())

        query = Union(self.q1, Union(self.q2, self.q3))
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(query.params, ())

        query = self.q1 | self.q2 | self.q3
        self.assertEqual(str(query),
            'SELECT * FROM "t1" AS "a" UNION SELECT * FROM "t2" AS "b" '
            'UNION SELECT * FROM "t3" AS "c"')
        self.assertEqual(query.params, ())
