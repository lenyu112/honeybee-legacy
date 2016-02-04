#
# Honeybee: A Plugin for Environmental Analysis (GPL) started by Mostapha Sadeghipour Roudsari
# 
# This file is part of Honeybee.
# 
# Copyright (c) 2013-2016, Chris Mackey <Chris@MackeyArchitecture.com.com> 
# Honeybee is free software; you can redistribute it and/or modify 
# it under the terms of the GNU General Public License as published 
# by the Free Software Foundation; either version 3 of the License, 
# or (at your option) any later version. 
# 
# Honeybee is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of 
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the 
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Honeybee; If not, see <http://www.gnu.org/licenses/>.
# 
# @license GPL-3.0+ <http://spdx.org/licenses/GPL-3.0+>


"""
Use this component to import the colored mesh results from a THERM simulation.  Note that, because the THERM API version is not free, you will have to open the file generated by run the "Write THERM File" component are run it yourself (maybe in the future, we will be able to launch it from the command line).
_
Before you run the file in THERM, make sure that you go to Options > Preferences > Simulation and check "Save Conrad results file (.O)" in order to enure that your THERM simulation writes all results out in a format that this component understands.
-
Provided by Honeybee 0.0.59
    
    Args:
        _resultFile: The resultFileAddress from the "Write THERM File" component.  Make sure that you have opened THERM and run your file before using this component. Also, before you run the file in THERM, make sure that you go to Options > Preferences > Simulation and check "Save Conrad results file (.O)" in order to enure that your THERM simulation writes this file.
        thermFile_: An optional filepath to a THERM file that has been generated with the 'Honeybee_Write THERM File' component.  The header of this file contains information on the transformations used to map the original geometry between Rhino space and the THERM canvas.  As a result, connecting a file here ensures that imported results happen on top of the original Rhino geometry.  If no file address is connected here, the THERM results are imported with their THERM canvass coordinates.
        uFactorFile_: An optional path to a THERM file that has been saved after importing and simulating files generated with the 'Honeybee_Write THERM File' component. Before you run the file in THERM, make sure that you go to Options > Preferences > Preferences and check "Automatic XML Export on Save" in order to enure that your THERM simulation writes this uFactorFile.
        dataType_: An optional integer to set the type of data to import.  If left blank, this component will import the temperature data.  Choose from the following two options:
            0 - Temperature (temperature meshValues at each point in C)
            1 - Heat Flux (heat flux meshValues at each point in W/m2)
        SIorIP_: Set to 'True' to have all data imported with SI units (Celcius and W/m2) and set to 'False' to have all data imported with IP Units (Farenheit and BTU/ft2).  The default is set to 'True' for SI.
        legendPar_: Optional legend parameters from the Ladybug "Legend Parameters" component.
        runIt_: Set boolean to "True" to run the component and import THERM results to Rhino/GH.
    Returns:
        readMe!: ...
        meshValues: The numerical meshValues of the results in either degrees C or W/m2 (depending on the dataYpe_ input of this component).
        meshPoints: The meshPoints of the mesh that THERM has generated.
        coloredMesh: A mesh of the original THERM geometry that is colored with the results.
        legend: A legend for the coloredMesh above. Connect this output to a grasshopper "Geo" component in order to preview this legend separately in the Rhino scene.  
        legendBasePt: The legend base point, which can be used to move the legend in relation to the newMesh with the grasshopper "move" component.
        title: The title text of the results.  Hook this up to a native Grasshopper 'Geo' component to preview it separately from the other outputs.
        titleBasePt: Point for the placement of the title, which can be used to move the title in relation to the chart with the native Grasshopper "Move" component.
"""

import Rhino as rc
import scriptcontext as sc
import os
import System
import Grasshopper.Kernel as gh
import math

ghenv.Component.Name = 'Honeybee_Read THERM Result'
ghenv.Component.NickName = 'readTHERM'
ghenv.Component.Message = 'VER 0.0.59\nFEB_03_2016'
ghenv.Component.IconDisplayMode = ghenv.Component.IconDisplayMode.application
ghenv.Component.Category = "Honeybee"
ghenv.Component.SubCategory = "11 | THERM"
#compatibleHBVersion = VER 0.0.56\nDEC_31_2015
#compatibleLBVersion = VER 0.0.59\nFEB_01_2015
try: ghenv.Component.AdditionalHelpFromDocStrings = "4"
except: pass


w = gh.GH_RuntimeMessageLevel.Warning
e = gh.GH_RuntimeMessageLevel.Error



