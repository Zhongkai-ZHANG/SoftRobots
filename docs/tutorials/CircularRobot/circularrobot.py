import Sofa
from splib.objectmodel import SofaObject, SofaPrefab

import os
path = os.path.dirname(os.path.abspath(__file__))+'/mesh/'


def Target(parentNode):
    target = parentNode.createChild('Target')
    target.createObject('EulerImplicitSolver', firstOrder=True)
    target.createObject('CGLinearSolver', iterations=100, tolerance=1e-4, threshold=1e-4)
    target.createObject('MechanicalObject', name='dofs', showObject=True, showObjectScale=5, drawMode=1, position=[0, 0, 5])
    target.createObject('UncoupledConstraintCorrection')
    return target

def Floor(parentNode, color=[0.5, 0.5, 0.5, 1.], rotation=[90, 0, 180], translation=[50, -22, -100]):
    floor = parentNode.createChild('Floor')
    floor.createObject('MeshObjLoader', name='loader', filename='mesh/square1.obj', scale=250, rotation=rotation, translation=translation)
    floor.createObject('OglModel', src='@loader', color=color)
    floor.createObject('MeshTopology', src='@loader', name='topo')
    floor.createObject('MechanicalObject')
    floor.createObject('TriangleCollisionModel')
    floor.createObject('LineCollisionModel')
    floor.createObject('PointCollisionModel')
    return floor

def Wall(parentNode, color=[0.5, 0.5, 0.5, 1.], rotation=[0, 0, 0], translation=[-200, -271, 100]):
    wall = parentNode.createChild('Wall')
    wall.createObject('MeshObjLoader', name='loader', filename='mesh/square1.obj', scale=250, rotation=rotation, translation=translation)
    wall.createObject('OglModel', src='@loader', color=color)
    return wall

@SofaPrefab
class CircularRobot(SofaObject):
    """ This prefab is implementing a soft circular robot actuated with four cables.

        The prefab is composed of:
        - a visual model
        - a collision model
        - a mechanical model for the deformable structure

        The prefab has the following parameters:
        - youngModulus
        - poissonRatio
        - totalMass

        Example of use in a Sofa scene:

        def createScene(root):
            ...
            circularrobot = CircularRobot(root)
    """

    def __init__(self, parentNode, youngModulus=500, poissonRatio=0.3, totalMass=0.042, inverseMode=True, effectorTarget=None):
        self.inverseMode = inverseMode

        self.node = parentNode.createChild('CircularRobot')
        self.node.createObject('MeshVTKLoader', name="loader", filename=path+"wheel.vtk")
        self.node.createObject('TetrahedronSetTopologyContainer', position='@loader.position', tetrahedra="@loader.tetrahedra")
        self.node.createObject('TetrahedronSetTopologyModifier')
        self.node.createObject('MechanicalObject', name='dofs', showIndices=False, showIndicesScale=4e-5)
        self.node.createObject('UniformMass', totalMass=totalMass)
        self.node.createObject('TetrahedronFEMForceField', poissonRatio=poissonRatio,  youngModulus=youngModulus)

        if inverseMode:
            if effectorTarget is None:
                Sofa.msg_warning("The prefab CircularRobot needs effectorTarget in inverseMode")
            self.node.createObject('BarycentricCenterEffector', limitShiftToTarget=True, maxShiftToTarget=5,
                                    effectorGoal=effectorTarget,
                                    axis=[1, 1, 1])
        self.__addCables()

    def __addCables(self):
        cables=["16 0 5","-16 0 5","0 16 5","0 -16 5","11 11 5","-11 -11 5","11 -11 5","-11 11 5"]
        for i in range(0,4):
            cable = self.node.createChild('cable'+str(i+1))
            cable.createObject('VisualStyle', displayFlags="showInteractionForceFields")
            cable.createObject('MechanicalObject' , position=cables[i*2]+" "+cables[i*2+1])
            cable.createObject('CableActuator' if self.inverseMode else 'CableConstraint', name="cable", indices=[0, 1], hasPullPoint=0, minForce=0, maxPositiveDisp=12, maxDispVariation=1.5)
            cable.createObject('BarycentricMapping', name='mapping', mapForces=False, mapMasses=False)

    def addVisualModel(self, color=[1., 0., 0., 1.]):
        modelVisu = self.node.createChild('VisualModel')
        modelVisu.createObject('MeshSTLLoader', filename=path+'wheel_visu.stl')
        modelVisu.createObject('OglModel', color=color)
        modelVisu.createObject('BarycentricMapping')

    def addCollisionModel(self):
        modelContact = self.node.createChild('CollisionModel')
        modelContact.createObject('MeshSTLLoader', name='loader', filename=path+'wheel_collision.stl', scale=1)
        modelContact.createObject('MeshTopology', src='@loader', name='topo')
        modelContact.createObject('MechanicalObject')
        modelContact.createObject('TriangleCollisionModel')
        modelContact.createObject('LineCollisionModel')
        modelContact.createObject('PointCollisionModel')
        modelContact.createObject('BarycentricMapping')


def createScene(rootNode):

    rootNode.createObject('RequiredPlugin', pluginName='SoftRobots SoftRobots.Inverse SofaOpenglVisual SofaSparseSolver')
    rootNode.createObject('VisualStyle', displayFlags='hideWireframe showVisualModels showBehaviorModels hideCollisionModels hideBoundingCollisionModels hideForceFields hideInteractionForceFields')
    rootNode.findData('gravity').value = [0, -9180, 0]
    rootNode.findData('dt').value = 0.01

    # Add solver for inverse resolution
    rootNode.createObject('FreeMotionAnimationLoop')
    rootNode.createObject('QPInverseProblemSolver', epsilon=2e-0, maxIterations=2500, tolerance=1e-7, responseFriction=0.8)

    # Contact detection methods
    rootNode.createObject('DefaultPipeline')
    rootNode.createObject('BruteForceDetection')
    rootNode.createObject('DefaultContactManager', response="FrictionContact", responseParams="mu=0.8")
    rootNode.createObject('LocalMinDistance', alarmDistance=5, contactDistance=1, angleCone=0.0)

    # Add linear solver
    simulation = rootNode.createChild("Simulation")
    simulation.createObject('EulerImplicitSolver', rayleighMass=0.015, rayleighStiffness=0.015)
    simulation.createObject('SparseLDLSolver')
    simulation.createObject("GenericConstraintCorrection", solverName="SparseLDLSolver")

    Floor(rootNode)
    target = Target(rootNode)

    circularrobot = CircularRobot(simulation, effectorTarget=target.dofs.getData("position").getLinkPath())
    circularrobot.addVisualModel()
    circularrobot.addCollisionModel()


    return rootNode
