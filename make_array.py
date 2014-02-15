# Hacky code to create an array of parts in Eagle. Great way to make an LED matrix!
# By Matt Mets


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
parser.add_argument('-spacingX', metavar='X spacing', dest='spacingX', type=int, default=10,
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


# Remove any part whose name ends in _, and store them for later duplication
schematicParts = schematicDrawing.find("parts")
schematicMatrixParts = ET.Element("parts")
for part in reversed(schematicParts):
    if part.get('name').endswith("_"):
        schematicParts.remove(part)
        schematicMatrixParts.append(part)

# Remove any instance whose name ends in _, and store them for later duplication
# Note that we are only considering things on the first schematic sheet!
schematicInstances = schematicDrawing.find(".//instances")
schematicMatrixInstances = ET.Element("instance")
for instance in reversed(schematicInstances):
    if instance.get('part').endswith("_"):
        schematicInstances.remove(instance)
        schematicMatrixInstances.append(instance)

# Remove any net whose name ends in IN_ or OUT_, and store them for later duplication
# Note that we are only considering things on the first schematic sheet!
schematicNets = schematicDrawing.find(".//nets")
schematicInputNets = ET.Element("nets")
schematicOutputNets = ET.Element("nets")
for net in reversed(schematicNets):
    if net.get('name').endswith("IN_"):
        schematicNets.remove(net)
        schematicInputNets.append(net)
    elif net.get('name').endswith("OUT_"):
        schematicNets.remove(net)
        schematicOutputNets.append(net)


##################################################################################
######## Board inspection phase
##################################################################################

Board = ET.parse(boardName)
BoardDrawing = Board.getroot().find("drawing").find("board")

# Remove any element whose name ends in _, and store them for later duplication 
boardElements = BoardDrawing.find("elements")
boardMatrixElements = ET.Element("elements")
for element in reversed(boardElements):
    if element.get('name').endswith("_"):
        boardElements.remove(element)
        boardMatrixElements.append(element)


# Remove any signal whose name ends in IN_ or OUT_, and store them for later duplication
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

def createSchematicParts(position):
    """ Create all the Schematic parts needed for this position
    
    For each of the elements that were in the original board file,
    create a copy of the element at the new location

    """
    for part in schematicMatrixParts:
        # Create a copy of them
        newPart = copy.deepcopy(part)

        # Adjust the name
    	newPart.set('name', newPart.get('name') + "%i"%(position))

        schematicParts.append(newPart)

def createSchematicInstances(position):
    """ Create all of the schematic instances needed for this position

    For each of the elements that were in the original board file,
    create a copy of the element at the new location

    """
    for sourceInstance in schematicMatrixInstances:
        # Create a copy of them
        newInstance = copy.deepcopy(sourceInstance)

        # Adjust the name
        newInstance.set('part', sourceInstance.get('part') + "%i"%(position))

        # Adjust the x and y position
        translateSchematicElement(newInstance, position)

        schematicInstances.append(newInstance)


def translateSchematicElement(element, position):
    """ Translate a schematic element to a new location

    Translate a schematic element to a new location, based on it's position number

    """
    xOffset = ((position-1)%args.cols)*args.schematicSpacingX
    yOffset = ((position-1)/args.cols)*args.schematicSpacingY

    if(element.get('x') != None):
        element.set('x', str(float(element.get('x')) + xOffset))
    if(element.get('y') != None):
        element.set('y', str(float(element.get('y')) + yOffset))

    if(element.get('x1') != None):
        element.set('x1', str(float(element.get('x1')) + xOffset))
    if(element.get('y1') != None):
        element.set('y1', str(float(element.get('y1')) + yOffset))

    if(element.get('x2') != None):
        element.set('x2', str(float(element.get('x2')) + xOffset))
    if(element.get('y2') != None):
        element.set('y2', str(float(element.get('y2')) + yOffset))

def updateSchematicNets(position):
    """ Update non-matrix nets

    For each non-matrix net that has a segment with a matrixed position,
    create a new copy of that segment and append it to the net.

    """
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
                        pinref.set('part', pinref.get('part') + "%i"%(position))
                for item in newSegment.iter():
                    translateSchematicElement(item, position)
                 
                net.append(newSegment)


def createSchematicInterconnectNets(position):
    """ Create input, output, and interconnect nets for the new part
    """

    # For the first position, the matrixed signals (nIN_) are replaced with inputs to the matrix
    if position == 1:
        for net in schematicInputNets:
            newNet = copy.deepcopy(net)
            newNet.set('name', net.get('name')[:-1])
            for pinref in newNet.iter('pinref'):
                if pinref.get('part').endswith('_'):
                    pinref.set('part', pinref.get('part') + "%i"%(position))
            for wire in newNet.iter('wire'):
                wire = translateSchematicElement(wire, position)
            for label in newNet.iter('label'):
                label = translateSchematicElement(label, position)

            # If a non-matrix part references the new input net, just append the segments
            # from the input to the existing net.
            shouldCreate = True
            for existingNet in schematicNets:
                if existingNet.get('name') == newNet.get('name'):
                    shouldCreate = False
                    for segment in newNet.iter('segment'):
                        existingNet.append(segment)
            # Otherwise, add the input net to the schematic.
            if shouldCreate:
                schematicNets.append(newNet)

    # For positions besides the first one, their inputs and output signals (nIN_ and nOUT_) are replaced
    # by new nMID_x signals, which connect the output of the previous position to the input of the
    # current position.
    if position > 1:
        for inputNet in schematicInputNets:
            for outputNet in schematicOutputNets:
                # Find a matching input and output pair
                if inputNet.get('name')[:-3] == outputNet.get('name')[:-4]:
                    # Create a new net, based on the matched input net
                    newNet = copy.deepcopy(inputNet)
                    newNet.set('name', inputNet.get('name')[:-3] + "MID_%i"%(position-1))
                    # Update the pinrefs so that they point to the new parts
                    for pinref in newNet.iter('pinref'):
                         if pinref.get('part').endswith('_'):
                             pinref.set('part', pinref.get('part') + "%i"%(position))
                    # And shift all wires to the correct positions.
                    for wire in newNet.iter('wire'):
                         wire = translateSchematicElement(wire, position)
                    for label in newNet.iter('label'):
                         label = translateSchematicElement(label, position)

                    # Copy in any segments from the matched output net,
                    # after translating them to the correct positions.
                    for segment in schematicOutputNets.iter('segment'):
                        newSegment = copy.deepcopy(segment)
                        for pinref in newSegment.iter('pinref'):
                             if pinref.get('part').endswith('_'):
                                 pinref.set('part', pinref.get('part') + "%i"%(position - 1))
                        # And shift all wires to the correct positions.
                        for wire in newSegment.iter('wire'):
                             wire = translateSchematicElement(wire, position - 1)
                        for label in newSegment.iter('label'):
                             label = translateSchematicElement(label, position - 1)

                        newNet.append(newSegment)

                    schematicNets.append(newNet)

    # For the last position, the matrixed signals (nOUT_) are replaced with outputs from the matrix
    if position == lastPosition:
        for net in schematicOutputNets:
            newNet = copy.deepcopy(net)
            newNet.set('name', net.get('name')[:-1])
            for pinref in newNet.iter('pinref'):
                 if pinref.get('part').endswith('_'):
                     pinref.set('part', pinref.get('part') + "%i"%(position))
            for wire in newNet.iter('wire'):
                 wire = translateSchematicElement(wire, position)
            for label in newNet.iter('label'):
                 label = translateSchematicElement(label, position)

            # If a non-matrix part references the new output net, just append the segments
            # from the output to the existing net.
            shouldCreate = True
            for existingNet in schematicNets:
                if existingNet.get('name') == newNet.get('name'):
                    shouldCreate = False
                    for segment in newNet.iter('segment'):
                        existingNet.append(segment)
            # Otherwise, add the input net to the schematic.
            if shouldCreate:
                schematicNets.append(newNet)


##################################################################################
######## Board creation functions
##################################################################################

def createBoardElements(position):
    """ Create all of the board elements needed for this position

    For each of the elements that were in the original board file,
    create a copy of the element at the new location

    """
    for element in boardMatrixElements:
        # Create a copy of the element
        newElement = copy.deepcopy(element)

        # Adjust the name
    	newElement.set('name', newElement.get('name') + "%i"%(position))

        # Adjust the x and y position
        translateBoardElement(newElement, position)

        boardElements.append(newElement)

def translateBoardElement(element, position):
    """ Move a board element into position

    Translate a board element to a new location, based on it's position number

    """
    xOffset = ((position-1)%args.cols)*args.spacingX
    yOffset = ((position-1)/args.cols)*args.spacingY

    if(element.get('x') != None):
        element.set('x', str(float(element.get('x')) + xOffset))
    if(element.get('y') != None):
        element.set('y', str(float(element.get('y')) + yOffset))

    if(element.get('x1') != None):
        element.set('x1', str(float(element.get('x1')) + xOffset))
    if(element.get('y1') != None):
        element.set('y1', str(float(element.get('y1')) + yOffset))

    if(element.get('x2') != None):
        element.set('x2', str(float(element.get('x2')) + xOffset))
    if(element.get('y2') != None):
        element.set('y2', str(float(element.get('y2')) + yOffset))


def updateBoardSignals(position):
    """" Hook the new element up to any non-matrix signals

    For each non-matrix signal that had a matrixed contactref entry, add the new
    element to it. This is mostly for power and ground, things that all of the
    elements share in parallel.

    """
    for signal in boardSignals:
        for contactref in signal.iter('contactref'):
            if contactref.get('element').endswith('_'):
                 newContactref = copy.deepcopy(contactref)
                 newContactref.set('element', contactref.get('element') + "%i"%(position))
                 signal.append(newContactref)


def createBoardInterconnectSignals(position):
    """ Create input, output, and interconnect signals for the new part
    """

    # For the first position, the matrixed signals (nIN_) are replaced with inputs to the matrix
    if position == 1:
        for signal in boardInputSignals:
            newSignal = copy.deepcopy(signal)
            newSignal.set('name', signal.get('name')[:-1])
            for contactref in newSignal.iter('contactref'):
                 contactref.set('element', contactref.get('element') + "%i"%(position))

            # If a non-matrix part references the new signal, just append the contactrefs
            # from the new signal to the existing signal.
            # Note: At some point, maybe we care about wires/etc here?
            shouldCreate = True
            for existingSignal in boardSignals:
                if existingSignal.get('name') == newSignal.get('name'):
                    shouldCreate = False
                    for contactref in newSignal.iter('contactref'):
                        existingSignal.append(contactref)
            # Otherwise, add the new signal to the board.
            if shouldCreate:
                boardSignals.append(newSignal)

    # For positions besides the first one, their inputs and output signals (nIN_ and nOUT_) are replaced
    # by new nMID_x signals, which connect the output of the previous position to the input of the
    # current position.
    if position > 1:
        for inputSignal in boardInputSignals:
            for outputSignal in boardOutputSignals:
                # Find a matching input and output pair
                if inputSignal.get('name')[:-3] == outputSignal.get('name')[:-4]:
                    # Create a new signal, based on the matched input signal
                    newSignal = copy.deepcopy(inputSignal)
                    newSignal.set('name', newSignal.get('name')[:-3] + "MID_%i"%(position-1))
                    # Modify all input contact refs to point to the current position
                    for contactref in newSignal.iter('contactref'):
                        contactref.set('element', contactref.get('element') + "%i"%(position))
                    # Modify all output contact refs to point to the previous position
                    for contactref in outputSignal.iter('contactref'):
                        newContactref = copy.deepcopy(contactref)
                        newContactref.set('element', contactref.get('element') + "%i"%(position-1))
                        newSignal.append(newContactref)
                    boardSignals.append(newSignal)


    # For the last position, the matrixed signals (nOUT_) are replaced with outputs from the matrix
    if position == lastPosition:
        for signal in boardOutputSignals:
            newSignal = copy.deepcopy(signal)
            newSignal.set('name', signal.get('name')[:-1])
            for contactref in newSignal.iter('contactref'):
                 contactref.set('element', contactref.get('element') + "%i"%(position))

            # If a non-matrix part references the new signal, just append the contactrefs
            # from the new signal to the existing signal.
            # Note: At some point, maybe we care about wires/etc here?
            shouldCreate = True
            for existingSignal in boardSignals:
                if existingSignal.get('name') == newSignal.get('name'):
                    shouldCreate = False
                    for contactref in newSignal.iter('contactref'):
                        existingSignal.append(contactref)
            # Otherwise, add the new signal to the board.
            if shouldCreate:
                boardSignals.append(newSignal)


##################################################################################
######## New part creation phase
##################################################################################


# Create a new part for each matrix position, that is:
# * Shifted in the x and y directions
# * Renamed according to it's instantion number
lastPosition = args.rows*args.cols
for position in range(1, lastPosition + 1):

    # Create copies of the schematic parts and instances, update existing nets, and add
    # intermediate nets.
    createSchematicParts(position)
    createSchematicInstances(position)
    updateSchematicNets(position)
    createSchematicInterconnectNets(position)

    # Create copies of the board elements, update existing signals, and add intermediate
    # signals to transfer data between positions
    createBoardElements(position)
    updateBoardSignals(position)
    createBoardInterconnectSignals(position)


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
