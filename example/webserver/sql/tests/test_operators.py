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
import warnings
from array import array

from sql import Table, Literal, Null, Flavor
from sql.operators import (And, Or, Not, Neg, Pos, Less, Greater, LessEqual,
    GreaterEqual, Equal, NotEqual, Sub, Mul, Div, Mod, Pow, Abs, LShift,
    RShift, Like, NotLike, ILike, NotILike, In, NotIn, FloorDiv, Exists)


class TestOperators(unittest.TestCase):
    table = Table('t')

    def test_and(self):
        for and_ in [And((self.table.c1, self.table.c2)),
                self.table.c1 & self.table.c2]:
            self.assertEqual(str(and_), '("c1" AND "c2")')
            self.assertEqual(and_.params, ())

        and_ = And((Literal(True), self.table.c2))
        self.assertEqual(str(and_), '(%s AND "c2")')
        self.assertEqual(and_.params, (True,))

    def test_operator_operators(self):
        and_ = And((Literal(True), self.table.c1))
        and2 = and_ & And((Literal(True), self.table.c2))
        self.assertEqual(str(and2), '((%s AND "c1") AND %s AND "c2")')
        self.assertEqual(and2.params, (True, True))

        and3 = and_ & Literal(True)
        self.assertEqual(str(and3), '((%s AND "c1") AND %s)')
        self.assertEqual(and3.params, (True, True))

        or_ = Or((Literal(True), self.table.c1))
        or2 = or_ | Or((Literal(True), self.table.c2))
        self.assertEqual(str(or2), '((%s OR "c1") OR %s OR "c2")')
        self.assertEqual(or2.params, (True, True))

        or3 = or_ | Literal(True)
        self.assertEqual(str(or3), '((%s OR "c1") OR %s)')
        self.assertEqual(or3.params, (True, True))

    def test_operator_compat_column(self):
        and_ = And((self.table.c1, self.table.c2))
        self.assertEqual(and_.table, '')
        self.assertEqual(and_.name, '')

    def test_or(self):
        for or_ in [Or((self.table.c1, self.table.c2)),
                self.table.c1 | self.table.c2]:
            self.assertEqual(str(or_), '("c1" OR "c2")')
            self.assertEqual(or_.params, ())

    def test_not(self):
        for not_ in [Not(self.table.c), ~self.table.c]:
            self.assertEqual(str(not_), '(NOT "c")')
            self.assertEqual(not_.params, ())

        not_ = Not(Literal(False))
        self.assertEqual(str(not_), '(NOT %s)')
        self.assertEqual(not_.params, (False,))

    def test_neg(self):
        for neg in [Neg(self.table.c1), -self.table.c1]:
            self.assertEqual(str(neg), '(- "c1")')
            self.assertEqual(neg.params, ())

    def test_pos(self):
        for pos in [Pos(self.table.c1), +self.table.c1]:
            self.assertEqual(str(pos), '(+ "c1")')
            self.assertEqual(pos.params, ())

    def test_less(self):
        for less in [Less(self.table.c1, self.table.c2),
                self.table.c1 < self.table.c2,
                ~GreaterEqual(self.table.c1, self.table.c2)]:
            self.assertEqual(str(less), '("c1" < "c2")')
            self.assertEqual(less.params, ())

        less = Less(Literal(0), self.table.c2)
        self.assertEqual(str(less), '(%s < "c2")')
        self.assertEqual(less.params, (0,))

    def test_greater(self):
        for greater in [Greater(self.table.c1, self.table.c2),
                self.table.c1 > self.table.c2,
                ~LessEqual(self.table.c1, self.table.c2)]:
            self.assertEqual(str(greater), '("c1" > "c2")')
            self.assertEqual(greater.params, ())

    def test_less_equal(self):
        for less in [LessEqual(self.table.c1, self.table.c2),
                self.table.c1 <= self.table.c2,
                ~Greater(self.table.c1, self.table.c2)]:
            self.assertEqual(str(less), '("c1" <= "c2")')
            self.assertEqual(less.params, ())

    def test_greater_equal(self):
        for greater in [GreaterEqual(self.table.c1, self.table.c2),
                self.table.c1 >= self.table.c2,
                ~Less(self.table.c1, self.table.c2)]:
            self.assertEqual(str(greater), '("c1" >= "c2")')
            self.assertEqual(greater.params, ())

    def test_equal(self):
        for equal in [Equal(self.table.c1, self.table.c2),
                self.table.c1 == self.table.c2,
                ~NotEqual(self.table.c1, self.table.c2)]:
            self.assertEqual(str(equal), '("c1" = "c2")')
            self.assertEqual(equal.params, ())

        equal = Equal(Literal('foo'), Literal('bar'))
        self.assertEqual(str(equal), '(%s = %s)')
        self.assertEqual(equal.params, ('foo', 'bar'))

        equal = Equal(self.table.c1, Null)
        self.assertEqual(str(equal), '("c1" IS NULL)')
        self.assertEqual(equal.params, ())

        equal = Equal(Literal('test'), Null)
        self.assertEqual(str(equal), '(%s IS NULL)')
        self.assertEqual(equal.params, ('test',))

        equal = Equal(Null, self.table.c1)
        self.assertEqual(str(equal), '("c1" IS NULL)')
        self.assertEqual(equal.params, ())

        equal = Equal(Null, Literal('test'))
        self.assertEqual(str(equal), '(%s IS NULL)')
        self.assertEqual(equal.params, ('test',))

    def test_not_equal(self):
        for equal in [NotEqual(self.table.c1, self.table.c2),
                self.table.c1 != self.table.c2,
                ~Equal(self.table.c1, self.table.c2)]:
            self.assertEqual(str(equal), '("c1" != "c2")')
            self.assertEqual(equal.params, ())

        equal = NotEqual(self.table.c1, Null)
        self.assertEqual(str(equal), '("c1" IS NOT NULL)')
        self.assertEqual(equal.params, ())

        equal = NotEqual(Null, self.table.c1)
        self.assertEqual(str(equal), '("c1" IS NOT NULL)')
        self.assertEqual(equal.params, ())

    def test_sub(self):
        for sub in [Sub(self.table.c1, self.table.c2),
                self.table.c1 - self.table.c2]:
            self.assertEqual(str(sub), '("c1" - "c2")')
            self.assertEqual(sub.params, ())

    def test_mul(self):
        for mul in [Mul(self.table.c1, self.table.c2),
                self.table.c1 * self.table.c2]:
            self.assertEqual(str(mul), '("c1" * "c2")')
            self.assertEqual(mul.params, ())

    def test_div(self):
        for div in [Div(self.table.c1, self.table.c2),
                self.table.c1 / self.table.c2]:
            self.assertEqual(str(div), '("c1" / "c2")')
            self.assertEqual(div.params, ())

    def test_mod(self):
        for mod in [Mod(self.table.c1, self.table.c2),
                self.table.c1 % self.table.c2]:
            self.assertEqual(str(mod), '("c1" %% "c2")')
            self.assertEqual(mod.params, ())

    def test_mod_paramstyle(self):
        flavor = Flavor(paramstyle='format')
        Flavor.set(flavor)
        try:
            mod = Mod(self.table.c1, self.table.c2)
            self.assertEqual(str(mod), '("c1" %% "c2")')
            self.assertEqual(mod.params, ())
        finally:
            Flavor.set(Flavor())

        flavor = Flavor(paramstyle='qmark')
        Flavor.set(flavor)
        try:
            mod = Mod(self.table.c1, self.table.c2)
            self.assertEqual(str(mod), '("c1" % "c2")')
            self.assertEqual(mod.params, ())
        finally:
            Flavor.set(Flavor())

    def test_pow(self):
        for pow_ in [Pow(self.table.c1, self.table.c2),
                self.table.c1 ** self.table.c2]:
            self.assertEqual(str(pow_), '("c1" ^ "c2")')
            self.assertEqual(pow_.params, ())

    def test_abs(self):
        for abs_ in [Abs(self.table.c1), abs(self.table.c1)]:
            self.assertEqual(str(abs_), '(@ "c1")')
            self.assertEqual(abs_.params, ())

    def test_lshift(self):
        for lshift in [LShift(self.table.c1, 2),
                self.table.c1 << 2]:
            self.assertEqual(str(lshift), '("c1" << %s)')
            self.assertEqual(lshift.params, (2,))

    def test_rshift(self):
        for rshift in [RShift(self.table.c1, 2),
                self.table.c1 >> 2]:
            self.assertEqual(str(rshift), '("c1" >> %s)')
            self.assertEqual(rshift.params, (2,))

    def test_like(self):
        for like in [Like(self.table.c1, 'foo'),
                self.table.c1.like('foo'),
                ~NotLike(self.table.c1, 'foo'),
                ~~Like(self.table.c1, 'foo')]:
            self.assertEqual(str(like), '("c1" LIKE %s)')
            self.assertEqual(like.params, ('foo',))

    def test_ilike(self):
        flavor = Flavor(ilike=True)
        Flavor.set(flavor)
        try:
            for like in [ILike(self.table.c1, 'foo'),
                    self.table.c1.ilike('foo'),
                    ~NotILike(self.table.c1, 'foo')]:
                self.assertEqual(str(like), '("c1" ILIKE %s)')
                self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

        flavor = Flavor(ilike=False)
        Flavor.set(flavor)
        try:
            like = ILike(self.table.c1, 'foo')
            self.assertEqual(str(like), '("c1" LIKE %s)')
            self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

    def test_not_ilike(self):
        flavor = Flavor(ilike=True)
        Flavor.set(flavor)
        try:
            for like in [NotILike(self.table.c1, 'foo'),
                    ~self.table.c1.ilike('foo')]:
                self.assertEqual(str(like), '("c1" NOT ILIKE %s)')
                self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

        flavor = Flavor(ilike=False)
        Flavor.set(flavor)
        try:
            like = NotILike(self.table.c1, 'foo')
            self.assertEqual(str(like), '("c1" NOT LIKE %s)')
            self.assertEqual(like.params, ('foo',))
        finally:
            Flavor.set(Flavor())

    def test_in(self):
        for in_ in [In(self.table.c1, [self.table.c2, 1, Null]),
                ~NotIn(self.table.c1, [self.table.c2, 1, Null]),
                ~~In(self.table.c1, [self.table.c2, 1, Null])]:
            self.assertEqual(str(in_), '("c1" IN ("c2", %s, %s))')
            self.assertEqual(in_.params, (1, None))

        t2 = Table('t2')
        in_ = In(self.table.c1, t2.select(t2.c2))
        self.assertEqual(str(in_),
            '("c1" IN (SELECT "a"."c2" FROM "t2" AS "a"))')
        self.assertEqual(in_.params, ())

        in_ = In(self.table.c1, t2.select(t2.c2) | t2.select(t2.c3))
        self.assertEqual(str(in_),
            '("c1" IN (SELECT "a"."c2" FROM "t2" AS "a" '
            'UNION SELECT "a"."c3" FROM "t2" AS "a"))')
        self.assertEqual(in_.params, ())

        in_ = In(self.table.c1, array('l', range(10)))
        self.assertEqual(str(in_),
            '("c1" IN (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s))')
        self.assertEqual(in_.params, tuple(range(10)))

    def test_exists(self):
        exists = Exists(self.table.select(self.table.c1,
                where=self.table.c1 == 1))
        self.assertEqual(str(exists),
            '(EXISTS (SELECT "a"."c1" FROM "t" AS "a" '
            'WHERE ("a"."c1" = %s)))')
        self.assertEqual(exists.params, (1,))

    def test_floordiv(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            FloorDiv(4, 2)
            self.assertEqual(len(w), 1)
            self.assertTrue(issubclass(w[-1].category, DeprecationWarning))
            self.assertIn('FloorDiv operator is deprecated, use Div function',
                str(w[-1].message))