def checkTheInputs():
    lb_preparation = sc.sticky["ladybug_Preparation"]()
    
    #Check if the result file exists.
    if not os.path.isfile(_resultFile):
        warning = "Cannot find the result file. Check the location of the file on your machine. \n If it is not there, make sure that you have opened THERM and run your .thmx file before using this component. \n Also, before you run the file in THERM, make sure that you go to Options > Preferences > Simulation and check 'Save Conrad results file (.O).'"
        print warning
        ghenv.Component.AddRuntimeMessage(w, warning)
        return -1
    
    #If there is a thermFile_ connected, check to make sure it exists and contains transformation data.
    planeReorientation = None
    unitsScale = None
    rhinoOrig = None
    if thermFile_ != None:
        if not os.path.isfile(thermFile_):
            warning = "Cannot find the THERM file at the thermFile_. \n Result geometry will not be imported to the location of the original Rhino geometry."
            print warning
            ghenv.Component.AddRuntimeMessage(w, warning)
        else:
            #Try to extract the transformations from the file header.
            thermFi = open(thermFile_, 'r')
            for lineCount, line in enumerate(thermFi):
                if '<Notes>' in line and '</Notes>' in line:
                    if 'RhinoUnits-' in line and 'RhinoOrigin-' in line and 'RhinoXAxis-' in line:
                        origRhinoUnits = line.split(',')[0].split('RhinoUnits-')[-1]
                        origRhinoOrigin = line.split('),')[0].split('RhinoOrigin-(')[-1].split(',')
                        origRhinoXaxis = line.split('),')[1].split('RhinoXAxis-(')[-1].split(',')
                        origRhinoYaxis = line.split('),')[2].split('RhinoYAxis-(')[-1].split(',')
                        origRhinoZaxis = line.split(')</Notes>')[0].split('RhinoZAxis-(')[-1].split(',')
                        
                        rhinoOrig = rc.Geometry.Point3d(float(origRhinoOrigin[0]), float(origRhinoOrigin[1]), float(origRhinoOrigin[2]))
                        thermPlane = rc.Geometry.Plane(rhinoOrig, rc.Geometry.Plane.WorldXY.XAxis, rc.Geometry.Plane.WorldXY.YAxis)
                        basePlane = rc.Geometry.Plane(rhinoOrig, rc.Geometry.Vector3d(float(origRhinoXaxis[0]), float(origRhinoXaxis[1]), float(origRhinoXaxis[2])), rc.Geometry.Vector3d(float(origRhinoYaxis[0]), float(origRhinoYaxis[1]), float(origRhinoYaxis[2])))
                        basePlaneNormal = rc.Geometry.Vector3d(float(origRhinoZaxis[0]), float(origRhinoZaxis[1]), float(origRhinoZaxis[2]))
                        planeReorientation = rc.Geometry.Transform.ChangeBasis(basePlane, thermPlane)
                        
                        conversionFactor = lb_preparation.checkUnits()
                        conversionFactor = 1/conversionFactor
                        unitsScale = rc.Geometry.Transform.Scale(rc.Geometry.Plane.WorldXY, conversionFactor, conversionFactor, conversionFactor)
                    else:
                        warning = "Cannot find the transformation data in the header of the THERM file at the thermFile_. \n Result geometry will not be imported to the location of the original Rhino geometry."
                        print warning
                        ghenv.Component.AddRuntimeMessage(w, warning)
            thermFi.close()
    
    #If there is a uFactorFile_ connected, check to make sure it exists and contains the U-Factor data.
    uFactorNames = []
    uFactors = []
    if uFactorFile_ != None:
        if not os.path.isfile(uFactorFile_):
            warning = "Cannot find the U-Factor file. Make sure that you have saved your THERM file after simulating it to ensure that this file is generated. \n Also, Before you run the file in THERM, make sure that you go to Options > Preferences > Preferences and check 'Automatic XML Export on Save' in order to enure that your THERM simulation writes this uFactorFile. \n No values will be output from the uFactors or uFactorTags."
            print warning
            ghenv.Component.AddRuntimeMessage(w, warning)
        else:
            #Try to extract the U-factors from the file header.
            uFacFile = open(uFactorFile_, 'r')
            tagTrigger = False
            tagName = ''
            for lineCount, line in enumerate(uFacFile):
                if '<Tag>' in line and '</Tag>' in line:
                    tagTrigger = True
                    tagName = line.split('<Tag>')[-1].split('</Tag>')[0]
                elif '</U-factors>' in line: tagTrigger = False
                elif tagTrigger == True:
                    if '<Length-type>' in line:
                        lengthStr = line.split('<Length-type>')[-1].split('</Length-type>')[0]
                        uFactorNames.append(tagName + ' - ' + lengthStr)
                    if '<U-factor value="NA" />' in line:
                        del uFactorNames[-1]
                    if '<U-factor units="W/m2-K" value="' in line:
                        uFactor = float(line.split('<U-factor units="W/m2-K" value="')[-1].split('" />')[0])
                        uFactors.append(uFactor)
            uFacFile.close()
        if SIorIP_ == False:
            for count, val in enumerate(uFactors): uFactors[count] = val*0.316998331
    
    #If there is an input for dataType_, check to make sure that it makes sense.
    dataType = 0
    if dataType_ != None:
        if dataType_ == 0 or dataType_ == 1: dataType = dataType_
        else:
            warning = "dataType_ must be either 0 or 1.'"
            print warning
            ghenv.Component.AddRuntimeMessage(e, warning)
            return -1
    
    return dataType, planeReorientation, unitsScale, rhinoOrig, uFactorNames, uFactors


