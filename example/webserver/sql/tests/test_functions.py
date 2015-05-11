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

from sql import Table, Flavor
from sql.functions import (Function, FunctionKeyword, FunctionNotCallable, Abs,
    Overlay, Trim, AtTimeZone, Div, CurrentTime)


class TestFunctions(unittest.TestCase):
    table = Table('t')

    def test_abs(self):
        abs_ = Abs(self.table.c1)
        self.assertEqual(str(abs_), 'ABS("c1")')
        self.assertEqual(abs_.params, ())

        abs_ = Abs(-12)
        self.assertEqual(str(abs_), 'ABS(%s)')
        self.assertEqual(abs_.params, (-12,))

    def test_mapping(self):
        class MyAbs(Function):
            _function = 'MY_ABS'
            params = ('test',)

        class MyOverlay(FunctionKeyword):
            _function = 'MY_OVERLAY'
            _keywords = ('', 'PLACING', 'FROM', 'FOR')

        class MyCurrentTime(FunctionNotCallable):
            _function = 'MY_CURRENT_TIME'

        class MyTrim(Trim):
            _function = 'MY_TRIM'

        abs_ = Abs(self.table.c1)
        overlay = Overlay(self.table.c1, 'test', 2)
        current_time = CurrentTime()
        trim = Trim(' test ')
        flavor = Flavor(function_mapping={
                Abs: MyAbs,
                Overlay: MyOverlay,
                CurrentTime: MyCurrentTime,
                Trim: MyTrim,
                })
        Flavor.set(flavor)
        try:
            self.assertEqual(str(abs_), 'MY_ABS("c1")')
            self.assertEqual(abs_.params, ('test',))

            self.assertEqual(str(overlay),
                'MY_OVERLAY("c1" PLACING %s FROM %s)')
            self.assertEqual(overlay.params, ('test', 2))

            self.assertEqual(str(current_time), 'MY_CURRENT_TIME')
            self.assertEqual(current_time.params, ())

            self.assertEqual(str(trim), 'MY_TRIM(BOTH %s FROM %s)')
            self.assertEqual(trim.params, (' ', ' test ',))
        finally:
            Flavor.set(Flavor())

    def test_overlay(self):
        overlay = Overlay(self.table.c1, 'test', 3)
        self.assertEqual(str(overlay), 'OVERLAY("c1" PLACING %s FROM %s)')
        self.assertEqual(overlay.params, ('test', 3))
        overlay = Overlay(self.table.c1, 'test', 3, 7)
        self.assertEqual(str(overlay),
            'OVERLAY("c1" PLACING %s FROM %s FOR %s)')
        self.assertEqual(overlay.params, ('test', 3, 7))

    def test_trim(self):
        trim = Trim(' test ')
        self.assertEqual(str(trim), 'TRIM(BOTH %s FROM %s)')
        self.assertEqual(trim.params, (' ', ' test ',))

        trim = Trim(self.table.c1)
        self.assertEqual(str(trim), 'TRIM(BOTH %s FROM "c1")')
        self.assertEqual(trim.params, (' ',))

    def test_at_time_zone(self):
        time_zone = AtTimeZone(self.table.c1, 'UTC')
        self.assertEqual(str(time_zone), '"c1" AT TIME ZONE %s')
        self.assertEqual(time_zone.params, ('UTC',))

    def test_at_time_zone_mapping(self):
        class MyAtTimeZone(Function):
            _function = 'MY_TIMEZONE'

        time_zone = AtTimeZone(self.table.c1, 'UTC')
        flavor = Flavor(function_mapping={
                AtTimeZone: MyAtTimeZone,
                })
        Flavor.set(flavor)
        try:
            self.assertEqual(str(time_zone), 'MY_TIMEZONE("c1", %s)')
            self.assertEqual(time_zone.params, ('UTC',))
        finally:
            Flavor.set(Flavor())

    def test_div(self):
        for div in [Div(self.table.c1, self.table.c2),
                self.table.c1 // self.table.c2]:
            self.assertEqual(str(div), 'DIV("c1", "c2")')
            self.assertEqual(div.params, ())

    def test_current_time(self):
        current_time = CurrentTime()
        self.assertEqual(str(current_time), 'CURRENT_TIME')
        self.assertEqual(current_time.params, ())
