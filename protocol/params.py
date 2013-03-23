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
# *  e-mail address 'jmdelarosa@cnb.csic.es'
# *
# **************************************************************************
"""
This module have the classes for protocol params definition:
Param, Section and Form
The definition will be holded at class level and will
be shared by all protocol class instances
"""

from pyworkflow.object import *


class FormBase(OrderedObject):
    def __init__(self, **args):
        OrderedObject.__init__(self, **args)
         
#    def setTags(self, tags):
#        for k, v in tags.iteritems():
#            if k in ['section']:
#                value = None
#            elif k in ['hidden', 'expert', 'view', 'has_question', 'visualize', 'text', 'file']:
#                value = Boolean(True)
#            else:
#                value = String(v)
#            if not value is None:
#                setattr(self, k, value)
#                
#    def __getattr__(self, name):
#        value = None
#        if name in ['hidden', 'expert', 'view', 'has_question', 'visualize', 'text', 'file']:
#            value = Boolean(True)
#        elif name in ['label', 'help', 'list', 'condition', 'validate', 'wizard']:
#            value = String()
#        elif name == 'default':
#            value = DefaultString()
#            
#        self.__setattr__(name, value)
#        return value
    
    
class Section(FormBase):
    """Definition of a section to hold other params"""
    
    def addParam(self, name, value):
        """Add a new param to last section"""
        setattr(self, name, value)
        
    def __str__(self):
        s = "  Section, label: %s\n" % self.label.get()
        for key in self._attributes:
            s += "    Param: '%s', %s\n" % (key, str(getattr(self, key)))
        return s        

                    
class Form(List):
    """Store all sections and parameters"""

    def addSection(self, section):
        """Add a new section"""
        List.append(self, section)

    def addParam(self, name, value):
        """Add a new param to last section"""
        self[-1].addParam(name, value)
        
    def __str__(self):
        s = "Form: \n"
        for section in self:
            s += str(section)
        return s
        
class DefaultString(String):
    pass 
      
      
class Param(FormBase):
    """Definition of a protocol paramter"""
    def __init__(self, **args):
        FormBase.__init__(self)
        self.paramClass = args.get('paramClass', None) # This should be defined in subclasses
        #self.name = String(args.get('name', None))
        self.label = String(args.get('label', None))
        self.default = String(args.get('default', None))
        self.expert = Boolean(args.get('expert', None))
        self.help = String(args.get('help', None))
        
    def addParam(self, name, value):
        """Add a new param to last section"""
        self.lastSection.addParam(name, value)
        
    def __str__(self):
        return "    label: %s" % self.label.get()


class StringParam(Param):
    """Param with underlying String value"""
    def __init__(self, **args):
        Param.__init__(self, paramClass=String, **args)


class TextParam(StringParam):
    """Long string params"""
    def __init__(self, **args):
        StringParam.__init__(self, **args)
        
        
class RegexParam(StringParam):
    """Regex based string param"""
    pass


class PathParam(StringParam):
    """Param for path strings"""
    pass


class FileParam(PathParam):
    """Filename path"""
    pass


class FolderParam(PathParam):
    """Folder path"""
    pass

        
class EnumParam(StringParam):
    """Select from a list of values, separated by comma"""
    def __init__(self, **args):
        StringParam.__init__(self, **args)
        self.choices = String(args.get('choices', None))
        self.display = String(args.get('display', 'list'))
        
class IntParam(Param):
    def __init__(self, **args):
        Param.__init__(self, paramClass=Integer, **args)
        
    
class FloatParam(Param):
    def __init__(self, **args):
        Param.__init__(self, paramClass=Float, **args)
        
        
class BooleanParam(Param):
    def __init__(self, **args):
        Param.__init__(self, paramClass=Boolean, **args)
        
        
        
        
        