def main(dataType, planeReorientation, unitsScale, rhinoOrig):
    #Import the class.
    lb_preparation = sc.sticky["ladybug_Preparation"]()
    lb_visualization = sc.sticky["ladybug_ResultVisualization"]()
    
    #Create lists to be filled up with data from the file.
    pointData = []
    elementData = []
    meshValues = []
    disjointedIndices = []
    pointTrigger = False
    elementTrigger = False
    meshValuesTrigger = False
    disjointTrigger = False
    
    #Parse the result file into the lists.
    resultFile = open(_resultFile, 'r')
    for lineCount, line in enumerate(resultFile):
        if 'node number    x1-coordinate     x2-coordinate      temperature' in line: pointTrigger = True
        elif 'elem. no.   i      j      k      l      matl. no.    matl. angle       volume' in line: elementTrigger = True
        elif 'node    temperature          x-flux         y-flux' in line: meshValuesTrigger = True
        elif 'warning --- mesh is disjoint at these nodes' in line: disjointTrigger = True
        elif '********************************************************************************' in line:
            pointTrigger = False
            elementTrigger = False
            disjointTrigger = False
        elif 'Boundary Element Edge Data:' in line: meshValuesTrigger = False
        elif pointTrigger == True:
            try:
                coordList = []
                intCount = 0
                columns = line.split(' ')
                for col in columns:
                    if col != '':
                        intCount += 1
                        if intCount > 1 and intCount <4: coordList.append(float(col))
                if coordList != []:
                    xCoord = float(coordList[0])
                    yCoord = float(coordList[1])
                    pointData.append(rc.Geometry.Point3d(xCoord, yCoord, 0))
            except: pass
        elif elementTrigger == True:
            try:
                elementList = []
                intCount = 0
                columns = line.split(' ')
                for col in columns:
                    if col != '':
                        intCount += 1
                        if intCount > 1 and intCount <6: elementList.append(int(col))
                if elementList != []: elementData.append(elementList)
            except: pass
        elif meshValuesTrigger == True:
            try:
                valList = []
                intCount = 0
                columns = line.split(' ')
                for col in columns:
                    if col != '':
                        intCount += 1
                        if intCount > 1 and intCount <5: valList.append(float(col))
                if valList != []:
                    if dataType == 0: meshValues.append(valList[0])
                    else: meshValues.append(math.sqrt((math.pow(float(valList[1]),2))+(math.pow(float(valList[2]),2))))
                    xCoord = float(coordList[0])
                    yCoord = float(coordList[1])
                    pointData.append(rc.Geometry.Point3d(xCoord, yCoord, 0))
            except: pass
        elif disjointTrigger == True:
            indexList = []
            columns = line.split(' ')
            for col in columns:
                if col != '':
                    try:
                        disind = int(col)
                        if len(pointData) > 10000:
                            indexList.append(int(str(disind)[:5]))
                            indexList.append(int(str(disind)[5:]))
                        else: indexList.append(disind)
                    except: pass
            if indexList != []: disjointedIndices.extend(indexList)
    
    resultFile.close()
    
    #Remove any disjointed meshPoints from each list.
    for count, index in enumerate(disjointedIndices):
        del pointData[index-1-count]
        del meshValues[index-1-count]
    
    for point in pointData: point.Transform(unitsScale)
    #If we have a Rhino transform from the thermFile, transform all of the point data.
    if planeReorientation != None:
        for point in pointData:
            point.Transform(planeReorientation)
        thermBB = rc.Geometry.BoundingBox(pointData)
        thermOrigin = rc.Geometry.BoundingBox.Corner(thermBB, True, True, True)
        vecDiff = rc.Geometry.Point3d.Subtract(rhinoOrig, thermOrigin)
        planeTransl = rc.Geometry.Transform.Translation(vecDiff.X, vecDiff.Y, vecDiff.Z)
        for point in pointData:
            point.Transform(planeTransl)
    
    #Build up a mesh from the point and element data.
    feMesh = rc.Geometry.Mesh()
    for point in pointData:
        feMesh.Vertices.Add(point)
    for face in elementData:
        feMesh.Faces.AddFace(face[0]-1, face[1]-1, face[2]-1, face[3]-1)
    
    #If IP units have been requested, convert everything.
    if SIorIP_ == False:
        if dataType == 0:
            for count, val in enumerate(meshValues): meshValues[count] = val*(9/5) + 32
        else:
            for count, val in enumerate(meshValues): meshValues[count] = val*0.316998331
    
    #Color the mesh with the data and create a legend/title.
    #Read the legend parameters.
    lowB, highB, numSeg, customColors, legendBasePoint, legendScale, legendFont, legendFontSize, legendBold, decimalPlaces, removeLessThan = lb_preparation.readLegendParameters(legendPar_, False)
    if len(legendPar_) == 0 or legendPar_[3] == []: customColors = lb_visualization.gradientLibrary[20]
    colors = lb_visualization.gradientColor(meshValues, lowB, highB, customColors)
    feMesh.VertexColors.CreateMonotoneMesh(System.Drawing.Color.Gray)
    for count, col in enumerate(colors):
        try: feMesh.VertexColors[count] = col
        except: pass
    
    #Get the bounding box of the secene that will work in 3 dimensions.
    meshBB = rc.Geometry.BoundingBox(pointData)
    finalLegBasePt = meshBB.Corner(False, True, True)
    meshBox = rc.Geometry.Box(meshBB)
    bbDim = [meshBox.X[1]-meshBox.X[0], meshBox.Y[1]-meshBox.Y[0], meshBox.Z[1]-meshBox.Z[0]]
    bbDim.sort()
    plane = rc.Geometry.Plane.WorldXY
    plane.Origin = rc.Geometry.BoundingBox.Corner(meshBB, True, True, True)
    theInt =  rc.Geometry.Interval(0, bbDim[-1])
    sceneBox = rc.Geometry.Box(plane, theInt, theInt, theInt)
    sceneBox = sceneBox.ToBrep()
    
    #Create the legend.
    lb_visualization.calculateBB([sceneBox], True)
    if SIorIP_ == False:
        if dataType == 0: legendTitle = 'F'
        else: legendTitle = 'BTU/ft2'
    else:
        if dataType == 0: legendTitle = 'C'
        else: legendTitle = 'W/m2'
    if legendBasePoint == None:
        legendBasePoint = finalLegBasePt
        lst = list(lb_visualization.BoundingBoxPar)
        lst[0] = legendBasePoint
        lb_visualization.BoundingBoxPar = tuple(lst)
    legendSrfs, legendText, legendTextCrv, textPt, textSize = lb_visualization.createLegend(meshValues, lowB, highB, numSeg, legendTitle, lb_visualization.BoundingBoxPar, legendBasePoint, legendScale, legendFont, legendFontSize, legendBold, decimalPlaces, removeLessThan)
    legendColors = lb_visualization.gradientColor(legendText[:-1], lowB, highB, customColors)
    legendSrfs = lb_visualization.colorMesh(legendColors, legendSrfs)
    
    #Create title.
    if dataType == 0: titleTxt = '\n\nTemperature \n' 'THERM Simulation'
    else: titleTxt = '\n\nHeat Flow \n' 'THERM Simulation'
    titleBasePt = lb_visualization.BoundingBoxPar[5]
    titleTextCurve = lb_visualization.text2srf([titleTxt], [titleBasePt], legendFont, textSize, legendBold)
    
    
    return meshValues, pointData, feMesh, [legendSrfs] + lb_preparation.flattenList(legendTextCrv), legendBasePoint, lb_preparation.flattenList(titleTextCurve), titleBasePt




