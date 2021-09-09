from typing import Dict, List, Union
import numpy as np
from tdw.output_data import OutputData, AvatarSimpleBody, ImageSensors
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera_base import ThirdPersonCameraBase
from tdw.add_ons.avatar_body import AvatarBody
from tdw.object_data.transform import Transform
from tdw.object_data.rigidbody import Rigidbody


class EmbodiedAvatar(ThirdPersonCameraBase):
    """
    An `EmbodiedAvatar` is an avatar with a physical body. The body has a simple shape and responds to physics (just like objects and robots).

    ```python
    from tdw.controller import Controller
    from tdw.tdw_utils import TDWUtils
    from tdw.add_ons.embodied_avatar import EmbodiedAvatar

    c = Controller()
    a = EmbodiedAvatar(position={"x": 0, "y": 0, "z": 0},
                       rotation={"x": 0, "y": 30, "z": 0},
                       avatar_id="a")
    c.add_ons.append(a)
    c.communicate(TDWUtils.create_empty_room(12, 12))
    a.move(500)
    while a.is_moving:
        c.communicate([])
    a.turn(-400)
    while a.is_moving:
        c.communicate([])
    c.communicate({"$type": "terminate"})
    ```
    """

    def __init__(self, avatar_id: str = None, position: Dict[str, float] = None, rotation: Dict[str, float] = None,
                 fov: int = None, color: Dict[str, float] = None, body: AvatarBody = AvatarBody.capsule,
                 scale_factor: Dict[str, float] = None, mass: float = 80, dynamic_friction: float = 0.3,
                 static_friction: float = 0.3, bounciness: float = 0.7):
        """
        :param avatar_id: The ID of the avatar (camera). If None, a random ID is generated.
        :param position: The initial position of the object.If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param rotation: The initial rotation of the camera. Can be Euler angles (keys are `(x, y, z)`) or a quaternion (keys are `(x, y, z, w)`). If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param fov: If not None, this is the initial field of view. Otherwise, defaults to 35.
        :param body: [The body of the avatar.](avatar_body.md)
        :param scale_factor: Scale the avatar by this factor. Can be None.
        :param mass: The mass of the avatar.
        :param dynamic_friction: The dynamic friction coefficient of the avatar.
        :param static_friction: The static friction coefficient of the avatar.
        :param bounciness: The bounciness of the avatar.
        """

        super().__init__(avatar_id=avatar_id, position=position, rotation=rotation, fov=fov)
        self._init_commands.extend([{"$type": "change_avatar_body",
                                     "body_type": body.name.title(),
                                     "avatar_id": self.avatar_id},
                                    {"$type": "set_avatar_mass",
                                     "mass": mass,
                                     "avatar_id": self.avatar_id},
                                    {"$type": "set_avatar_physic_material",
                                     "dynamic_friction": dynamic_friction,
                                     "static_friction": static_friction,
                                     "bounciness": bounciness,
                                     "avatar_id": self.avatar_id},
                                    {"$type": "set_avatar_drag",
                                     "angular_drag": 0.5,
                                     "avatar_id": self.avatar_id,
                                     "drag": 1},
                                    {"$type": "send_avatars",
                                     "frequency": "always"},
                                    {"$type": "send_image_sensors",
                                     "frequency": "always"}])
        if color is not None:
            if "a" in color and color["a"] < 1:
                self._init_commands.append({"$type": "enable_avatar_transparency",
                                            "avatar_id": self.avatar_id})
            self._init_commands.append({"$type": "set_avatar_color",
                                        "color": color,
                                        "avatar_id": self.avatar_id})
        if scale_factor is not None:
            self._init_commands.append({"$type": "scale_avatar",
                                        "scale_factor": scale_factor,
                                        "avatar_id": self.avatar_id})
        """:field
        [Transform data](../object_data/transform.md) for the avatar.
        """
        self.transform: Transform = Transform(position=np.array([0, 0, 0]),
                                              rotation=np.array([0, 0, 0, 0]),
                                              forward=np.array([0, 0, 0]))
        """:field
        [Rigidbody data](../object_data/rigidbody.md) for the avatar.
        """
        self.rigidbody: Rigidbody = Rigidbody(velocity=np.array([0, 0, 0]),
                                              angular_velocity=np.array([0, 0, 0]),
                                              sleeping=True)
        """:field
        The rotation of the camera as an [x, y, z, w] numpy array.
        """
        self.camera_rotation: np.array = np.array([0, 0, 0, 0])
        """:field
        If True, the avatar is currently moving or turning.
        """
        self.is_moving: bool = False

    def on_send(self, resp: List[bytes]) -> None:
        for i in range(len(resp) - 1):
            r_id = OutputData.get_data_type_id(resp[i])
            # Update my state.
            if r_id == "avsb":
                avsb = AvatarSimpleBody(resp[i])
                if avsb.get_avatar_id() == self.avatar_id:
                    # Update the transform data.
                    self.transform.position = np.array(avsb.get_position())
                    self.transform.rotation = np.array(avsb.get_rotation())
                    self.transform.forward = np.array(avsb.get_forward())
                    # Update the rigidbody data.
                    self.rigidbody.velocity = np.array(avsb.get_velocity())
                    self.rigidbody.angular_velocity = np.array(avsb.get_angular_velocity())
                    self.rigidbody.sleeping = np.array(avsb.get_sleeping())
                    # Update whether the avatar is moving.
                    self.is_moving = not self.rigidbody.sleeping
            # Update the rotation of the camera.
            elif r_id == "imse":
                imse = ImageSensors(resp[i])
                if imse.get_avatar_id() == self.avatar_id:
                    self.camera_rotation = np.array(imse.get_sensor_rotation(0))

    def move(self, force: Union[float, int, Dict[str, float], np.ndarray]) -> None:
        """
        Apply a force to the avatar to begin moving it.

        :param force: The force. If float: apply a force along the forward (positive value) or backward (negative value) directional vector of the avatar. If dictionary or numpy array: Apply a force defined by the x, y, z vector.
        """

        if isinstance(force, float) or isinstance(force, int):
            self.commands.append({"$type": "move_avatar_forward_by",
                                  "magnitude": force,
                                  "avatar_id": self.avatar_id})
        elif isinstance(force, dict):
            force_arr = TDWUtils.vector3_to_array(force)
            force_magnitude = float(np.linalg.norm(force_arr))
            self.commands.append({"$type": "apply_force_to_avatar",
                                  "magnitude": force_magnitude,
                                  "direction": force_arr / force_magnitude,
                                  "avatar_id": self.avatar_id})
        elif isinstance(force, np.ndarray):
            force_magnitude = float(np.linalg.norm(force))
            self.commands.append({"$type": "apply_force_to_avatar",
                                  "magnitude": force_magnitude,
                                  "direction": force / force_magnitude,
                                  "avatar_id": self.avatar_id})
        else:
            raise Exception(f"Invalid type: {force}")
        self.is_moving = True

    def turn(self, torque: float) -> None:
        """
        Apply a torque to the avatar so that it starts turning.

        :param torque: The torque. Positive value = clockwise rotation.
        """

        self.commands.append({"$type": "turn_avatar_by",
                              "torque": torque,
                              "avatar_id": self.avatar_id})
        self.is_moving = True

    def set_drag(self, drag: float = 1, angular_drag: float = 0.5) -> None:
        """
        Set the drag of the avatar. Increase this to force the avatar to slow down.

        :param drag: The drag of the rigidbody. A higher drag value will cause the avatar slow down faster.
        :param angular_drag: The angular drag of the rigidbody. A higher angular drag will cause the avatar's rotation to slow down faster.
        """

        self.commands.append({"$type": "set_avatar_drag",
                              "drag": drag,
                              "angular_drag": angular_drag,
                              "avatar_id": self.avatar_id})

    def rotate_camera(self, rotation: Dict[str, float]) -> None:
        """
        Rotate the camera.

        :param rotation: Rotate the camera by these angles (in degrees). Keys are `"x"`, `"y"`, `"z"` and correspond to `(pitch, yaw, roll)`.
        """

        for q, axis in zip(["x", "y", "z"], ["pitch", "yaw", "roll"]):
            self.commands.append({"$type": "rotate_sensor_container_by",
                                  "axis": axis,
                                  "angle": rotation[q],
                                  "avatar_id": self.avatar_id})

    def look_at(self, target: Union[int, Dict[str, float], np.ndarray]) -> None:
        """
        Look at a target object or position.

        :param target: The target. If int: an object ID. If a dictionary or numpy array: an x, y, z position.
        """

        if isinstance(target, int):
            self.commands.append({"$type": "look_at",
                                  "object_id": target,
                                  "use_centroid": True,
                                  "avatar_id": self.avatar_id})
        elif isinstance(target, dict):
            self.commands.append({"$type": "look_at_position",
                                  "position": target,
                                  "avatar_id": self.avatar_id})
        elif isinstance(target, np.ndarray):
            self.commands.append({"$type": "look_at_position",
                                  "position": TDWUtils.array_to_vector3(target),
                                  "avatar_id": self.avatar_id})
        else:
            raise Exception(f"Invalid type: {target}")

    def reset_camera(self) -> None:
        """
        Reset the rotation of the camera.
        """

        self.commands.append({"$type": "reset_sensor_container_rotation",
                              "avatar_id": self.avatar_id})

    def _get_avatar_type(self) -> str:
        return "A_Simple_Body"
