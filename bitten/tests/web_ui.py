# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://bitten.edgewall.org/wiki/License.

import shutil
import tempfile
import unittest

from trac.core import TracError
from trac.db import DatabaseManager
from trac.perm import PermissionCache, PermissionSystem
from trac.resource import Resource
from trac.test import EnvironmentStub, Mock
from trac.util.html import Markup
from trac.web.api import HTTPNotFound
from trac.web.href import Href
from bitten.main import BuildSystem
from bitten.model import Build, BuildConfig, BuildStep, TargetPlatform, schema
from bitten.web_ui import BuildConfigController, BuildController, \
                          SourceFileLinkFormatter


class AbstractWebUITestCase(unittest.TestCase):

    def setUp(self):
        self.env = EnvironmentStub(enable=['trac.*', 'bitten.*'])
        self.env.path = tempfile.mkdtemp()

        # Create tables
        db = self.env.get_db_cnx()
        cursor = db.cursor()
        connector, _ = DatabaseManager(self.env)._get_connector()
        for table in schema:
            for stmt in connector.to_sql(table):
                cursor.execute(stmt)

        # Set up permissions
        self.env.config.set('trac', 'permission_store',
                            'DefaultPermissionStore')

        # Hook up a dummy repository
        self.repos = Mock(
            get_node=lambda path, rev=None: Mock(get_history=lambda: [],
                                                 isdir=True),
            normalize_path=lambda path: path,
            normalize_rev=lambda rev: rev,
            sync=lambda: None,
            resource=Resource('repository', None),
            authz = Mock(has_permission=lambda path: True,
                         assert_permission=lambda path: None))
        self.env.get_repository = lambda authname=None: self.repos # 0.11
        try: # 0.12+
            from trac.core import Component, implements
            from trac.versioncontrol.api import IRepositoryConnector, \
                                                IRepositoryProvider
            class DummyRepos(Component):
                implements(IRepositoryConnector, IRepositoryProvider)
                def get_supported_types(self):
                    yield ('dummy', 9)
                def get_repository(this, repos_type, repos_dir, params):
                    return self.repos # Note: 'this' vs 'self' usage
                def get_repositories(self):
                    yield ('', {'dir': 'dummy_dir', 'type': 'dummy'})
            self.dummy = DummyRepos
        except ImportError:
            self.dummy = None # not supported, will use get_repository()

    def tearDown(self):
        if self.dummy: # remove from components list + interfaces dict
            self.env.__metaclass__._components.remove(self.dummy)
            for key in self.env.__metaclass__._registry.keys():
                if self.dummy in self.env.__metaclass__._registry[key]:
                    self.env.__metaclass__._registry[key].remove(self.dummy)
        shutil.rmtree(self.env.path)


