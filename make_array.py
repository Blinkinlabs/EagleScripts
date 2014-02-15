
import xml.etree.ElementTree as ET
import copy
import argparse

parser = argparse.ArgumentParser(description='Create a matrix of parts for Eagle PCB. Tested with Eagle 6.5.0.')
parser.add_argument('filepath', metavar='in-file',
                   help='Design name (without extension)')
parser.add_argument('-r', metavar='rows', dest='rows', type=int, default=4,
                   help='Number of rows in the matrix')
parser.add_argument('-c', metavar='cols', dest='cols', type=int, default=4,
                   help='Number of columns in the matrix')
parser.add_argument('-spacingX', metavar='X spacing',  dest='spacingX', type=int, default=10,
                   help='Amount of space between rows of parts on the PCB, in the default board units')
parser.add_argument('-spacingY', metavar='Y spacing', dest='spacingY', type=int, default=-10,
                   help='Amount of space between columns of parts on the PCB, in the default board units')
parser.add_argument('-schematicSpacingX', metavar='Schematix X spacing', dest='schematicSpacingX', type=int, default=40,
                   help='Amount of space between rows of parts in the schematic, in the default board units')
parser.add_argument('-schematicSpacingY', metavar='Schematix Y spacing', dest='schematicSpacingY', type=int, default=-40,
                   help='Amount of space between columns of parts in the schematic, in the default board units')

args = parser.parse_args()


designName = args.filepath
boardName = designName + ".brd"
outputBoardName = designName + "matrix" + ".brd"
schematicName = designName + ".sch"
outputSchematicName = designName + "matrix" + ".sch"





##################################################################################
######## Schematic inspection phase
##################################################################################

Schematic= ET.parse(schematicName)
schematicDrawing = Schematic.getroot().find("drawing").find("schematic")


# Separate out the 
# Remove any part whose name ends in _, and store them for later copying
schematicParts = schematicDrawing.find("parts")
schematicMatrixParts = ET.Element("parts")
for part in reversed(schematicParts):
  if part.get('name').endswith("_"):
    schematicParts.remove(part)
    schematicMatrixParts.append(part)

# Remove any instance whose name ends in _, and store them for later copying
# Note that we are only considering things on the first schematic sheet!
schematicInstances = schematicDrawing.find(".//instances")
schematicMatrixInstances = ET.Element("instance")
for instance in reversed(schematicInstances):
  if instance.get('part').endswith("_"):
    schematicInstances.remove(instance)
    schematicMatrixInstances.append(instance)

# Remove any net whose name ends in IN_ or OUT_, and store them for later copying
# Note that we are only considering things on the first schematic sheet!
schematicNets = schematicDrawing.find(".//nets")
schematicInputNets = ET.Element("nets")
schematicOutputNets = ET.Element("nets")
for net in reversed(schematicNets):
  if net.get('name').endswith("IN_"):
    schematicNets.remove(net)
    schematicInputNets.append(net)
  if net.get('name').endswith("OUT_"):
    schematicNets.remove(net)
    schematicOutputNets.append(net)


##################################################################################
######## Board inspection phase
##################################################################################

Board = ET.parse(boardName)
BoardDrawing = Board.getroot().find("drawing").find("board")

# Remove any element whose name ends in _, and store them for later copying
boardElements = BoardDrawing.find("elements")
boardMatrixElements = ET.Element("elements")
for element in reversed(boardElements):
  if element.get('name').endswith("_"):
    boardElements.remove(element)
    boardMatrixElements.append(element)


# Remove any signal whose name ends in IN_ or OUT_, and store them for later copying
boardSignals = BoardDrawing.find("signals")
boardInputSignals = ET.Element("signals")
boardOutputSignals = ET.Element("signals")
for signal in reversed(boardSignals):
  if signal.get('name').endswith("IN_"):
    boardSignals.remove(signal)
    boardInputSignals.append(signal)
  if signal.get('name').endswith("OUT_"):
    boardSignals.remove(signal)
    boardOutputSignals.append(signal)


##################################################################################
######## Schematic creation functions
##################################################################################

def createSchematicParts(instance):
  """ Create all the Schematic parts needed for this instance
  
  For each of the elements that were in the original board file,
  create a copy of the element at the new location

  """
  for part in schematicMatrixParts:
    # Create a copy of them
    newPart = copy.deepcopy(part)

    # Adjust the name
    renameElement(newPart, instance)

    schematicParts.append(newPart)

def createSchematicInstances(instance):
  """ Create all of the schematic instances needed for this instance

  For each of the elements that were in the original board file,
  create a copy of the element at the new location

  """
  for sourceInstance in schematicMatrixInstances:
    # Create a copy of them
    newInstance = copy.deepcopy(sourceInstance)

    # Adjust the name
    newInstance.set('part', sourceInstance.get('part') + "%i"%(instance))

    # Adjust the x and y position
    translateSchematicElement(newInstance, instance)

    schematicInstances.append(newInstance)


