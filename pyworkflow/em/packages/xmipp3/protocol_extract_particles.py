# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
# *              Laura del Cano (ldelcano@cnb.csic.es)
# *              Adrian Quintana (aquintana@cnb.csic.es)
# *              Javier Vargas (jvargas@cnb.csic.es)
# *              Grigory Sharov (sharov@igbmc.fr)
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
# *  e-mail address 'scipion@cnb.csic.es'
# *
# **************************************************************************

from glob import glob
from itertools import izip
from os.path import exists, basename

import pyworkflow.em.metadata as md
import pyworkflow.utils as pwutils
from pyworkflow.em.packages.xmipp3.constants import SAME_AS_PICKING, OTHER
from pyworkflow.protocol.constants import STEPS_PARALLEL, LEVEL_ADVANCED, STATUS_FINISHED
from pyworkflow.protocol.params import (PointerParam, EnumParam, FloatParam, IntParam, 
                                        BooleanParam, RelationParam, Positive)
from pyworkflow.em.protocol import ProtExtractParticles
from pyworkflow.em.data import SetOfParticles
from pyworkflow.em.constants import RELATION_CTF

from convert import writeSetOfCoordinates, readSetOfParticles, micrographToCTFParam
from xmipp3 import XmippProtocol

# Rejection method constants
REJECT_NONE = 0
REJECT_MAXZSCORE = 1
REJECT_PERCENTAGE = 2

                
class XmippProtExtractParticles(ProtExtractParticles, XmippProtocol):
    """Protocol to extract particles from a set of coordinates"""
    _label = 'extract particles'
    
    def __init__(self, **args):
        ProtExtractParticles.__init__(self, **args)
        self.stepsExecutionMode = STEPS_PARALLEL

    #--------------------------- DEFINE param functions --------------------------------------------
    def _defineParams(self, form):
        form.addSection(label='Input')
        
        form.addParam('inputCoordinates', PointerParam, pointerClass='SetOfCoordinates', 
                      important=True,
                      label="Input coordinates",
                      help='Select the SetOfCoordinates ')
        
        form.addParam('micsSource', EnumParam, choices=['same as picking', 'other'],
                      default=0, important=True,
                      label='Micrographs source', display=EnumParam.DISPLAY_HLIST, 
                      help='By default the particles will be extracted \n'
                           'from the micrographs used in the picking \n'
                           'step ( _same as picking_ option ). \n'
                           'If you select _other_ option, you must provide \n'
                           'a different set of micrographs to extract from.\n'
                           '*Note*: In the _other_ case, ensure that provided \n'
                           'micrographs and coordinates are related \n'
                           'by micName or by micId. Difference in pixel size will \n'
                           'be handled automatically.')

        form.addParam('inputMicrographs', PointerParam, 
                      pointerClass='SetOfMicrographs', condition='micsSource != 0',
                      important=True, label='Input micrographs',
                      help='Select the SetOfMicrographs from which to extract.')

        form.addParam('ctfRelations', RelationParam, allowsNull=True,
                      relationName=RELATION_CTF, attributeName='getInputMicrographs',
                      label='CTF estimation',
                      help='Choose some CTF estimation related to input micrographs. \n'
                           'CTF estimation is needed if you want to do phase flipping or \n'
                           'you want to associate CTF information to the particles.')

        form.addParam('boxSize', IntParam, default=0,
                      label='Particle box size', validators=[Positive],
                      help='In pixels. The box size is the size of the boxed particles, '
                           'actual particles may be smaller than this. If you do downsampling '
                           'after extraction, provide final box size here.')

        form.addParam('doSort', BooleanParam, default=True,
                      label='Perform sort by statistics',
                      help='Perform sort by statistics to add zscore info to particles.')

        form.addParam('rejectionMethod', EnumParam, choices=['None','MaxZscore', 'Percentage'],
                      default=REJECT_NONE, display=EnumParam.DISPLAY_COMBO, condition='doSort',
                      label='Automatic particle rejection', expertLevel=LEVEL_ADVANCED,
                      help='How to automatically reject particles. It can be none (no rejection), '
                           'maxZscore (reject a particle if its Zscore is larger than this value), '
                           'Percentage (reject a given percentage in each one of the screening criteria).')

        form.addParam('maxZscore', IntParam, default=3, expertLevel=LEVEL_ADVANCED,
                      condition='doSort and rejectionMethod==%d' % REJECT_MAXZSCORE,
                      label='Maximum Zscore',
                      help='Maximum Zscore above which particles are rejected.')
        
        form.addParam('percentage', IntParam, default=5, expertLevel=LEVEL_ADVANCED, 
                      condition='rejectionMethod==%d' % REJECT_PERCENTAGE,
                      label='Percentage (%)',
                      help='Percentage of particles to reject')
        
        form.addSection(label='Preprocess')
        form.addParam('doRemoveDust', BooleanParam, default=True, important=True,
                      label='Dust removal (Recommended)', 
                      help='Sets pixels with unusually large values to random values from a Gaussian '
                           'with zero-mean and unity-standard deviation.')
        form.addParam('thresholdDust', FloatParam, default=3.5, 
                      condition='doRemoveDust', expertLevel=LEVEL_ADVANCED,
                      label='Threshold for dust removal',
                      help='Pixels with a signal higher or lower than this value times the standard '
                           'deviation of the image will be affected. For cryo, 3.5 is a good value.'
                           'For high-contrast negative stain, the signal itself may be affected so '
                           'that a higher value may be preferable.')

        form.addParam('doInvert', BooleanParam, default=False,
                      label='Invert contrast', 
                      help='Invert the contrast if your particles are black over a white background.\n'
                           'Xmipp, Spider, Relion and Eman require white particles over a black background\n'
                           'Frealign (up to v9.07) requires black particles over a white background')
        
        form.addParam('doFlip', BooleanParam, default=None,
                      label='Phase flipping (Recommended)', 
                      help='Use the information from the CTF to compensate for phase reversals.\n'
                           'Phase flip is recommended in Xmipp or Eman\n'
                           '(even Wiener filtering and bandpass filter are recommended for obtaining '
                           'better 2D classes)\nOtherwise (Frealign, Relion, Spider, ...), '
                           'phase flip is not recommended.')

        form.addParam('doDownsample', BooleanParam, default=False,
                      label='Downsample particles?',
                      help='Downsample particles by a given factor upon extraction.')
        form.addParam('downFactor', FloatParam, default=2.0,
                      condition='doDownsample',
                      label='Downsampling factor',
                      help='Non-integer downsample factors are possible. Must be larger than 1.')
        
        form.addParam('doNormalize', BooleanParam, default=True,
                      label='Normalize (Recommended)', 
                      help='It subtract a ramp in the gray values and normalizes so that in the '
                           'background there is 0 mean and standard deviation 1.')
        form.addParam('normType', EnumParam, choices=['OldXmipp','NewXmipp','Ramp'], default=2, 
                      condition='doNormalize', expertLevel=LEVEL_ADVANCED,
                      display=EnumParam.DISPLAY_COMBO,
                      label='Normalization type', 
                      help='OldXmipp (mean(Image)=0, stddev(Image)=1).  \n  '
                           'NewXmipp (mean(background)=0, stddev(background)=1)  \n  '
                           'Ramp (subtract background+NewXmipp).  \n  ')
        form.addParam('backRadius', IntParam, default=-1, condition='doNormalize',
                      label='Background radius', expertLevel=LEVEL_ADVANCED,
                      help='Pixels outside this circle are assumed to be noise and their stddev '
                           'is set to 1. Radius for background circle definition (in pix.). '
                           'If this value is 0, then half the box size is used.')

        form.addParallelSection(threads=4, mpi=1)

    #--------------------------- INSERT steps functions --------------------------------------------
    def _insertAllSteps(self):
        """for each micrograph insert the steps to preprocess it"""
        self._setupBasicProperties()
        # Write pos files for each micrograph
        firstStepId = self._insertFunctionStep('writePosFilesStep')
        
        # For each micrograph insert the steps, run in parallel
        deps = []
        
        for mic in self.inputMics:
            localDeps = [firstStepId]
            micrographToExtract = mic.getFileName()
            baseMicName = pwutils.removeBaseExt(mic.getFileName())

            if self.ctfRelations.hasValue():
                micKey = self.micKey(mic)
                mic.setCTF(self.ctfDict[micKey])

            # If remove dust 
            if self.doRemoveDust:
                fnNoDust = self._getTmpPath(baseMicName + "_noDust.xmp")
                thresholdDust = self.thresholdDust.get() #TODO: remove this extra variable
                args = " -i %(micrographToExtract)s -o %(fnNoDust)s"
                args += " --bad_pixels outliers %(thresholdDust)f"
                localDeps = [self._insertRunJobStep("xmipp_transform_filter",
                                                    args % locals(),
                                                    prerequisites=localDeps)]
                micrographToExtract = fnNoDust

            fnCTF = None
            if self.ctfRelations.hasValue():
                # If the micrograph doesn't come from Xmipp, we need to write
                # a Xmipp ctfparam file to perform the phase flip on the micrograph                     
                fnCTF = micrographToCTFParam(mic, self._getTmpPath("%s.ctfParam" % baseMicName))
                # Insert step to flip micrograph
                if self.doFlip:
                    localDeps = [self._insertFunctionStep('flipMicrographStep',
                                                          baseMicName, fnCTF,
                                                          micrographToExtract,
                                                          prerequisites=localDeps)]
                    micrographToExtract = self._getTmpPath(baseMicName + "_flipped.xmp")
            else:
                fnCTF = None
            
            # Actually extract
            deps.append(self._insertFunctionStep('extractParticlesStep',
                                                 mic.getObjId(), baseMicName,
                                                 fnCTF, micrographToExtract,
                                                 prerequisites=localDeps))

        # Insert step to create output objects
        metaDeps = self._insertFunctionStep('createMetadataImageStep', prerequisites=deps)
        
        if self.doSort:
            screenDep = self._insertFunctionStep('screenParticlesStep', prerequisites=[metaDeps])
            finalDeps = [screenDep]
        else:
            finalDeps = [metaDeps]
        
        self._insertFunctionStep('createOutputStep', prerequisites=finalDeps)

    #--------------------------- STEPS functions --------------------------------------------
    def writePosFilesStep(self):
        """ Write the pos file for each micrograph on metadata format. """
        writeSetOfCoordinates(self._getExtraPath(), self.inputCoords)
        # We need to find the mapping (either by micName (without ext) or micId)
        # between the micrographs in the SetOfCoordinates and
        # the Other micrographs if necessary
        if self.micsSource == OTHER:
            micDict = {}
            coordMics = self.inputCoords.getMicrographs()
            for mic in coordMics:
                micBase = pwutils.removeBaseExt(mic.getFileName())
                micPos = self._getExtraPath(micBase + ".pos")
                micDict[pwutils.removeBaseExt(mic.getMicName())] = micPos
                micDict[mic.getObjId()] = micPos
                
            if any(pwutils.removeBaseExt(mic.getMicName()) in micDict for mic in self.inputMics):
                micKey = lambda mic: pwutils.removeBaseExt(mic.getMicName())
            elif any(mic.getObjId() in micDict for mic in self.inputMics):
                self.warning('Could not match input micrographs and coordinates '
                             'micrographs by micName, using micId.')
                micKey = lambda mic: mic.getObjId()
            else:
                raise Exception('Could not match input micrographs and coordinates '
                                'neither by micName or micId.')
            
            for mic in self.inputMics: # micrograph from input (other)
                mk = micKey(mic)
                if mk in micDict:
                    micPosCoord = micDict[mk]
                    if exists(micPosCoord):
                        micBase = pwutils.removeBaseExt(mic.getFileName())
                        micPos = self._getExtraPath(micBase + ".pos")
                        if micPos != micPosCoord:
                            self.info('Moving %s -> %s' % (micPosCoord, micPos))
                            pwutils.moveFile(micPosCoord, micPos)
                        
    def flipMicrographStep(self, baseMicName, fnCTF, micrographToExtract):
        """ Flip micrograph. """           
        fnFlipped = self._getTmpPath(baseMicName +"_flipped.xmp")
        args = " -i %(micrographToExtract)s --ctf %(fnCTF)s -o %(fnFlipped)s"
        args += " --sampling %f" % self.samplingMics
        self.runJob("xmipp_ctf_phase_flip", args % locals())
        
    def extractParticlesStep(self, micId, baseMicName, fnCTF, micrographToExtract):
        """ Extract particles from one micrograph """
        outputRoot = str(self._getExtraPath(baseMicName))
        fnPosFile = self._getExtraPath(baseMicName + ".pos")

        # If it has coordinates extract the particles      
        particlesMd = 'particles@%s' % fnPosFile
        boxSize = self.boxSize.get()
        # get box size for extraction, before downsampling
        if self.doDownsample:
            boxSize *= self.downFactor.get()
        
        if exists(fnPosFile):
            args = " -i %(micrographToExtract)s --pos %(particlesMd)s" % locals()
            args += " -o %(outputRoot)s --Xdim %(boxSize)d" % locals()
            if self.micsSource.get() != SAME_AS_PICKING:
                args += " --downsampling %f" % self.samplingFactor
            if self.doInvert:
                args += " --invert"
            if fnCTF:
                args += " --ctfparam " + fnCTF
            self.runJob("xmipp_micrograph_scissor", args)

            # Downsample
            if self.doDownsample:
                downFactor = self.downFactor.get()
                self.runDownsample(outputRoot + '.stk', boxSize, downFactor)

            # Normalize 
            if self.doNormalize:
                self.runNormalize(outputRoot + '.stk', self.normType.get(), self.backRadius.get())          
                               
            if self.doDownsample:
                #rescale coords in metadata file if doDownsample
                selfile = outputRoot + ".xmd"
                mdSelFile = md.MetaData(selfile)
                mdSelFile.operate("Xcoor=Xcoor*%f" % (1.0 / downFactor))
                mdSelFile.operate("Ycoor=Ycoor*%f" % (1.0 / downFactor))
                mdSelFile.write(selfile)
        else:
            self.warning("The micrograph %s hasn't coordinate file! " % baseMicName)
            self.warning("Maybe you picked over a subset of micrographs")

        # Let's clean the temporary mrc micrographs
        pwutils.cleanPattern(self._getTmpPath(baseMicName) + '*')

    def runDownsample(self, stack, boxSize, downFactor):
        program = "xmipp_image_resize"
        #outputFn = removeExt(stack) + '_down.stk'
        #FIXME: is it OK to overwrite input stack?
        args = " -i %s --fourier %d" % (stack, int(boxSize / downFactor))
        self.runJob(program, args % locals())

    def runNormalize(self, stack, normType, bgRadius):
        program = "xmipp_transform_normalize"
        args = " -i %(stack)s "
        
        if bgRadius <= 0:
            particleSize = md.MetaDataInfo(stack)[0]
            bgRadius = int(particleSize/2)
        
        if normType=="OldXmipp":
            args += " --method OldXmipp"
        elif normType=="NewXmipp":
            args += " --method NewXmipp --background circle %(bgRadius)d"
        else:
            args += " --method Ramp --background circle %(bgRadius)d"
        self.runJob(program, args % locals())
    
    def createMetadataImageStep(self):
        #Create images.xmd metadata
        fnImages = self._getOutputImgMd()
        imgsXmd = md.MetaData()
        posFiles = glob(self._getExtraPath('*.pos')) 
        for posFn in posFiles:
            xmdFn = self._getExtraPath(pwutils.replaceBaseExt(posFn, "xmd"))
            if exists(xmdFn):
                mdFn = md.MetaData(xmdFn)
                mdPos = md.MetaData('particles@%s' % posFn)
                mdPos.merge(mdFn) 
                imgsXmd.unionAll(mdPos)
            else:
                self.warning("The coord file %s wasn't used for extraction! " % basename(posFn))
                self.warning("Maybe you are extracting over a subset of micrographs")
        imgsXmd.write(fnImages)

    def screenParticlesStep(self):
        # If selected run xmipp_image_sort_by_statistics to add zscore info to images.xmd
        fnImages = self._getOutputImgMd()
        args = " -i %(fnImages)s --addToInput"
        if self.rejectionMethod == REJECT_MAXZSCORE:
            maxZscore = self.maxZscore.get()
            args += " --zcut " + str(maxZscore)
        elif self.rejectionMethod == REJECT_PERCENTAGE:
            percentage = self.percentage.get()
            args += " --percent " + str(percentage)
        
        self.runJob("xmipp_image_sort_by_statistics", args % locals())
    
    def createOutputStep(self):
        # Create the SetOfImages object on the database
        fnImages = self._getOutputImgMd()
        # Create output SetOfParticles
        imgSet = self._createSetOfParticles()
        imgSet.copyInfo(self.inputMics)
        # set coords from the input, will update later if needed
        imgSet.setCoordinates(self.inputCoords)

        if self.doFlip:
            # Check if self.inputMics are phase flipped.
            if self.inputMics.isPhaseFlipped():
                imgSet.setIsPhaseFlipped(False)
            else:
                imgSet.setIsPhaseFlipped(True)

        sampling = self.samplingMics if self.micsSource == OTHER else self.samplingInput
        if self.doDownsample:
            sampling *= self.downFactor.get()
        imgSet.setSamplingRate(sampling)

        # Create a temporary set to read from the metadata file
        # and later create the good one with the coordinates 
        # properly set. We need this because the .update is not
        # working in the mapper when new attributes are added.
        imgSet.setHasCTF(self.ctfRelations.hasValue())
        auxSet = SetOfParticles(filename=':memory:')
        auxSet.copyInfo(imgSet)
        readSetOfParticles(fnImages, auxSet)

        # calculate factor for coords scaling
        factor = 1 / self.samplingFactor
        if self.doDownsample:
            factor /= self.downFactor.get()

        # For each particle retrieve micId from SetOfCoordinates and set it on the CTFModel
        for img in auxSet:
            coord = self.getCoords()[img.getObjId()]
            if self.micsSource == OTHER or self.doDownsample:
                coord.scale(factor)
            ctfModel = img.getCTF()
            if ctfModel is not None:
                ctfModel.setObjId(coord.getMicId())
            img.setMicId(coord.getMicId())
            img.setCoordinate(coord)
            imgSet.append(img)

        self._storeMethodsInfo(fnImages)
        self._defineOutputs(outputParticles=imgSet)
        self._defineSourceRelation(self.inputCoordinates, imgSet)
        if self.ctfRelations.hasValue():
            self._defineSourceRelation(self.ctfRelations.get(), imgSet)

    #--------------------------- INFO functions -------------------------------------------- 
    def _validate(self):
        errors = []
        if self.doDownsample and self.downFactor.get() <= 1.0:
            errors.append('Downsample factor must be larger than 1.')
        
        # doFlip can only be True if CTF information is available on picked micrographs
        if self.doFlip and not self.ctfRelations.hasValue():
            errors.append('Phase flipping cannot be performed unless CTF information is provided.')

        if self.doNormalize:
            if self.backRadius > int(self.boxSize.get() / 2):
                errors.append("Background radius for normalization should be "
                              "equal or less than half of the box size.")

        self._setupCtfProperties() # setup self.micKey among others
        if self.ctfRelations.hasValue() and self.micKey is None:
            errors.append('Some problem occurs matching micrographs and CTF.\n'
                                'There were micrographs for which CTF was not found\n'
                                'either using micName or micId.\n')
        return errors
    
    def _citations(self):
        return ['Vargas2013b']
        
    def _summary(self):
        micsSourceText = {SAME_AS_PICKING:'Same as picking',
                          OTHER: 'Other set'}
        summary = []
        summary.append("Micrographs source: %s" % micsSourceText.get(self.micsSource.get()))
        summary.append("Particle box size: %d" % self.boxSize.get())
        
        if not hasattr(self, 'outputParticles'):
            summary.append("Output images not ready yet.") 
        else:
            summary.append("Particles extracted: %d" % (self.outputParticles.getSize()))
            
        return summary
    
    def _methods(self):
        methodsMsgs = []

        if self.getStatus() == STATUS_FINISHED:
            msg = "A total of %d particles of size %d were extracted" % (self.getOutput().getSize(),
                                                                         self.boxSize)
            if self.micsSource == OTHER:
                msg += " from another set of micrographs: %s" % self.getObjectTag('inputMicrographs')

            msg += " using coordinates %s" % self.getObjectTag('inputCoordinates')
            msg += self.methodsVar.get('')
            methodsMsgs.append(msg)

            if self.doRemoveDust:
                methodsMsgs.append("Removed dust over a threshold of %s." % (self.thresholdDust))
            if self.doInvert:
                methodsMsgs.append("Inverted contrast on images.")
            if self.doDownsample:
                methodsMsgs.append("Particles downsampled by a factor of %0.2f." % self.downFactor)
            if self.doNormalize:
                methodsMsgs.append("Normalization performed of type %s." % (self.getEnumText('normType')))

        return methodsMsgs

    #--------------------------- UTILS functions --------------------------------------------
    def _setupBasicProperties(self):
        # Set sampling rate (before and after doDownsample) and inputMics
        # according to micsSource type
        self.inputCoords = self.getCoords()
        self.inputMics = self.getInputMicrographs()
        self.samplingInput = self.inputCoords.getMicrographs().getSamplingRate()
        self.samplingMics = self.inputMics.getSamplingRate()
        self.samplingFactor = float(self.samplingMics / self.samplingInput)

        self._setupCtfProperties()
        
    def _setupCtfProperties(self):
        inputMics = self.getInputMicrographs()
        if self.ctfRelations.hasValue():
            # Load CTF dictionary for all micrographs, all CTF should be present
            self.ctfDict = {}
            
            for ctf in self.ctfRelations.get():
                ctfMic = ctf.getMicrograph()
                newCTF = ctf.clone()
                self.ctfDict[ctfMic.getMicName()] = newCTF
                self.ctfDict[ctfMic.getObjId()] = newCTF
            
            if all(mic.getMicName() in self.ctfDict for mic in inputMics):
                self.micKey = lambda mic: mic.getMicName()
            elif all(mic.getObjId() in self.ctfDict for mic in inputMics):
                self.micKey = lambda mic: mic.getObjId()
            else:
                self.micKey = None # some problem matching CTF
            
    def getInputMicrographs(self):
        """ Return the micrographs associated to the SetOfCoordinates or
        Other micrographs. """
        if self.micsSource == SAME_AS_PICKING:
            return self.inputCoordinates.get().getMicrographs()
        else:
            return self.inputMicrographs.get()

    def _storeMethodsInfo(self, fnImages):
        """ Store some information when the protocol finishes. """
        mdImgs = md.MetaData(fnImages)
        total = mdImgs.size() 
        mdImgs.removeDisabled()
        zScoreMax = mdImgs.getValue(md.MDL_ZSCORE, mdImgs.lastObject())
        numEnabled = mdImgs.size()
        numRejected = total - numEnabled
        msg = ""

        if self.doSort:
            if self.rejectionMethod != REJECT_NONE:
                msg = " %d of them were rejected with Zscore greater than %.2f." % (numRejected, zScoreMax)
        if self.doFlip:
            msg += "\nPhase flipping was performed."

        self.methodsVar.set(msg)

    def getCoords(self):
        return self.inputCoordinates.get()

    def getOutput(self):
        if self.hasAttribute('outputParticles') and self.outputParticles.hasValue():
            return self.outputParticles
        else:
            return None

    def getBoxSize(self):
        # This function is needed by the wizard
        inputMics = self.getInputMicrographs()
        boxSize = self.getCoords().getBoxSize()
        samplingInput = self.getCoords().getMicrographs().getSamplingRate()
        samplingMics = inputMics.getSamplingRate()
        samplingFactor = float(samplingMics / samplingInput)

        # if micsSource same as picking sampling does not change, except if we doDownsample
        if self.micsSource.get() == SAME_AS_PICKING:
            if self.doDownsample:
                return int(boxSize / self.downFactor.get())
            else:
                return boxSize
        # if micsSource is Other, recalculate boxSize from pixel size difference
        else:
            if self.doDownsample:
                return int(boxSize / samplingFactor / self.downFactor.get())
            else:
                return int(boxSize / samplingFactor)

    def _getOutputImgMd(self):
        return self._getPath('images.xmd')
