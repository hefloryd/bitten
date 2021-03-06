# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import os
import shutil
import tempfile
import unittest

from bitten.build import ctools
from bitten.build.tests import dummy
from bitten.recipe import Context, Recipe


class CppUnitTestCase(unittest.TestCase):

    def setUp(self):
        self.basedir = os.path.realpath(tempfile.mkdtemp())
        self.ctxt = Context(self.basedir)

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def test_missing_param_file(self):
        self.assertRaises(AssertionError, ctools.cppunit, self.ctxt)

    def test_empty_summary(self):
        cppunit_xml = file(self.ctxt.resolve('cppunit.xml'), 'w')
        cppunit_xml.write("""<?xml version="1.0" encoding='utf-8' ?>
<TestRun>
  <FailedTests>
    <FailedTest id="2">
      <Name>HelloTest::secondTest</Name>
      <FailureType>Assertion</FailureType>
      <Location>
        <File>HelloTest.cxx</File>
        <Line>95</Line>
      </Location>
      <Message>assertion failed
- Expression: 2 == 3
</Message>
    </FailedTest>
  </FailedTests>
  <SuccessfulTests>
    <Test id="1">
      <Name>HelloTest::firstTest</Name>
    </Test>
    <Test id="3">
      <Name>HelloTest::thirdTest</Name>
    </Test>
  </SuccessfulTests>
  <Statistics>
    <Tests>3</Tests>
    <FailuresTotal>1</FailuresTotal>
    <Errors>0</Errors>
    <Failures>1</Failures>
  </Statistics>
</TestRun>""")
        cppunit_xml.close()
        ctools.cppunit(self.ctxt, file_='cppunit.xml')
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual(Recipe.REPORT, type)
        self.assertEqual('test', category)

        tests = list(xml.children)
        self.assertEqual(3, len(tests))
        self.assertEqual('HelloTest', tests[0].attr['fixture'])
        self.assertEqual('secondTest', tests[0].attr['name'])
        self.assertEqual('failure', tests[0].attr['status'])
        self.assertEqual('HelloTest.cxx', tests[0].attr['file'])
        self.assertEqual('95', tests[0].attr['line'])

        self.assertEqual('HelloTest', tests[1].attr['fixture'])
        self.assertEqual('firstTest', tests[1].attr['name'])
        self.assertEqual('success', tests[1].attr['status'])

        self.assertEqual('HelloTest', tests[2].attr['fixture'])
        self.assertEqual('thirdTest', tests[2].attr['name'])
        self.assertEqual('success', tests[2].attr['status'])


