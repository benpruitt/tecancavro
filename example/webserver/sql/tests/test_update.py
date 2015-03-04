# -*- coding: utf-8 -*-
#
# Copyright (c) 2011-2013, Cédric Krier
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

from sql import Table, Literal, With


class TestUpdate(unittest.TestCase):
    table = Table('t')

    def test_update1(self):
        query = self.table.update([self.table.c], ['foo'])
        self.assertEqual(str(query), 'UPDATE "t" SET "c" = %s')
        self.assertEqual(query.params, ('foo',))

        query.where = (self.table.b == Literal(True))
        self.assertEqual(str(query),
            'UPDATE "t" SET "c" = %s WHERE ("t"."b" = %s)')
        self.assertEqual(query.params, ('foo', True))

    def test_update2(self):
        t1 = Table('t1')
        t2 = Table('t2')
        query = t1.update([t1.c], ['foo'], from_=[t2], where=(t1.c == t2.c))
        self.assertEqual(str(query),
            'UPDATE "t1" AS "b" SET "c" = %s FROM "t2" AS "a" '
            'WHERE ("b"."c" = "a"."c")')
        self.assertEqual(query.params, ('foo',))

    def test_update_subselect(self):
        t1 = Table('t1')
        t2 = Table('t2')
        query_list = t1.update([t1.c], [t2.select(t2.c, where=t2.i == t1.i)])
        query_nolist = t1.update([t1.c], t2.select(t2.c, where=t2.i == t1.i))
        for query in [query_list, query_nolist]:
            self.assertEqual(str(query),
                'UPDATE "t1" SET "c" = ('
                'SELECT "b"."c" FROM "t2" AS "b" WHERE ("b"."i" = "t1"."i"))')
            self.assertEqual(query.params, ())

    def test_update_returning(self):
        query = self.table.update([self.table.c], ['foo'],
            returning=[self.table.c])
        self.assertEqual(str(query),
            'UPDATE "t" SET "c" = %s RETURNING "t"."c"')
        self.assertEqual(query.params, ('foo',))

    def test_with(self):
        t1 = Table('t1')
        w = With(query=t1.select(t1.c1))

        query = self.table.update(
            [self.table.c2],
            with_=[w],
            values=[w.select(w.c3, where=w.c4 == 2)])
        self.assertEqual(str(query),
            'WITH b AS (SELECT "c"."c1" FROM "t1" AS "c") '
            'UPDATE "t" SET "c2" = (SELECT "b"."c3" FROM b AS "b" '
            'WHERE ("b"."c4" = %s))')
        self.assertEqual(query.params, (2,))