def translateSchematicElement(part, instance):
  # Translate a schematic element to a new location, based on it's instance number
  xOffset = ((instance-1)%args.cols)*args.schematicSpacingX
  yOffset = ((instance-1)/args.cols)*args.schematicSpacingY

  if(part.get('x') != None):
    part.set('x', str(float(part.get('x')) + xOffset))
  if(part.get('y') != None):
    part.set('y', str(float(part.get('y')) + yOffset))

  if(part.get('x1') != None):
    part.set('x1', str(float(part.get('x1')) + xOffset))
  if(part.get('y1') != None):
    part.set('y1', str(float(part.get('y1')) + yOffset))

  if(part.get('x2') != None):
    part.set('x2', str(float(part.get('x2')) + xOffset))
  if(part.get('y2') != None):
    part.set('y2', str(float(part.get('y2')) + yOffset))

  return part

def updateSchematicNets(instance):
  # For each non-matrix net that has a segment with a matrixed instance,
  # create a new copy of that segment and append it to the net.
  for net in schematicNets:
    for segment in net.iter('segment'):
      shouldCopy = False
      for pinref in segment.iter('pinref'):
        if pinref.get('part').endswith('_'):
           shouldCopy = True
      if shouldCopy:
        newSegment = copy.deepcopy(segment)
        for pinref in newSegment.iter('pinref'):
          if pinref.get('part').endswith('_'):
            pinref.set('part', pinref.get('part') + "%i"%(instance))
        for item in newSegment.iter():
          translateSchematicElement(item, instance)
         
        net.append(newSegment)


def createSchematicInterconnectNets(instance):
  # For the first instance, the matrixed signals (nIN_) are replaced with inputs to the matrix
  if instance == 1:
    for net in schematicInputNets:
      newNet = copy.deepcopy(net)
      newNet.set('name', net.get('name')[:-1])
      for pinref in newNet.iter('pinref'):
        if pinref.get('part').endswith('_'):
          pinref.set('part', pinref.get('part') + "%i"%(instance))
      for wire in newNet.iter('wire'):
        wire = translateSchematicElement(wire, instance)
      for label in newNet.iter('label'):
        label = translateSchematicElement(label, instance)
      schematicNets.append(newNet)

  # For instances besides the first one, their inputs and output signals (nIN_ and nOUT_) are replaced
  # by new nMID_x signals, which connect the output of the previous instance to the input of the
  # current instance.
  if instance > 1:
    for inputNet in schematicInputNets:
      for outputNet in schematicOutputNets:
        # Find a matching input and output pair
        if inputNet.get('name')[:-3] == outputNet.get('name')[:-4]:
          # Create a new net, based on the matched input net
          newNet = copy.deepcopy(inputNet)
          newNet.set('name', inputNet.get('name')[:-3] + "MID_%i"%(instance-1))
          # Update the pinrefs so that they point to the new parts
          for pinref in newNet.iter('pinref'):
             if pinref.get('part').endswith('_'):
               pinref.set('part', pinref.get('part') + "%i"%(instance))
          # And shift all wires to the correct positions.
          for wire in newNet.iter('wire'):
             wire = translateSchematicElement(wire, instance)
          for label in newNet.iter('label'):
             label = translateSchematicElement(label, instance)

          # Copy in any segments from the matched output net,
          # after translating them to the correct positions.
          for segment in schematicOutputNets.iter('segment'):
            newSegment = copy.deepcopy(segment)
            for pinref in newSegment.iter('pinref'):
               if pinref.get('part').endswith('_'):
                 pinref.set('part', pinref.get('part') + "%i"%(instance - 1))
            # And shift all wires to the correct positions.
            for wire in newSegment.iter('wire'):
               wire = translateSchematicElement(wire, instance - 1)
            for label in newSegment.iter('label'):
               label = translateSchematicElement(label, instance - 1)

            newNet.append(newSegment)

          schematicNets.append(newNet)

  # For the last instance, the matrixed signals (nOUT_) are replaced with outputs from the matrix
  if instance == lastInstance:
    for net in schematicOutputNets:
      newNet = copy.deepcopy(net)
      newNet.set('name', net.get('name')[:-1])
      for pinref in newNet.iter('pinref'):
         if pinref.get('part').endswith('_'):
           pinref.set('part', pinref.get('part') + "%i"%(instance))
      for wire in newNet.iter('wire'):
         wire = translateSchematicElement(wire, instance)
      for label in newNet.iter('label'):
         label = translateSchematicElement(label, instance)
      schematicNets.append(newNet)


##################################################################################
######## Board creation functions
##################################################################################

def createBoardElements(instance):
  # For each of the elements that were in the original board file,
  # create a copy of the element at the new location
  for element in boardMatrixElements:
    # Create a copy of them
    newElement = copy.deepcopy(element)

    # Adjust the name
    #newElement.set('name', element.get('name') + "%i"%(instance))
    renameElement(newElement, instance)

    # Adjust the x and y position
    translateBoardElement(newElement, instance)

    boardElements.append(newElement)

def renameElement(part, instance):
  # Rename a board element, based on it's instance number
  # This should result in each consecutive part being named _1, _2, etc.
  # This is shared between the board and schematic, to try and keep them consistent.
  part.set('name', part.get('name') + "%i"%(instance))

