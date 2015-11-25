import os
import sys
from datetime import datetime
from trac.core import *
from bitten.main import BuildSystem
from bitten.model import Build, BuildConfig
try:
    from tracrpc.api import IXMLRPCHandler, expose_rpc, Binary
    from tracrpc.util import StringIO, to_utimestamp, from_utimestamp
except ImportError:
    pass

class BittenRPC(Component):
    """XML RPC API for Bitten
    """

    try:
        # if XMLRPCPlugin is not available, do not register as an XML RPC responder
        implements(IXMLRPCHandler)
    except:
        pass

    def __init__(self):
        self.bitten = BuildSystem

    def xmlrpc_namespace(self):
        return 'build'

    def xmlrpc_methods(self):
        yield ('BUILD_VIEW', ((list, str, str, str, str, str),), self.getBuilds)
        yield ('BUILD_VIEW', ((list, str, str, str, str, str),), self.getBuildIds)
        yield ('BUILD_VIEW', ((list, bool),), self.getConfigurations)
        yield ('BUILD_DELETE', ((bool, int),), self.deleteBuild)

    def getBuilds(self, req, config=None, rev=None, platform=None, slave=None, status=None):
        """Retrieve a list of builds that match the selected criteria, with all build properties
        """
        builds = []
        for build in Build.select(self.env, config=config or None, rev=rev or None,
                                  platform=platform or None, slave=slave or None,
                                  status=status or None):
            if not build:
                continue
            builds.append({
                'id': build.id,
                'config': build.config,
                'rev': build.rev,
                'platform': build.platform,
                'slave': build.slave,
                'started': build.started,
                'stopped': build.stopped,
                'last_activity': build.last_activity,
                'rev_time': build.rev_time,
                'status': build.status,
            })
        return builds

    def getBuildIds(self, req, config=None, rev=None, platform=None, slave=None, status=None):
        """Retrieve a list of build unique identifiers that match the selected criteria
        """
        return [build.id for build in Build.select(self.env, config=config or None,
                    rev=rev or None, platform=platform or None, slave=slave or None,
                    status=status or None) if build]

    def deleteBuild(self, req, id_):
        """Delete a build referenced from its unique ID
        """
        try:
            build = Build.fetch(self.env, id_)
            build.delete()
            return True
        except Exception:
            return False

    def getConfigurations(self, req, include_inactive=False):
        """Retrieve a list of available configurations
        """
        configs = []
        for config in BuildConfig.select(self.env, include_inactive=include_inactive):
            if not config:
                continue
            configs.append({
                'name': config.name,
                'path': config.path,
                'active': config.active,
                'recipe': config.recipe,
                'min_rev': config.min_rev,
                'max_rev': config.max_rev,
                'label': config.label,
                'description': config.description,
            })
        return configs
