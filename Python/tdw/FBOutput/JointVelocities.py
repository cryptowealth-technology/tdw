# automatically generated by the FlatBuffers compiler, do not modify

# namespace: FBOutput

import tdw.flatbuffers

class JointVelocities(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsJointVelocities(cls, buf, offset):
        n = tdw.flatbuffers.encode.Get(tdw.flatbuffers.packer.uoffset, buf, offset)
        x = JointVelocities()
        x.Init(buf, n + offset)
        return x

    # JointVelocities
    def Init(self, buf, pos):
        self._tab = tdw.flatbuffers.table.Table(buf, pos)

    # JointVelocities
    def Id(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(tdw.flatbuffers.number_types.Int32Flags, o + self._tab.Pos)
        return 0

    # JointVelocities
    def Velocity(self, j):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            a = self._tab.Vector(o)
            return self._tab.Get(tdw.flatbuffers.number_types.Float32Flags, a + tdw.flatbuffers.number_types.UOffsetTFlags.py_type(j * 4))
        return 0

    # JointVelocities
    def VelocityAsNumpy(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.GetVectorAsNumpy(tdw.flatbuffers.number_types.Float32Flags, o)
        return 0

    # JointVelocities
    def VelocityLength(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # JointVelocities
    def AngularVelocity(self, j):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            a = self._tab.Vector(o)
            return self._tab.Get(tdw.flatbuffers.number_types.Float32Flags, a + tdw.flatbuffers.number_types.UOffsetTFlags.py_type(j * 4))
        return 0

    # JointVelocities
    def AngularVelocityAsNumpy(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            return self._tab.GetVectorAsNumpy(tdw.flatbuffers.number_types.Float32Flags, o)
        return 0

    # JointVelocities
    def AngularVelocityLength(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # JointVelocities
    def Sleeping(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(10))
        if o != 0:
            return bool(self._tab.Get(tdw.flatbuffers.number_types.BoolFlags, o + self._tab.Pos))
        return False

def JointVelocitiesStart(builder): builder.StartObject(4)
def JointVelocitiesAddId(builder, id): builder.PrependInt32Slot(0, id, 0)
def JointVelocitiesAddVelocity(builder, velocity): builder.PrependUOffsetTRelativeSlot(1, tdw.flatbuffers.number_types.UOffsetTFlags.py_type(velocity), 0)
def JointVelocitiesStartVelocityVector(builder, numElems): return builder.StartVector(4, numElems, 4)
def JointVelocitiesAddAngularVelocity(builder, angularVelocity): builder.PrependUOffsetTRelativeSlot(2, tdw.flatbuffers.number_types.UOffsetTFlags.py_type(angularVelocity), 0)
def JointVelocitiesStartAngularVelocityVector(builder, numElems): return builder.StartVector(4, numElems, 4)
def JointVelocitiesAddSleeping(builder, sleeping): builder.PrependBoolSlot(3, sleeping, 0)
def JointVelocitiesEnd(builder): return builder.EndObject()