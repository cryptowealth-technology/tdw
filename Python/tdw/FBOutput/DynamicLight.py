# automatically generated by the FlatBuffers compiler, do not modify

# namespace: FBOutput

import tdw.flatbuffers

class DynamicLight(object):
    __slots__ = ['_tab']

    @classmethod
    def GetRootAsDynamicLight(cls, buf, offset):
        n = tdw.flatbuffers.encode.Get(tdw.flatbuffers.packer.uoffset, buf, offset)
        x = DynamicLight()
        x.Init(buf, n + offset)
        return x

    # DynamicLight
    def Init(self, buf, pos):
        self._tab = tdw.flatbuffers.table.Table(buf, pos)

    # DynamicLight
    def Id(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.Get(tdw.flatbuffers.number_types.Int32Flags, o + self._tab.Pos)
        return 0

    # DynamicLight
    def IsOn(self):
        o = tdw.flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(6))
        if o != 0:
            return bool(self._tab.Get(tdw.flatbuffers.number_types.BoolFlags, o + self._tab.Pos))
        return False

def DynamicLightStart(builder): builder.StartObject(2)
def DynamicLightAddId(builder, id): builder.PrependInt32Slot(0, id, 0)
def DynamicLightAddIsOn(builder, isOn): builder.PrependBoolSlot(1, isOn, 0)
def DynamicLightEnd(builder): return builder.EndObject()