class GCovTestCase(unittest.TestCase):

    def setUp(self):
        self.basedir = os.path.realpath(tempfile.mkdtemp())
        self.ctxt = Context(self.basedir)

    def tearDown(self):
        shutil.rmtree(self.basedir)

    def _create_file(self, *path, **kwargs):
        filename = os.path.join(self.basedir, *path)
        dirname = os.path.dirname(filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        fd = file(filename, 'w')
        if 'content' in kwargs:
            fd.write(kwargs['content'])
        fd.close()
        return filename[len(self.basedir) + 1:]

    def test_no_file(self):
        ctools.CommandLine = dummy.CommandLine()
        ctools.gcov(self.ctxt)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('log', type)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(0, len(xml.children))

    def test_single_file(self):
        self._create_file('foo.c')
        self._create_file('foo.o')
        self._create_file('foo.gcno')
        self._create_file('foo.gcda')

        ctools.CommandLine = dummy.CommandLine(stdout="""
File `foo.c'
Lines executed:45.81% of 884
Branches executed:54.27% of 398
Taken at least once:36.68% of 398
Calls executed:48.19% of 249

File `foo.h'
Lines executed:50.00% of 4
No branches
Calls executed:100.00% of 1
""")
        ctools.gcov(self.ctxt)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('log', type)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(1, len(xml.children))
        elem = xml.children[0]
        self.assertEqual('coverage', elem.name)
        self.assertEqual('foo.c', elem.attr['file'])
        self.assertEqual('foo.c', elem.attr['name'])
        self.assertEqual(888, elem.attr['lines'])
        self.assertEqual(45, elem.attr['percentage'])
        
    def test_unreached_exceptional_path_is_zero(self):
        self._create_file('foo.cpp')
        self._create_file('foo.o')
        self._create_file('foo.gcno')
        self._create_file('foo.gcda')
        self._create_file('foo.cpp.gcov', content="""        -:    0:Source:foo.cpp
        -:    0:Graph:./foo.gcno
        -:    0:Data:./foo.gcda
        -:    0:Runs:1
        -:    0:Programs:1
        -:    1:#include <iostream>
        -:    2:
        1:    3:int main() {
        -:    4:    try {
        1:    5:        std::cout << "No exception!";
    =====:    6:    } catch(const std::exception &) {
    =====:    7:        std::cout << "Exception!";
        -:    8:    }
        4:    9:}
""")
        ctools.CommandLine = dummy.CommandLine(stdout="""
File 'foo.cpp'
Lines executed:60.00% of 5
Creating 'foo.cpp.gcov'

File '/usr/include/c++/4.9.1/iostream'
Lines executed:100.00% of 1
Creating 'iostream.gcov'

File '/usr/include/c++/4.9.1/bits/basic_ios.h'
No executable lines
Removing 'basic_ios.h.gcov'

File '/usr/include/c++/4.9.1/ostream'
No executable lines
Removing 'ostream.gcov'

File '/usr/include/c++/4.9.1/bits/ios_base.h'
Lines executed:0.00% of 2
Creating 'ios_base.h.gcov'

File '/usr/include/c++/4.9.1/bits/char_traits.h'
Lines executed:0.00% of 2
Creating 'char_traits.h.gcov'
""")
        ctools.gcov(self.ctxt)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('log', type)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(1, len(xml.children))
        elem = xml.children[0]
        self.assertEqual('coverage', elem.name)
        self.assertEqual('- - 1 - 1 0 0 - 4', elem.attr['line_hits'])
        
    def test_mark_unknown_lines(self):
        self._create_file('foo.cpp')
        self._create_file('foo.o')
        self._create_file('foo.gcno')
        self._create_file('foo.gcda')
        # changed line 2 to include unknown text
        self._create_file('foo.cpp.gcov', content="""        -:    0:Source:foo.cpp
        -:    0:Graph:./foo.gcno
        -:    0:Data:./foo.gcda
        -:    0:Runs:1
        -:    0:Programs:1
        -:    1:#include <iostream>
        x:    2:
        1:    3:int main() {
        -:    4:    try {
        1:    5:        std::cout << "No exception!";
    =====:    6:    } catch(const std::exception &) {
    =====:    7:        std::cout << "Exception!";
        -:    8:    }
        4:    9:}
""")
        ctools.CommandLine = dummy.CommandLine(stdout="""
File 'foo.cpp'
Lines executed:60.00% of 5
Creating 'foo.cpp.gcov'

File '/usr/include/c++/4.9.1/iostream'
Lines executed:100.00% of 1
Creating 'iostream.gcov'

File '/usr/include/c++/4.9.1/bits/basic_ios.h'
No executable lines
Removing 'basic_ios.h.gcov'

File '/usr/include/c++/4.9.1/ostream'
No executable lines
Removing 'ostream.gcov'

File '/usr/include/c++/4.9.1/bits/ios_base.h'
Lines executed:0.00% of 2
Creating 'ios_base.h.gcov'

File '/usr/include/c++/4.9.1/bits/char_traits.h'
Lines executed:0.00% of 2
Creating 'char_traits.h.gcov'
""")
        ctools.gcov(self.ctxt)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('log', type)
        type, category, generator, xml = self.ctxt.output.pop()
        self.assertEqual('report', type)
        self.assertEqual('coverage', category)
        self.assertEqual(1, len(xml.children))
        elem = xml.children[0]
        self.assertEqual('coverage', elem.name)
        self.assertEqual('- ??? 1 - 1 0 0 - 4', elem.attr['line_hits'])

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(CppUnitTestCase, 'test'))
    suite.addTest(unittest.makeSuite(GCovTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