#If Ladybug is not flying or is an older version, give a warning.
initCheck = True

#Ladybug check.
if not sc.sticky.has_key('ladybug_release') == True:
    initCheck = False
    print "You should first let Ladybug fly..."
    ghenv.Component.AddRuntimeMessage(w, "You should first let Ladybug fly...")
else:
    try:
        if not sc.sticky['ladybug_release'].isCompatible(ghenv.Component): initCheck = False
        if sc.sticky['ladybug_release'].isInputMissing(ghenv.Component): initCheck = False
    except:
        initCheck = False
        warning = "You need a newer version of Ladybug to use this compoent." + \
        "Use updateLadybug component to update userObjects.\n" + \
        "If you have already updated userObjects drag Ladybug_Ladybug component " + \
        "into canvas and try again."
        ghenv.Component.AddRuntimeMessage(w, warning)


#If the intital check is good, run the component.
if initCheck and _resultFile and _runIt:
    initInputs = checkTheInputs()
    if initInputs != -1:
        dataType, planeReorientation, unitsScale, rhinoOrig, uFactorTags, uFactors = initInputs
        result = main(dataType, planeReorientation, unitsScale, rhinoOrig)
        if result != -1:
            meshValues, meshPoints, coloredMesh, legend, legendBasePt, title, titleBasePt = result

ghenv.Component.Params.Output[4].Hidden = True
ghenv.Component.Params.Output[8].Hidden = True
ghenv.Component.Params.Output[10].Hidden = True