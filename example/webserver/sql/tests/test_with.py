# -*- coding: utf-8 -*-
#
# Copyright (c) 2014, Nicolas Évrard
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

from sql import AliasManager, Table, Literal, Values, With, WithQuery


class TestWith(unittest.TestCase):
    table = Table('t')

    def test_with(self):
        with AliasManager():
            simple = With(query=self.table.select(self.table.id,
                    where=self.table.id == 1))

            self.assertEqual(simple.statement(),
                'a AS ('
                'SELECT "b"."id" FROM "t" AS "b" WHERE ("b"."id" = %s)'
                ')')
            self.assertEqual(simple.statement_params(), (1,))

    def test_with_columns(self):
        with AliasManager():
            second = With('a', query=self.table.select(self.table.a))

            self.assertEqual(second.statement(),
                'a("a") AS ('
                'SELECT "b"."a" FROM "t" AS "b"'
                ')')
            self.assertEqual(second.statement_params(), ())

    def test_with_query(self):
        with AliasManager():
            simple = With()
            simple.query = self.table.select(self.table.id,
                where=self.table.id == 1)
            second = With()
            second.query = simple.select()

            wq = WithQuery(with_=[simple, second])
            self.assertEqual(wq._with_str(),
                'WITH a AS ('
                'SELECT "b"."id" FROM "t" AS "b" WHERE ("b"."id" = %s)'
                '), c AS ('
                'SELECT * FROM a AS "a"'
                ') ')
            self.assertEqual(wq._with_params(), (1,))

    def test_recursive(self):
        upto10 = With('n', recursive=True)
        upto10.query = Values([(1,)])
        upto10.query |= upto10.select(
            upto10.n + Literal(1),
            where=upto10.n < Literal(100))
        upto10.query.all_ = True

        q = upto10.select(with_=[upto10])
        self.assertEqual(str(q),
            'WITH RECURSIVE a("n") AS ('
            'VALUES (%s) '
            'UNION ALL '
            'SELECT ("a"."n" + %s) FROM a AS "a" WHERE ("a"."n" < %s)'
            ') SELECT * FROM a AS "a"')
        self.assertEqual(q.params, (1, 1, 100))
