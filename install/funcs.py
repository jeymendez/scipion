# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
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
# *  e-mail address 'xmipp@cnb.csic.es'
# *
# **************************************************************************

import platform
import os
import sys
import time
from glob import glob

from subprocess import STDOUT, check_call, CalledProcessError


# Then we get some OS vars
MACOSX = (platform.system() == 'Darwin')
WINDOWS = (platform.system() == 'Windows')
LINUX = (platform.system() == 'Linux')

SCIPION_URL_SOFTWARE = os.environ['SCIPION_URL_SOFTWARE']


def ansi(n):
    "Return function that escapes text with ANSI color n."
    return lambda txt: '\x1b[%dm%s\x1b[0m' % (n, txt)

black, red, green, yellow, blue, magenta, cyan, white = map(ansi, range(30, 38))



def progInPath(prog):
    """ Is program prog in PATH? """
    for base in os.environ.get('PATH', '').split(os.pathsep):
        if os.path.exists('%s/%s' % (base, prog)):
            return True
    return False


def checkLib(lib, target=None):
    """ See if we have library lib """
    try:
        check_call(['pkg-config', '--cflags', '--libs', lib],
                   stdout=open(os.devnull, 'w'), stderr=STDOUT)
    except (CalledProcessError, OSError) as e:
        try:
            check_call(['%s-config' % lib, '--cflags'])
        except (CalledProcessError, OSError) as e:
            print """
  ************************************************************************
    Warning: %s not found. Please consider installing it first.
  ************************************************************************

Continue anyway? (y/n)""" % lib
            if raw_input().upper() != 'Y':
                sys.exit(2)
    # TODO: maybe write the result of the check in
    # software/log/lib_...log so we don't check again if we already said "no"



class Command():
    def __init__(self, env, cmd, targets=None,  **kwargs):
        self._env = env
        self._cmd = cmd

        if targets is None:
            self._targets = []
        elif isinstance(targets, basestring):
            self._targets = [targets]
        else:
            self._targets = targets

        self._cwd = kwargs.get('cwd', None)
        self._out = kwargs.get('out', None)
        self._always = kwargs.get('always', False)

    def _existsAll(self):
        """ Return True if all targets exist. """
        for t in self._targets:
            if not glob(t):
                return False
        return True

    def execute(self):
        if not self._always and self._targets and self._existsAll():
            print("  Skipping command: %s" % cyan(self._cmd))
            print("  All targets exist.")
        else:
            cwd = os.getcwd()
            if self._cwd is not None:
                if not self._env.showOnly:
                    os.chdir(self._cwd)
                print(cyan("cd %s" % self._cwd))

            cmd = self._cmd
            if self._out is not None:
                cmd += ' > %s 2>&1' % self._out
                # TODO: more general, this only works for bash.
            print(cyan(cmd))
            if not self._env.showOnly:
                # self._cmd could be a function, in which case just call it
                if callable(self._cmd):
                    self._cmd()
                else: # if not, we assume is a command and we make a system call
                    os.system(cmd)
            # Return to working directory, useful
            # when changing dir before executing command
            os.chdir(cwd)
            if not self._env.showOnly:
                for t in self._targets:
                    assert glob(t), ("target '%s' not built (after "
                                     "running '%s')" % (t, cmd))

    def __str__(self):
        return "Command: %s, targets: %s" % (self._cmd, self._targets)


class Target():
    def __init__(self, env, name, *commands, **kwargs):
        self._env = env
        self._name = name
        self._default = kwargs.get('default', False)
        self._commandList = list(commands[:])
        self._deps = [] # list of name of dependency targets

    def addCommand(self, cmd, **kwargs):
        if isinstance(cmd, Command):
            c = cmd
        else:
            c = Command(self._env, cmd, **kwargs)
        self._commandList.append(c)
        return c

    def addDep(self, dep):
        self._deps.append(dep)

    def getDeps(self):
        return self._deps

    def _existsAll(self):
        for command in self._commandList:
            if not command._existsAll():
                return False
        return True

    def isDefault(self):
        return self._default

    def getName(self):
        return self._name

    def execute(self):
        t1 = time.time()

        print(green("Building %s ..." % self._name))
        if self._existsAll():
            print("  All targets exist, skipping.")
        else:
            for command in self._commandList:
                command.execute()

        if not self._env.showOnly:
            dt = time.time() - t1
            if dt < 60:
                print(green('Done (%.2f seconds)' % dt))
            else:
                print(green('Done (%d m %02d s)' % (dt / 60, int(dt) % 60)))

    def __str__(self):
        return self._name


