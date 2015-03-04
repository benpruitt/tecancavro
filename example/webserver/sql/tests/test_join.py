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

from sql import Join, Table, AliasManager
from sql.functions import Now


class TestJoin(unittest.TestCase):
    def test_join(self):
        t1 = Table('t1')
        t2 = Table('t2')
        join = Join(t1, t2)
        with AliasManager():
            self.assertEqual(str(join), '"t1" AS "a" INNER JOIN "t2" AS "b"')
            self.assertEqual(join.params, ())

        join.condition = t1.c == t2.c
        with AliasManager():
            self.assertEqual(str(join),
                '"t1" AS "a" INNER JOIN "t2" AS "b" ON ("a"."c" = "b"."c")')

    def test_join_subselect(self):
        t1 = Table('t1')
        t2 = Table('t2')
        select = t2.select()
        join = Join(t1, select)
        join.condition = t1.c == select.c
        with AliasManager():
            self.assertEqual(str(join),
                '"t1" AS "a" INNER JOIN (SELECT * FROM "t2" AS "c") AS "b" '
                'ON ("a"."c" = "b"."c")')
            self.assertEqual(join.params, ())

    def test_join_function(self):
        t1 = Table('t1')
        join = Join(t1, Now())
        with AliasManager():
            self.assertEqual(str(join), '"t1" AS "a" INNER JOIN NOW() AS "b"')
            self.assertEqual(join.params, ())
