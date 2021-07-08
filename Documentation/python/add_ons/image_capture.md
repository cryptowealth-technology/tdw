# ImageCapture

`from tdw.add_ons.image_capture import ImageCapture`

Per frame, request image data and save the images to disk.

```python
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from tdw.add_ons.image_capture import ImageCapture

c = Controller(launch_build=False)
c.start()

# Add a third-person camera. It will look at object 0.
    object_id = 0
camera = ThirdPersonCamera(position={"x": 0.5, "y": 1.5, "z": -2},
                           look_at=0,
                           pass_masks=["_img", "_id"])
# Tell the camera to capture images per-frame.
capture = ImageCapture(avatar_ids=[camera.avatar_id], path="D:/image_capture_test")
c.add_ons.extend([camera, capture])

# Create an empty room and add an object.
# The camera will be added after creating the empty room and the object.
# The image capture add-on will initialize after the camera and save an `_img` pass and `_id` pass to disk.
c.communicate([TDWUtils.create_empty_room(12, 12),
               c.get_add_object(model_name="iron_box",
                                object_id=object_id)])

c.communicate({"$type": "terminate"})
```

***

## Fields

- `commands` These commands will be appended to the commands of the next `communicate()` call.

- `initialized` If True, this module has been initialized.

- `path` The path to the output directory.

- `avatar_ids` The IDs of the avatars that will capture and save images. If empty, all avatars will capture and save images.

***

## Functions

#### \_\_init\_\_

**`ImageCapture(path)`**

**`ImageCapture(path, avatar_ids=None, png=False)`**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| path |  Union[str, Path] |  | The path to the output directory. |
| avatar_ids |  List[str] | None | The IDs of the avatars that will capture and save images. If empty, all avatars will capture and save images. |
| png |  bool  | False | If True, images will be lossless png files. If False, images will be jpgs. Usually, jpg is sufficient. |

#### get_initialization_commands

**`self.get_initialization_commands()`**

This function gets called exactly once per add-on. To call it again, set `self.initialized = False`.

_Returns:_  A list of commands that will initialize this module.

#### on_send

**`self.on_send(resp)`**

This is called after commands are sent to the build and a response is received.

Use this function to send commands to the build on the next frame, given the `resp` response.
Any commands in the `self.commands` list will be sent on the next frame.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| resp |  List[bytes] |  | The response from the build. |

##### before_send

**`self.before_send(commands)`**

This is called before sending commands to the build. By default, this function doesn't do anything.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| commands |  List[dict] |  | The commands that are about to be sent to the build. |