class BuildConfigControllerTestCase(AbstractWebUITestCase):

    def test_overview(self):
        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build', href=Href('/trac'), args={}, chrome={},
                   perm=PermissionCache(self.env, 'joe'), authname='joe')

        module = BuildConfigController(self.env)
        assert module.match_request(req)
        _, data, _ = module.process_request(req)

        self.assertEqual('overview', data['page_mode'])

    def test_view_config(self):
        config = BuildConfig(self.env, name='test', path='trunk')
        config.insert()
        platform = TargetPlatform(self.env, config='test', name='any')
        platform.insert()

        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build/test', href=Href('/trac'), args={},
                   chrome={}, authname='joe',
                   perm=PermissionCache(self.env, 'joe'))

        root = Mock(get_entries=lambda: ['foo'],
                    get_history=lambda: [('trunk', rev, 'edit') for rev in
                                          range(123, 111, -1)])
        self.repos.get_node=lambda path, rev=None: root
        self.repos.youngest_rev=123
        self.repos.get_changeset=lambda rev: Mock(author='joe', date=99)

        module = BuildConfigController(self.env)
        assert module.match_request(req)
        _, data, _ = module.process_request(req)

        self.assertEqual('view_config', data['page_mode'])
        assert not 'next' in req.chrome['links']

        self.assertEquals(Resource('build', 'test'), data['context'].resource)

        self.assertEquals([], data['config']['attachments']['attachments'])
        self.assertEquals('/trac/attachment/build/test/',
                                data['config']['attachments']['attach_href'])

    def test_bitten_keeps_order_of_revisions_from_versioncontrol(self):
        # Trac's API specifies that they are sorted chronological (backwards)
        # We must not assume that these revision numbers can be sorted later on,
        # for example the mercurial plugin will return the revisions as strings
        # (e.g. '880:4c19fa95fb9e')
        config = BuildConfig(self.env, name='test', path='trunk')
        config.insert()
        platform = TargetPlatform(self.env, config='test', name='any')
        platform.insert()

        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build/'+config.name, href=Href('/trac'), args={},
                   chrome={}, authname='joe',
                   perm=PermissionCache(self.env, 'joe'))

        # revisions are intentionally not sorted in any way - bitten should just keep them!
        revision_ids = [5, 8, 2]
        revision_list = [('trunk', revision, 'edit') for revision in revision_ids]
        root = Mock(get_entries=lambda: ['foo'], get_history=lambda: revision_list)
        self.repos.get_node=lambda path, rev=None: root
        self.repos.youngest_rev=5
        self.repos.get_changeset=lambda rev: Mock(author='joe', date=99)

        module = BuildConfigController(self.env)
        assert module.match_request(req)
        _, data, _ = module.process_request(req)

        actual_revision_ids = data['config']['revisions']
        self.assertEquals(revision_ids, actual_revision_ids)

    def test_view_config_paging(self):
        config = BuildConfig(self.env, name='test', path='trunk')
        config.insert()
        platform = TargetPlatform(self.env, config='test', name='any')
        platform.insert()

        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build/test', href=Href('/trac'), args={},
                   chrome={}, authname='joe',
                   perm=PermissionCache(self.env, 'joe'))

        root = Mock(get_entries=lambda: ['foo'],
                    get_history=lambda: [('trunk', rev, 'edit') for rev in
                                          range(123, 110, -1)])
        self.repos.get_node=lambda path, rev=None: root
        self.repos.youngest_rev=123
        self.repos.get_changeset=lambda rev: Mock(author='joe', date=99)

        module = BuildConfigController(self.env)
        assert module.match_request(req)
        _, data, _ = module.process_request(req)

        if req.chrome:
            self.assertEqual('/trac/build/test?page=2',
                             req.chrome['links']['next'][0]['href'])

    def test_raise_404(self):
        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        module = BuildConfigController(self.env)
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build/nonexisting', href=Href('/trac'), args={},
                   chrome={}, authname='joe',
                   perm=PermissionCache(self.env, 'joe'))
        self.failUnless(module.match_request(req))
        try:
            module.process_request(req)
        except Exception, e:
            self.failUnless(isinstance(e, HTTPNotFound))
            self.assertEquals(str(e), "404 Not Found (Build configuration "
                                      "'nonexisting' does not exist.)")
            return
        self.fail("This should have raised HTTPNotFound")


class BuildControllerTestCase(AbstractWebUITestCase):

    def test_view_build(self):
        config = BuildConfig(self.env, name='test', path='trunk')
        config.insert()
        platform = TargetPlatform(self.env, config='test', name='any')
        platform.insert()
        build = Build(self.env, config='test', platform=1, rev=123, rev_time=42,
                      status=Build.SUCCESS, slave='hal')
        build.insert()

        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build/test/1', href=Href('/trac'), args={},
                   chrome={}, authname='joe',
                   perm=PermissionCache(self.env, 'joe'))

        root = Mock(get_entries=lambda: ['foo'],
                    get_history=lambda: [('trunk', rev, 'edit') for rev in
                                          range(123, 111, -1)])
        self.repos.get_node=lambda path, rev=None: root
        self.repos.get_changeset=lambda rev: Mock(author='joe')

        module = BuildController(self.env)
        assert module.match_request(req)
        _, data, _ = module.process_request(req)

        self.assertEqual('view_build', data['page_mode'])

        self.assertEquals(Resource('build', 'test/1'), data['context'].resource)

        self.assertEquals([], data['build']['attachments']['attachments'])
        self.assertEquals('/trac/attachment/build/test/1/',
                                data['build']['attachments']['attach_href'])

    def test_raise_404(self):
        PermissionSystem(self.env).grant_permission('joe', 'BUILD_VIEW')
        module = BuildController(self.env)
        config = BuildConfig(self.env, name='existing', path='trunk')
        config.insert()
        req = Mock(method='GET', base_path='', cgi_location='',
                   path_info='/build/existing/42', href=Href('/trac'), args={},
                   chrome={}, authname='joe',
                   perm=PermissionCache(self.env, 'joe'))
        self.failUnless(module.match_request(req))
        try:
            module.process_request(req)
        except Exception, e:
            self.failUnless(isinstance(e, HTTPNotFound))
            self.assertEquals(str(e),
                    "404 Not Found (Build '42' does not exist.)")
            return
        self.fail("This should have raised HTTPNotFound")


