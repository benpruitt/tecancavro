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
import threading

from sql import AliasManager, Table


class TestAliasManager(unittest.TestCase):

    def setUp(self):
        self.synchro = threading.Event()
        self.succeed1 = threading.Event()
        self.succeed2 = threading.Event()
        self.finish1 = threading.Event()
        self.finish2 = threading.Event()

        self.t1 = Table('t1')
        self.t2 = Table('t2')

    def func1(self):
        try:
            with AliasManager():
                a1 = AliasManager.get(self.t1)
                a2 = AliasManager.get(self.t2)
                self.synchro.wait()
                self.assertEqual(a1, AliasManager.get(self.t1))
                self.assertEqual(a2, AliasManager.get(self.t2))
                self.succeed1.set()
            return
        except Exception:
            pass
        finally:
            self.finish1.set()

    def func2(self):
        try:
            with AliasManager():
                a2 = AliasManager.get(self.t2)
                a1 = AliasManager.get(self.t1)
                self.synchro.set()
                self.assertEqual(a1, AliasManager.get(self.t1))
                self.assertEqual(a2, AliasManager.get(self.t2))
                self.succeed2.set()
            return
        except Exception:
            pass
        finally:
            self.synchro.set()
            self.finish2.set()

    def test_threading(self):

        th1 = threading.Thread(target=self.func1)
        th2 = threading.Thread(target=self.func2)

        th1.start()
        th2.start()

        self.finish1.wait()
        self.finish2.wait()
        if not self.succeed1.is_set() or not self.succeed2.is_set():
            self.fail()
