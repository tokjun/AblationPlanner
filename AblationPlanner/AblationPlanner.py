import os
import unittest
from __main__ import vtk, qt, ctk, slicer
import math
import numpy
from Endoscopy import EndoscopyComputePath

#
# AblationPlanner
#

class AblationPlanner:
  def __init__(self, parent):
    parent.title = "AblationPlanner"
    parent.categories = ["IGT"]
    parent.dependencies = []
    parent.contributors = ["Junichi Tokuda (BWH), Laurent Chauvin (BWH)"]
    parent.helpText = """
    This module generates a 3D curve model that connects fiducials listed in a given markup node. 
    """
    parent.acknowledgementText = """
    This work was supported by National Center for Image Guided Therapy (P41EB015898). The module is based on a template developed by Jean-Christophe Fillion-Robin, Kitware Inc. and Steve Pieper, Isomics, Inc. partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.
    self.parent = parent


#
# AblationPlannerWidget
#

class AblationPlannerWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()
    self.logic = AblationPlannerLogic()
    self.tag = 0

  def setup(self):
    # Instantiate and connect widgets ...
    
    #####################
    ## For debugging
    ##
    ## Reload and Test area
    #reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    #reloadCollapsibleButton.text = "Reload && Test"
    #self.layout.addWidget(reloadCollapsibleButton)
    #reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)
    #
    ## reload button
    ## (use this during development, but remove it when delivering
    ##  your module to users)
    #self.reloadButton = qt.QPushButton("Reload")
    #self.reloadButton.toolTip = "Reload this module."
    #self.reloadButton.name = "AblationPlanner Reload"
    #reloadFormLayout.addWidget(self.reloadButton)
    #self.reloadButton.connect('clicked()', self.onReload)
    ##
    #####################

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Source points (vtkMRMLMarkupsFiducialNode)
    #
    self.SourceSelector = slicer.qMRMLNodeComboBox()
    self.SourceSelector.nodeTypes = ( ("vtkMRMLAnnotationRulerNode"), "" )
    self.SourceSelector.addEnabled = True
    self.SourceSelector.removeEnabled = False
    self.SourceSelector.noneEnabled = True
    self.SourceSelector.showHidden = False
    self.SourceSelector.renameEnabled = True
    self.SourceSelector.showChildNodeTypes = False
    self.SourceSelector.setMRMLScene( slicer.mrmlScene )
    self.SourceSelector.setToolTip( "Pick up a Ruler node listing fiducials." )
    parametersFormLayout.addRow("Source points: ", self.SourceSelector)

    #
    # Target point (vtkMRMLMarkupsFiducialNode)
    #
    self.DestinationSelector = slicer.qMRMLNodeComboBox()
    self.DestinationSelector.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.DestinationSelector.addEnabled = True
    self.DestinationSelector.removeEnabled = False
    self.DestinationSelector.noneEnabled = True
    self.DestinationSelector.showHidden = False
    self.DestinationSelector.renameEnabled = True
    self.DestinationSelector.selectNodeUponCreation = True
    self.DestinationSelector.showChildNodeTypes = False
    self.DestinationSelector.setMRMLScene( slicer.mrmlScene )
    self.DestinationSelector.setToolTip( "Pick up or create a Model node." )
    parametersFormLayout.addRow("Ablation volume model: ", self.DestinationSelector)


    #
    # Major axis for the ablation volume
    #
    self.MajorAxisSliderWidget = ctk.ctkSliderWidget()
    self.MajorAxisSliderWidget.singleStep = 1.0
    self.MajorAxisSliderWidget.minimum = 1.0
    self.MajorAxisSliderWidget.maximum = 100.0
    self.MajorAxisSliderWidget.value = 30.0
    self.MajorAxisSliderWidget.setToolTip("Size of ablation volume -- diameter for major axis.")
    parametersFormLayout.addRow("Major Axis (mm): ", self.MajorAxisSliderWidget)

    #
    # MinorAxis for the tube
    #
    self.MinorAxisSliderWidget = ctk.ctkSliderWidget()
    self.MinorAxisSliderWidget.singleStep = 1.0
    self.MinorAxisSliderWidget.minimum = 1.0
    self.MinorAxisSliderWidget.maximum = 100.0
    self.MinorAxisSliderWidget.value = 20.0
    self.MinorAxisSliderWidget.setToolTip("Size of ablation volume -- diameter for minor axis.")
    parametersFormLayout.addRow("Minor Axis (mm): ", self.MinorAxisSliderWidget)

    #
    # TipOffset for the tube
    #
    self.TipOffsetSliderWidget = ctk.ctkSliderWidget()
    self.TipOffsetSliderWidget.singleStep = 1.0
    self.TipOffsetSliderWidget.minimum = 0.0
    self.TipOffsetSliderWidget.maximum = 50.0
    self.TipOffsetSliderWidget.value = 0.0
    self.TipOffsetSliderWidget.setToolTip("Offset between probe tip and ablation volume center.")
    parametersFormLayout.addRow("Ablation volume offset (mm): ", self.TipOffsetSliderWidget)

    #
    # Check box to start visualizing the ablation volume
    #
    self.EnableCheckBox = qt.QCheckBox()
    self.EnableCheckBox.checked = 0
    self.EnableCheckBox.setToolTip("If checked, the AblationPlanner module keeps updating the ablation volume as the points are updated.")
    parametersFormLayout.addRow("Enable", self.EnableCheckBox)

    #
    # Check box to show the slice intersection
    #
    self.SliceIntersectionCheckBox = qt.QCheckBox()
    self.SliceIntersectionCheckBox.checked = 1
    self.SliceIntersectionCheckBox.setToolTip("If checked, intersection of the ablation volume will be displayed on 2D viewers.")
    parametersFormLayout.addRow("Slice Intersection", self.SliceIntersectionCheckBox)

    # Connections
    self.EnableCheckBox.connect('toggled(bool)', self.onEnable)
    self.SliceIntersectionCheckBox.connect('toggled(bool)', self.onEnableSliceIntersection)
    self.SourceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSourceSelected)
    self.DestinationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onDestinationSelected)
    self.MajorAxisSliderWidget.connect("valueChanged(double)", self.onSizeParameterUpdated)
    self.MinorAxisSliderWidget.connect("valueChanged(double)", self.onSizeParameterUpdated)
    self.TipOffsetSliderWidget.connect("valueChanged(double)", self.onSizeParameterUpdated)

    # Add vertical spacer
    self.layout.addStretch(1)
    
  def cleanup(self):
    pass

  def onEnable(self, state):
    self.logic.enableAutomaticUpdate(state)

  def onEnableSliceIntersection(self, state):
    self.logic.enableSliceIntersection(state)

  def onSourceSelected(self):
    # Remove observer if previous node exists
    if self.logic.SourceNode and self.tag:
      self.logic.SourceNode.RemoveObserver(self.tag)

    # Update selected node, add observer, and update control points
    if self.SourceSelector.currentNode():
      self.logic.SourceNode = self.SourceSelector.currentNode()

      # Check if model has already been generated with for this fiducial list
      ablationVolumeModelID = self.logic.SourceNode.GetAttribute('AblationPlanner.VolumeModel')
      self.DestinationSelector.setCurrentNodeID(ablationVolumeModelID)

      self.tag = self.logic.SourceNode.AddObserver('ModifiedEvent', self.logic.controlPointsUpdated)

    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('AblationPlanner.VolumeModel',self.logic.DestinationNode.GetID())
      self.logic.updateAblationVolume()

  def onDestinationSelected(self):
    # Update destination node
    if self.DestinationSelector.currentNode():
      self.logic.DestinationNode = self.DestinationSelector.currentNode()
      self.logic.DestinationNode.AddObserver(vtk.vtkCommand.ModifiedEvent, self.onModelModifiedEvent)
      ## TODO: Need to remove observer?

    # Update checkbox
    if (self.SourceSelector.currentNode() == None or self.DestinationSelector.currentNode() == None):
      self.EnableCheckBox.setCheckState(False)
    else:
      self.logic.SourceNode.SetAttribute('AblationPlanner.VolumeModel',self.logic.DestinationNode.GetID())
      self.logic.updateAblationVolume()

  def onSizeParameterUpdated(self):
    self.logic.setSize(self.MajorAxisSliderWidget.value, self.MinorAxisSliderWidget.value)
    self.logic.setTipOffset(self.TipOffsetSliderWidget.value)

  def onReload(self,moduleName="AblationPlanner"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    globals()[moduleName] = slicer.util.reloadScriptedModule(moduleName)

  def onModelModifiedEvent(self, caller, event):
    pass



#
# AblationPlannerLogic
#

class AblationPlannerLogic:

  def __init__(self):
    self.SourceNode = None
    self.DestinationNode = None
    self.TubeRadius = 5.0

    self.MajorAxis = 30.0
    self.MinorAxis = 20.0
    self.TipOffset = 0.0

    self.AutomaticUpdate = False
    self.NumberOfIntermediatePoints = 20
    self.ModelColor = [0.0, 0.0, 1.0]

    self.SphereSource = None
    self.SliceIntersection = True
    
  def setNumberOfIntermediatePoints(self,npts):
    if npts > 0:
      self.NumberOfIntermediatePoints = npts
    self.updateAblationVolume()

  def setSize(self, majorAxis, minorAxis):
    self.MajorAxis = majorAxis
    self.MinorAxis = minorAxis
    self.updateAblationVolume()
    
  def setTipOffset(self, offset):
    self.TipOffset = offset
    self.updateAblationVolume()

  def enableAutomaticUpdate(self, auto):
    self.AutomaticUpdate = auto
    self.updateAblationVolume()

  def enableSliceIntersection(self, state):
    if self.DestinationNode.GetDisplayNodeID() == None:
      modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
      modelDisplayNode.SetColor(self.ModelColor)
      slicer.mrmlScene.AddNode(modelDisplayNode)
      self.DestinationNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
    
    displayNodeID = self.DestinationNode.GetDisplayNodeID()
    displayNode = slicer.mrmlScene.GetNodeByID(displayNodeID)
    if displayNode != None:
      if state:
        displayNode.SliceIntersectionVisibilityOn()
      else:
        displayNode.SliceIntersectionVisibilityOff()
    

  def controlPointsUpdated(self,caller,event):
    if caller.IsA('vtkMRMLAnnotationRulerNode') and event == 'ModifiedEvent':
      self.updateAblationVolume()

  def computeTransform(self, pTip, pTail, offset, transform):
    v1 = [0.0, 0.0, 0.0]
    vtk.vtkMath.Subtract(pTip, pTail, v1)
    vtk.vtkMath.Normalize(v1)
    v2 = [0.0, 0.0, 1.0]
    axis = [0.0, 0.0, 0.0]

    #vtk.vtkMath.Cross(v1, v2, axis)
    vtk.vtkMath.Cross(v2, v1, axis)
    #angle = vtk.vtkMath.AngleBetweenVectors(v1, v2) # This does not work
    s = vtk.vtkMath.Norm(axis)
    c = vtk.vtkMath.Dot(v1, v2)
    angle = math.atan2(s, c)

    tipOffset = v1
    vtk.vtkMath.MultiplyScalar(tipOffset, offset)
    transform.PostMultiply()
    transform.RotateWXYZ(angle*180.0/math.pi, axis)
    transform.Translate(pTip)
    transform.Translate(tipOffset)

  def updateAblationVolume(self):

    if self.AutomaticUpdate == False:
      return

    if self.SourceNode and self.DestinationNode:

      pTip = [0.0, 0.0, 0.0]
      pTail = [0.0, 0.0, 0.0]
      #self.SourceNode.GetNthFiducialPosition(0,pTip)
      self.SourceNode.GetPosition1(pTip)
      #self.SourceNode.GetNthFiducialPosition(1,pTail)
      self.SourceNode.GetPosition2(pTail)
      
      if self.DestinationNode.GetDisplayNodeID() == None:
        modelDisplayNode = slicer.vtkMRMLModelDisplayNode()
        modelDisplayNode.SetColor(self.ModelColor)
        slicer.mrmlScene.AddNode(modelDisplayNode)
        self.DestinationNode.SetAndObserveDisplayNodeID(modelDisplayNode.GetID())
        
      displayNodeID = self.DestinationNode.GetDisplayNodeID()
      modelDisplayNode = slicer.mrmlScene.GetNodeByID(displayNodeID)

      if modelDisplayNode != None and self.SliceIntersection == True:
        modelDisplayNode.SliceIntersectionVisibilityOn()
      else:
        modelDisplayNode.SliceIntersectionVisibilityOff()
        
      if self.SphereSource == None:  
        self.SphereSource = vtk.vtkSphereSource()
        self.SphereSource.SetThetaResolution(20)
        self.SphereSource.SetPhiResolution(20)
        self.SphereSource.Update()
        
      # Scale sphere to make ellipsoid
      scale = vtk.vtkTransform()
      scale.Scale(self.MinorAxis, self.MinorAxis, self.MajorAxis)
      scaleFilter = vtk.vtkTransformPolyDataFilter()
      scaleFilter.SetInputConnection(self.SphereSource.GetOutputPort())
      scaleFilter.SetTransform(scale)
      scaleFilter.Update();
      
      # Transform
      transform = vtk.vtkTransform()
      self.computeTransform(pTip, pTail, self.TipOffset, transform)
      transformFilter = vtk.vtkTransformPolyDataFilter()
      transformFilter.SetInputConnection(scaleFilter.GetOutputPort())
      transformFilter.SetTransform(transform)
      transformFilter.Update();
      
      self.DestinationNode.SetAndObservePolyData(transformFilter.GetOutput())
      self.DestinationNode.Modified()
      
      if self.DestinationNode.GetScene() == None:
        slicer.mrmlScene.AddNode(self.DestinationNode)

        