class SourceFileLinkFormatterTestCase(AbstractWebUITestCase):

    def test_format_simple_link_in_repos(self):
        BuildConfig(self.env, name='test', path='trunk').insert()
        build = Build(self.env, config='test', platform=1, rev=123, rev_time=42,
                      status=Build.SUCCESS, slave='hal')
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()

        self.repos.get_node = lambda path, rev: (path, rev)

        req = Mock(method='GET', href=Href('/trac'), authname='hal')
        comp = SourceFileLinkFormatter(self.env)
        formatter = comp.get_formatter(req, build)

        # posix
        output = formatter(step, None, None, u'error in foo/bar.c: bad')
        self.assertEqual(Markup, type(output))
        self.assertEqual('error in <a href="/trac/browser/trunk/foo/bar.c">'
                         'foo/bar.c</a>: bad', output)
        # windows
        output = formatter(step, None, None, u'error in foo\\win.c: bad')
        self.assertEqual(Markup, type(output))
        self.assertEqual(r'error in <a href="/trac/browser/trunk/foo/win.c">'
                         'foo\win.c</a>: bad', output)

    def test_format_bad_links(self):
        BuildConfig(self.env, name='test', path='trunk').insert()
        build = Build(self.env, config='test', platform=1, rev=123, rev_time=42,
                      status=Build.SUCCESS, slave='hal')
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()

        self.repos.get_node = lambda path, rev: (path, rev)

        req = Mock(method='GET', href=Href('/trac'), authname='hal')
        comp = SourceFileLinkFormatter(self.env)
        formatter = comp.get_formatter(req, build)

        output = formatter(step, None, None, u'Linking -I../.. with ../libtool')
        self.assertEqual(Markup, type(output))
        self.assertEqual('Linking -I../.. with ../libtool', output)

    def test_format_simple_link_not_in_repos(self):
        BuildConfig(self.env, name='test', path='trunk').insert()
        build = Build(self.env, config='test', platform=1, rev=123, rev_time=42,
                      status=Build.SUCCESS, slave='hal')
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()

        def _raise():
            raise TracError('No such node')
        self.repos.get_node = lambda path, rev: _raise()

        req = Mock(method='GET', href=Href('/trac'), authname='hal')
        comp = SourceFileLinkFormatter(self.env)
        formatter = comp.get_formatter(req, build)

        output = formatter(step, None, None, u'error in foo/bar.c: bad')
        self.assertEqual(Markup, type(output))
        self.assertEqual('error in foo/bar.c: bad', output)

    def test_format_link_in_repos_with_line(self):
        BuildConfig(self.env, name='test', path='trunk').insert()
        build = Build(self.env, config='test', platform=1, rev=123, rev_time=42,
                      status=Build.SUCCESS, slave='hal')
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()

        self.repos.get_node = lambda path, rev: (path, rev)

        req = Mock(method='GET', href=Href('/trac'), authname='hal')
        comp = SourceFileLinkFormatter(self.env)
        formatter = comp.get_formatter(req, build)

        # posix
        output = formatter(step, None, None, u'error in foo/bar.c:123: bad')
        self.assertEqual(Markup, type(output))
        self.assertEqual('error in <a href="/trac/browser/trunk/foo/bar.c#L123">'
                         'foo/bar.c:123</a>: bad', output)
        # windows
        output = formatter(step, None, None, u'error in foo\\win.c:123: bad')
        self.assertEqual(Markup, type(output))
        self.assertEqual(r'error in <a href="/trac/browser/trunk/foo/win.c#L123">'
                         'foo\win.c:123</a>: bad', output)

    def test_format_link_not_in_repos_with_line(self):
        BuildConfig(self.env, name='test', path='trunk').insert()
        build = Build(self.env, config='test', platform=1, rev=123, rev_time=42,
                      status=Build.SUCCESS, slave='hal')
        build.insert()
        step = BuildStep(self.env, build=build.id, name='foo',
                         status=BuildStep.SUCCESS)
        step.insert()

        def _raise():
            raise TracError('No such node')
        self.repos.get_node = lambda path, rev: _raise()

        req = Mock(method='GET', href=Href('/trac'), authname='hal')
        comp = SourceFileLinkFormatter(self.env)
        formatter = comp.get_formatter(req, build)

        output = formatter(step, None, None, u'error in foo/bar.c:123: bad')
        self.assertEqual(Markup, type(output))
        self.assertEqual('error in foo/bar.c:123: bad', output)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BuildConfigControllerTestCase, 'test'))
    suite.addTest(unittest.makeSuite(BuildControllerTestCase, 'test'))
    suite.addTest(unittest.makeSuite(SourceFileLinkFormatterTestCase, 'test'))
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