class Environment():

    def __init__(self, **kwargs):
        self._targetList = []
        self._targetDict = {}
        self._args = kwargs.get('args', [])
        self.showOnly = '--show' in self._args
        
        # Find if the -j arguments was passed to grap the number of processors
        if '-j' in self._args:
            j = self._args.index('-j')
            self._processors = int(self._args[j+1])
        else:
            self._processors = 1
            
        if LINUX:
            self._libSuffix = 'so' # Shared libraries extension name
        else:
            self._libSuffix = 'dylib'

        self._downloadCmd = 'wget -nv -c -O %s %s'
        self._tarCmd = 'tar --recursive-unlink -xzf %s'

    def getLibSuffix(self):
        return self._libSuffix
    
    def getProcessors(self):
        return self._processors
    
    def getLib(self, name):
        return 'software/lib/lib%s.%s' % (name, self._libSuffix)

    def getBin(self, name):
        return 'software/bin/%s' % name
    
    def getEm(self, name):
        return 'software/em/%s' % name

    def addTarget(self, name, *commands, **kwargs):

        if name in self._targetDict:
            raise Exception("Duplicated target '%s'" % name)

        t = Target(self, name, *commands, **kwargs)
        self._targetList.append(t)
        self._targetDict[name] = t

        return t
    
    def getTarget(self, name):
        return self._targetDict[name]
    
    def hasTarget(self, name):
        return name in self._targetDict
    
    def getTargets(self):
        return self._targetList

    def _addTargetDeps(self, target, deps):
        """ Add the dependencies to target.
        Check that each dependency correspond to a previous target.
        """
        for d in deps:
            if isinstance(d, str):
                targetName = d
            elif isinstance(d, Target):
                targetName = d.getName()
            else:
                raise Exception("Dependencies should be either string or Target, received: %s" % d)

            if targetName not in self._targetDict:
                raise Exception("Dependency '%s' does not exists. " % targetName)

            target.addDep(targetName)

    def _addDownloadUntar(self, name, **kwargs):
        """ Buid a basic target and add commands for Download and Untar.
        This is the base for addLibrary, addModule and addPackage.
        """
        # Use reasonable defaults.
        tar = kwargs.get('tar', '%s.tgz' % name)
        urlSuffix = kwargs.get('urlSuffix', 'external')
        url = kwargs.get('url', '%s/%s/%s' % (SCIPION_URL_SOFTWARE, urlSuffix, tar))
        downloadDir = kwargs.get('downloadDir', 
                                 os.path.join('software', 'tmp'))
        buildDir = kwargs.get('buildDir',
                              tar.rsplit('.tar.gz', 1)[0].rsplit('.tgz', 1)[0])
        deps = kwargs.get('deps', [])
        
        # Download library tgz
        tarFile = os.path.join(downloadDir, tar)
        buildPath = os.path.join(downloadDir, buildDir)
        
        t = self.addTarget(name, default=kwargs.get('default', True))
        self._addTargetDeps(t, deps)
        t.buildDir = buildDir
        t.buildPath = buildPath

        t.addCommand(self._downloadCmd % (tarFile, url),
                     targets=tarFile)
        t.addCommand(self._tarCmd % tar,
                     targets=buildPath,
                     cwd=downloadDir)
        
        return t          
         
    def addLibrary(self, name, **kwargs):
        """Add library <name> to the construction process.

        This pseudobuilder checks that the needed programs are in PATH,
        downloads the given url, untars the resulting tar file, configures
        the library with the given flags, compiles it (in the given
        buildDir) and installs it. It also tells SCons about the proper
        dependencies (deps).

        If default=False, the library will not be built.

        Returns the final targets, the ones that Make will create.

        """
        configTarget = kwargs.get('configTarget', 'Makefile')
        configAlways = kwargs.get('configAlways', False)
        flags = kwargs.get('flags', [])
        targets = kwargs.get('targets', [self.getLib(name)])
        clean = kwargs.get('clean', False) # Execute make clean at the end??
        cmake = kwargs.get('cmake', False) # Use cmake instead of configure??

        # If passing a command list (of tuples (command, target)) those actions
        # will be performed instead of the normal ./configure / cmake + make
        commands = kwargs.get('commands', []) 

        t = self._addDownloadUntar(name, **kwargs)
        configDir = kwargs.get('configDir', t.buildDir)

        configPath = os.path.join('software/tmp', configDir)
        makeFile = '%s/%s' % (configPath, configTarget)
        prefixPath = os.path.abspath('software')

        # If we specified the commands to run to obtain the target,
        # that's the only thing we will do.
        if commands:
            for cmd, tgt in commands:
                t.addCommand(cmd, targets=tgt)
            return t

        # If we didnt' specify the commands, we can either compile
        # with autotools (so we have to run "configure") or cmake.
        if not cmake:
            flags.append('--prefix=%s' % prefixPath)
            flags.append('--libdir=%s/lib' % prefixPath)

            t.addCommand('./configure %s' % ' '.join(flags),
                         targets=makeFile,
                         cwd=configPath,
                         out='%s/log/%s_configure.log' % (prefixPath, name),
                         always=configAlways)
        else:
            assert progInPath('cmake'), ("Cannot run 'cmake'. Please install "
                                         "it in your system first.")
            flags.append('-DCMAKE_INSTALL_PREFIX:PATH=%s .' % prefixPath)
            t.addCommand('cmake %s' % ' '.join(flags),
                         targets=makeFile,
                         cwd=configPath,
                         out='%s/log/%s_cmake.log' % (prefixPath, name))

        t.addCommand('make -j %d' % self._processors,
                     cwd=t.buildPath,
                     out='%s/log/%s_make.log' % (prefixPath, name))

        t.addCommand('make install',
                     targets=targets,
                     cwd=t.buildPath,
                     out='%s/log/%s_make_install.log' % (prefixPath, name))

        if clean:
            t.addCommand('make clean',
                         cwd=t.buildPath,
                         out='%s/log/%s_make_clean.log' % (prefixPath, name))
            t.addCommand('rm %s' % makeFile)

        return t

    def addModule(self, name, **kwargs):
        """Add a new module to our built Python .
        Params in kwargs:
            targets: targets that should be generated after building the module.
            flags: special flags passed to setup.py 
            deps: dependencies of this modules.
            default: True if this module is build by default.
        """
        # Use reasonable defaults.
        targets = kwargs.get('targets', [name])
        flags = kwargs.get('flags', [])
        
        deps = kwargs.get('deps', [])
        deps.append('python')

        prefixPath = os.path.abspath('software')
        flags.append('--prefix=%s' % prefixPath)

        modArgs = {'urlSuffix': 'python'}
        modArgs.update(kwargs)
        t = self._addDownloadUntar(name, **modArgs )
        self._addTargetDeps(t, deps)

        def path(x):
            if '/' in x:
                return x
            else:
                return 'software/lib/python2.7/site-packages/%s' % x
         
        t.addCommand('PYTHONHOME="%(root)s" LD_LIBRARY_PATH="%(root)s/lib" '
                     'PATH="%(root)s/bin:%(PATH)s" '
    #               'CFLAGS="-I%(root)s/include" LDFLAGS="-L%(root)s/lib" '
    # The CFLAGS line is commented out because even if it is needed for modules
    # like libxml2, it causes problems for others like numpy and scipy (see for
    # example http://mail.scipy.org/pipermail/scipy-user/2007-January/010773.html)
    # TODO: maybe add an argument to the function to chose if we want them?
                     '%(root)s/bin/python setup.py install %(flags)s > '
                     '%(root)s/log/%(name)s.log 2>&1' % {'root': prefixPath,
                                                       'PATH': os.environ['PATH'],
                                                       'flags': ' '.join(flags),
                                                       'name': name},
                   targets=[path(tg) for tg in targets],
                   cwd=t.buildPath)

        return t
    
    def addPackage(self, name, **kwargs):
        """ This function download a package tar.gz, untar it and 
        create a link in software/em.
        Params in kwargs:
            tar: the package tar file, by default the name + .tgz
            commands: a list with action to be executed to install the package
        """
        # We reuse the download and untar from the addLibrary method
        # and pass the createLink as a new command 
        tar = kwargs.get('tar', '%s.tgz' % name)
        packageDir = tar.rsplit('.tar.gz', 1)[0].rsplit('.tgz', 1)[0]
        
        libArgs = {'downloadDir': os.path.join('software', 'em'),
                   'urlSuffix': 'em',
                   'default': False} # This will be updated with value in kwargs
        libArgs.update(kwargs)
        
        target = self._addDownloadUntar(name, **libArgs)
        target.addCommand(Command(self, Link(name, packageDir),
                             targets=[self.getEm(name), 
                                      self.getEm(packageDir)],
                             cwd=self.getEm('')))
        commands = kwargs.get('commands', [])
        for cmd, tgt in commands:
            if isinstance(tgt, basestring):
                tgt = [tgt]
            # Take all package targets relative to package build dir
            target.addCommand(cmd, targets=[os.path.join(target.buildPath, t) 
                                            for t in tgt], 
                         cwd=target.buildPath)            

        return target
    
    def _showTargetGraph(self, targetList):
        """ Traverse the targets taking into account
        their dependences and print them in DOT format.
        """
        print('digraph libraries {')
        for tgt in targetList:
            deps = tgt.getDeps()
            if deps:
                print('\n'.join("  %s -> %s" % (tgt, x) for x in deps))
            else:
                print("  %s" % tgt)
        print('}')

    def _showTargetTree(self, targetList, maxLevel=-1):
        """ Print the tree of dependencies for the given targets,
        up to a depth level of maxLevel (-1 for unlimited).
        """
        # List of (indent level, target)
        nodes = [(0, tgt) for tgt in targetList[::-1]]
        while nodes:
            lvl, tgt = nodes.pop()
            print("%s- %s" % ("  " * lvl, tgt))
            if maxLevel != -1 and lvl >= maxLevel:
                continue
            nodes.extend((lvl + 1, self._targetDict[x]) for x in tgt.getDeps())

    def _executeTargets(self, targetList):
        """ Execute the targets in targetList, running all their
        dependencies first.
        """
        executed = set()  # targets already executed
        exploring = set()  # targets whose dependencies we are exploring
        targets = targetList[::-1]
        while targets:
            tgt = targets.pop()
            if tgt.getName() in executed:
                continue
            deps = tgt.getDeps()
            if set(deps) - executed:  # there are dependencies not yet executed
                if tgt.getName() in exploring:
                    raise RuntimeError("Cyclic dependency on %s" % tgt)
                exploring.add(tgt.getName())
                targets.append(tgt)
                targets.extend(self._targetDict[x] for x in deps)
            else:
                tgt.execute()
                executed.add(tgt.getName())
                exploring.discard(tgt.getName())

    def execute(self):
        # Check if there are explicit targets and only install
        # the selected ones, ignore starting with 'xmipp'
        cmdTargets = [a for a in self._args[2:] if a[0].isalpha() and not a.startswith('xmipp')]

        if cmdTargets:
            # Grab the targets passed in the command line
            targetList = [self._targetDict[t] for t in cmdTargets]
        else:
            # use all targets marked as default
            targetList = [t for t in self._targetList if t.isDefault()]

        if '--show-tree' in self._args:
            if '--dot' in self._args:
                self._showTargetGraph(targetList)
            else:
                self._showTargetTree(targetList)
        else:
            self._executeTargets(targetList)
            
        
class Link():
    def __init__(self, packageLink, packageFolder):
        self._packageLink = packageLink
        self._packageFolder = packageFolder
        
    def __call__(self):
        self.createPackageLink(self._packageLink, self._packageFolder)
        
    def __str__(self):
        return "Link '%s -> %s'" % (self._packageLink, self._packageFolder)
        
    def createPackageLink(self, packageLink, packageFolder):
        """ Create a link to packageFolder in packageLink, validate
        that packageFolder exists and if packageLink exists it is 
        a link.
        This function is supposed to be executed in software/em folder.
        """
        linkText = "'%s -> %s'" % (packageLink, packageFolder)
        
        if not os.path.exists(packageFolder):
            print(red("Creating link %s, but '%s' does not exist!!!\n"
                 "INSTALLATION FAILED!!!" % (linkText, packageFolder)))
            sys.exit(1)
    
        if os.path.exists(packageLink):
            if os.path.islink(packageLink):
                os.remove(packageLink)
            else:
                print(red("Creating link %s, but '%s' exists and is not a link!!!\n"
                     "INSTALLATION FAILED!!!" % (linkText, packageLink)))
                sys.exit(1)
    
        os.symlink(packageFolder, packageLink)
        print("Created link: %s" % linkText)
