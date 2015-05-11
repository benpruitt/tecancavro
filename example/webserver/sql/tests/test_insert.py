# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2013, Cédric Krier
# Copyright (c) 2013, Nicolas Évrard
# Copyright (c) 2011-2013, B2CK
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

from sql import Table, With
from sql.functions import Abs


class TestInsert(unittest.TestCase):
    table = Table('t')

    def test_insert_default(self):
        query = self.table.insert()
        self.assertEqual(str(query), 'INSERT INTO "t" DEFAULT VALUES')
        self.assertEqual(query.params, ())

    def test_insert_values(self):
        query = self.table.insert([self.table.c1, self.table.c2],
            [['foo', 'bar']])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c1", "c2") VALUES (%s, %s)')
        self.assertEqual(query.params, ('foo', 'bar'))

    def test_insert_many_values(self):
        query = self.table.insert([self.table.c1, self.table.c2],
            [['foo', 'bar'], ['spam', 'eggs']])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c1", "c2") VALUES (%s, %s), (%s, %s)')
        self.assertEqual(query.params, ('foo', 'bar', 'spam', 'eggs'))

    def test_insert_subselect(self):
        t1 = Table('t1')
        t2 = Table('t2')
        subquery = t2.select(t2.c1, t2.c2)
        query = t1.insert([t1.c1, t1.c2], subquery)
        self.assertEqual(str(query),
            'INSERT INTO "t1" ("c1", "c2") '
            'SELECT "a"."c1", "a"."c2" FROM "t2" AS "a"')
        self.assertEqual(query.params, ())

    def test_insert_function(self):
        query = self.table.insert([self.table.c], [[Abs(-1)]])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c") VALUES (ABS(%s))')
        self.assertEqual(query.params, (-1,))

    def test_insert_returning(self):
        query = self.table.insert([self.table.c1, self.table.c2],
            [['foo', 'bar']], returning=[self.table.c1, self.table.c2])
        self.assertEqual(str(query),
            'INSERT INTO "t" ("c1", "c2") VALUES (%s, %s) '
            'RETURNING "c1", "c2"')
        self.assertEqual(query.params, ('foo', 'bar'))

    def test_with(self):
        t1 = Table('t1')
        w = With(query=t1.select())

        query = self.table.insert(
            [self.table.c1],
            with_=[w],
            values=w.select())
        self.assertEqual(str(query),
            'WITH a AS (SELECT * FROM "t1" AS "b") '
            'INSERT INTO "t" ("c1") SELECT * FROM a AS "a"')
        self.assertEqual(query.params, ())
