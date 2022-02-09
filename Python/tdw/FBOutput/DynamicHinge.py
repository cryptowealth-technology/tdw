# automatically generated by the FlatBuffers compiler, do not modify

# namespace: FBOutput

import tdw.flatbuffers

class DynamicHinge(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsDynamicHinge(cls, buf, offset):
        n = tdw.flatbuffers.encode.Get(tdw.flatbuffers.packer.uoffset, buf, offset)
        x = DynamicHinge()
        x.Init(buf, n + offset)
        return x

    # DynamicHinge
    def Init(self, buf, pos):
        self._tab = tdw.flatbuffers.table.Table(buf, pos)

    # DynamicHinge
    def Id(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(tdw.flatbuffers.number_types.Int32Flags, o + self._tab.Pos)
        return 0

    # DynamicHinge
    def Angle(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return self._tab.Get(tdw.flatbuffers.number_types.Float32Flags, o + self._tab.Pos)
        return 0.0

    # DynamicHinge
    def Velocity(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(8))
        if o != 0:
            return self._tab.Get(tdw.flatbuffers.number_types.Float32Flags, o + self._tab.Pos)
        return 0.0

def DynamicHingeStart(builder): builder.StartObject(3)
def DynamicHingeAddId(builder, id): builder.PrependInt32Slot(0, id, 0)
def DynamicHingeAddAngle(builder, angle): builder.PrependFloat32Slot(1, angle, 0.0)
def DynamicHingeAddVelocity(builder, velocity): builder.PrependFloat32Slot(2, velocity, 0.0)
def DynamicHingeEnd(builder): return builder.EndObject()
