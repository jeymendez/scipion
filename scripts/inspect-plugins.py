#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *
# * [1] SciLifeLab, Stockholm University
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

from __future__ import print_function
import sys
import importlib
import traceback

from pyworkflow.em import Domain
import pyworkflow.utils as pwutils


def usage(error):
    print("""
    ERROR: %s

    Usage: scipion python scripts/inspect-plugins.py [PLUGIN-NAME]
        This script loads all Scipion plugins found.
        If a PLUGIN-NAME is passed, it will inspect that plugin
        in more detail.
    """ % error)
    sys.exit(1)


def getSubmodule(name, subname):
    """ Return a tuple: (module, error)
    If module is None:
        1) if error is None is that the submodule does not exist
        2) if error is not None, it is an Exception raised when
        importing the submodule
    """
    try:
        m = importlib.import_module('%s.%s' % (name, subname))
        r = (m, None)
    except Exception as e:
        noModuleMsg = 'No module named %s' % subname
        msg = str(e)
        r = (None, None if msg == noModuleMsg else traceback.format_exc())
    return r

n = len(sys.argv)

if n > 2:
    usage("Incorrect number of input parameters")

if n == 1:  # List all plugins
    plugins = Domain.getPlugins()
    print("Plugins:")
    for k, v in plugins.iteritems():
        print("-", k)


    print("Objects")
    pwutils.prettyDict(Domain.getObjects())

    print("Protocols")
    pwutils.prettyDict(Domain.getProtocols())

    print("Viewers")
    pwutils.prettyDict(Domain.getViewers())


else:
    pluginName = sys.argv[1]
    plugin = Domain.getPlugin(pluginName)
    print("Plugin: %s" % pluginName)
    for subName in ['constants', 'convert', 'protocols',
                    'wizards', 'viewers', 'tests']:
        sub, error = getSubmodule(pluginName, subName)

        if sub is None:
            if error is None:
                msg = " missing"
            else:
                msg = " error -> %s" % error

        else:
            msg = " loaded"

        print("   >>> %s: %s" % (subName, msg))