def translateBoardElement(part, instance):
  # Translate a board element to a new location, based on it's instance number
  xOffset = ((instance-1)%args.cols)*args.spacingX
  yOffset = ((instance-1)/args.cols)*args.spacingY

  if(part.get('x') != None):
    part.set('x', str(float(part.get('x')) + xOffset))
  if(part.get('y') != None):
    part.set('y', str(float(part.get('y')) + yOffset))

  if(part.get('x1') != None):
    part.set('x1', str(float(part.get('x1')) + xOffset))
  if(part.get('y1') != None):
    part.set('y1', str(float(part.get('y1')) + yOffset))

  if(part.get('x2') != None):
    part.set('x2', str(float(part.get('x2')) + xOffset))
  if(part.get('y2') != None):
    part.set('y2', str(float(part.get('y2')) + yOffset))

  return part


def updateBoardSignals(instance):
  # For each non-matrix signal that had a matrixed contactref entry, add the new
  # element to it. This is mostly for power and ground, things that all of the
  # elements share in parallel.
  for signal in boardSignals:
    for contactref in signal.iter('contactref'):
      if contactref.get('element').endswith('_'):
         newContactref = copy.deepcopy(contactref)
         newContactref.set('element', contactref.get('element') + "%i"%(instance))
         signal.append(newContactref)


def createBoardInterconnectSignals(instance):
  # For the first instance, the matrixed signals (nIN_) are replaced with inputs to the matrix
  if instance == 1:
    for signal in boardInputSignals:
      newSignal = copy.deepcopy(signal)
      newSignal.set('name', signal.get('name')[:-1])
      for contactref in newSignal.iter('contactref'):
         contactref.set('element', contactref.get('element') + "%i"%(instance))
      boardSignals.append(newSignal)

  # For instances besides the first one, their inputs and output signals (nIN_ and nOUT_) are replaced
  # by new nMID_x signals, which connect the output of the previous instance to the input of the
  # current instance.
  if instance > 1:
    for inputSignal in boardInputSignals:
      for outputSignal in boardOutputSignals:
        # Find a matching input and output pair
        if inputSignal.get('name')[:-3] == outputSignal.get('name')[:-4]:
          # Create a new signal, based on the matched input signal
          newSignal = copy.deepcopy(inputSignal)
          newSignal.set('name', newSignal.get('name')[:-3] + "MID_%i"%(instance-1))
          # Modify all input contact refs to point to the current instance
          for contactref in newSignal.iter('contactref'):
            contactref.set('element', contactref.get('element') + "%i"%(instance))
          # Modify all output contact refs to point to the previous instance
          for contactref in outputSignal.iter('contactref'):
            newContactref = copy.deepcopy(contactref)
            newContactref.set('element', contactref.get('element') + "%i"%(instance-1))
            newSignal.append(newContactref)
          boardSignals.append(newSignal)


  # For the last instance, the matrixed signals (nOUT_) are replaced with outputs from the matrix
  if instance == lastInstance:
    for signal in boardOutputSignals:
      newSignal = copy.deepcopy(signal)
      newSignal.set('name', signal.get('name')[:-1])
      for contactref in newSignal.iter('contactref'):
         contactref.set('element', contactref.get('element') + "%i"%(instance))
      boardSignals.append(newSignal)


##################################################################################
######## Matrix loop phase
##################################################################################


# For each position in the matrix, create a new set of elements that is:
# * Shifted in the x and y directions
# * Renamed according to it's X and Y location
for r in range(0, args.rows):
  for c in range(0, args.cols):
    instance = 1 + r*args.cols + c
    lastInstance = args.rows*args.cols

    # Create copies of the schematic parts and instances, update existing nets, and add
    # intermediate nets.
    createSchematicParts(instance)
    createSchematicInstances(instance)
    updateSchematicNets(instance)
    createSchematicInterconnectNets(instance)

    # Create copies of the board elements, update existing signals, and add intermediate
    # signals to transfer data between instances
    createBoardElements(instance)
    updateBoardSignals(instance)
    createBoardInterconnectSignals(instance)


##################################################################################
######## Schematic Cleanup phase
##################################################################################

# Now we need to clean up any segments of non-matrix nets that include a reference to
# a pin on a matrix device.
for net in schematicNets:
  for segment in reversed(list(net)):
    shouldDelete = False
    for pinref in segment.iter('pinref'):
      if pinref.get('part').endswith('_'):
         shouldDelete = True
    if shouldDelete:
      net.remove(segment)

##################################################################################
######## Board Cleanup phase
##################################################################################


# Now we need to clean up any non-matrix signals that include a reference to
# an input matrix element (since we canned those)
for signal in boardSignals:
  for contactref in reversed(list(signal)):
    if contactref.get('element') != None and contactref.get('element').endswith('_'):
      signal.remove(contactref)


##################################################################################
######## Write out phase
##################################################################################

Board.write(outputBoardName, encoding="utf-8", xml_declaration=True)
Schematic.write(outputSchematicName, encoding="utf-8", xml_declaration=True)