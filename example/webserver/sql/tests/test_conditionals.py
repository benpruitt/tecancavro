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

from sql import Table
from sql.conditionals import Case, Coalesce, NullIf, Greatest, Least


class TestConditionals(unittest.TestCase):
    table = Table('t')

    def test_case(self):
        case = Case((self.table.c1, 'foo'),
            (self.table.c2, 'bar'),
            else_=self.table.c3)
        self.assertEqual(str(case),
            'CASE WHEN "c1" THEN %s '
            'WHEN "c2" THEN %s '
            'ELSE "c3" END')
        self.assertEqual(case.params, ('foo', 'bar'))

    def test_case_no_expression(self):
        case = Case((True, self.table.c1), (self.table.c2, False),
            else_=False)
        self.assertEqual(str(case),
            'CASE WHEN %s THEN "c1" '
            'WHEN "c2" THEN %s '
            'ELSE %s END')
        self.assertEqual(case.params, (True, False, False))

    def test_coalesce(self):
        coalesce = Coalesce(self.table.c1, self.table.c2, 'foo')
        self.assertEqual(str(coalesce), 'COALESCE("c1", "c2", %s)')
        self.assertEqual(coalesce.params, ('foo',))

    def test_nullif(self):
        nullif = NullIf(self.table.c1, 'foo')
        self.assertEqual(str(nullif), 'NULLIF("c1", %s)')
        self.assertEqual(nullif.params, ('foo',))

    def test_greatest(self):
        greatest = Greatest(self.table.c1, self.table.c2, 'foo')
        self.assertEqual(str(greatest), 'GREATEST("c1", "c2", %s)')
        self.assertEqual(greatest.params, ('foo',))

    def test_least(self):
        least = Least(self.table.c1, self.table.c2, 'foo')
        self.assertEqual(str(least), 'LEAST("c1", "c2", %s)')
        self.assertEqual(least.params, ('foo',))
