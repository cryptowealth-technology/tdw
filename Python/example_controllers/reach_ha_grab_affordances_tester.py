from tdw.librarian import HumanoidAnimationLibrarian, HumanoidLibrarian
from tdw.controller import Controller
from typing import List, Dict, Union
from tdw.tdw_utils import TDWUtils, QuaternionUtils
from tdw.output_data import OutputData, Transforms, LocalTransforms
from tdw.output_data import OutputData, EmptyObjects, Bounds
from random import uniform
from time import sleep
import os
import numpy as np
from enum import Enum
from tdw.tdw_utils import QuaternionUtils


class Arm(Enum):
    left = 0
    right = 1

"""
Create a humanoid that walks across the room, knocks over a chair and reaches for 
a randomly-positioned object multiple times.
"""


class ReachForAffordancePoint(Controller):

    # A dictionary of affordance points per model. This could be saved to a json file.
    AFFORDANCE_POINTS = {"basket_18inx18inx12iin_wicker": [{'x': -0.2285, 'y': 0.305, 'z': 0.0},
                                                           {'x': 0.2285, 'y': 0.305, 'z': 0.0},
                                                           {'x': 0, 'y': 0.305, 'z': 0.2285},
                                                           {'x': 0, 'y': 0.305, 'z': -0.2285}],
                         "basket_18inx18inx12iin_bamboo": [{'x': -0.2285, 'y': 0.305, 'z': 0.0},
                                                           {'x': 0.2285, 'y': 0.305, 'z': 0.0},
                                                           {'x': 0, 'y': 0.305, 'z': 0.2285},
                                                           {'x': 0, 'y': 0.305, 'z': -0.2285}]}
    # Store empty object IDs.
    # Key = The empty object ID. Value = {"object_id": object_id, "position": position}
    EMPTY_OBJECT_IDS: Dict[int, Dict[str, int]] = dict()

    AFFORDANCE_POINTS_BY_OBJECT_ID: Dict[int, Dict[int, Dict[str, float]]] = dict()

    def __init__(self, port: int = 1071, check_version: bool = True, launch_build: bool = True):
        super().__init__(port=port, check_version=check_version, launch_build=launch_build)
        self.h_id = self.get_unique_id()
        self.t_id = self.get_unique_id()
        self.reach_action_length=30
        self.reset_action_length=20
        self.affordance_id = 0
        self.reach_arm = "left"

    @staticmethod
    def get_add_object_with_affordance_points(model_name: str, object_id: int, position: Dict[str, float] = None,
                                              rotation: Dict[str, float] = None, library: str = "",
                                              scale_factor: Dict[str, float] = None, kinematic: bool = False,
                                              gravity: bool = True,
                                              default_physics_values: bool = True, mass: float = 1,
                                              dynamic_friction: float = 0.3,
                                              static_friction: float = 0.3, bounciness: float = 0.7) -> List[dict]:
        # Add the object with physics parameters.
        commands = Controller.get_add_physics_object(model_name=model_name, object_id=object_id, position=position,
                                                     rotation=rotation, library=library, scale_factor=scale_factor,
                                                     kinematic=kinematic, gravity=gravity,
                                                     default_physics_values=default_physics_values, mass=mass,
                                                     dynamic_friction=dynamic_friction, static_friction=static_friction,
                                                     bounciness=bounciness)
        # Add affordance points.
        if model_name in ReachForAffordancePoint.AFFORDANCE_POINTS:
            for affordance_position in ReachForAffordancePoint.AFFORDANCE_POINTS[model_name]:
                # Remember the original local positions.
                ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID[object_id] = dict()
                empty_object_id = Controller.get_unique_id()
                # Cache the mapping between empty object IDs and the ID of the parent object.
                ReachForAffordancePoint.EMPTY_OBJECT_IDS[empty_object_id] = {"object_id": object_id,
                                                                             "position": affordance_position}
                # Add a command to attach an empty object.
                commands.extend([{"$type": "attach_empty_object",
                                 "id": object_id,
                                 "empty_object_id": empty_object_id,
                                 "position": affordance_position},
                                 {"$type": "add_position_marker", 
                                  "position":  {'x': affordance_position['x'], 'y': affordance_position['y'] + 0.35, 'z': affordance_position['z']}, 
                                  "scale": 0.05, 
                                  "color": {"r": 1, "g": 0, "b": 0, "a": 1},
                                  "shape": "sphere"}])
                # Remember the position.
                ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID[object_id][empty_object_id] = affordance_position
        return commands

    def reach_for(self, resp: List[bytes], target: Union[int, np.ndarray, Dict[str,  float]], arm: Arm, hand_position: np.ndarray) -> List[dict]:
        # Convert from a numpy array to a dictionary.
        if isinstance(target, np.ndarray):
            target = TDWUtils.array_to_vector3(target)
        # The target is an object ID.
        elif isinstance(target, int):
            # Get the nearest affordance position.
            nearest_distance = np.inf
            nearest_position = np.array([0, 0, 0])
            got_affordance_position = False
            for i in range(len(resp) - 1):
                r_id = OutputData.get_data_type_id(resp[i])
                if r_id == "empt":
                    empt = EmptyObjects(resp[i])
                    for j in range(empt.get_num()):
                        # Get the ID of the affordance point.
                        empty_object_id = empt.get_id(j)
                        self.affordance_id = empty_object_id
                        # Get the parent object ID.
                        object_id = ReachForAffordancePoint.EMPTY_OBJECT_IDS[empty_object_id]["object_id"]
                        # Found the target object.
                        if object_id == target:
                            got_affordance_position = True
                            # Get the position of the empty object.
                            empty_object_position = empt.get_position(j)
                            # Get the nearest affordance position.
                            distance = np.linalg.norm(hand_position - empty_object_position)
                            if distance < nearest_distance:
                                nearest_distance = distance
                                nearest_position = empty_object_position
            # The target position is the nearest affordance point.
            if got_affordance_position:
                target = TDWUtils.array_to_vector3(nearest_position)
            # If the object doesn't have empty game objects, aim for the center and hope for the best.
            else:
                got_center = False
                for i in range(len(resp) - 1):
                    r_id = OutputData.get_data_type_id(resp[i])
                    if r_id == "boun":
                        bounds = Bounds(resp[i])
                        for j in range(bounds.get_num()):
                            if bounds.get_id(j) == target:
                                target = TDWUtils.array_to_vector3(bounds.get_center(j))
                                got_center = True
                                break
                if not got_center:
                    raise Exception("Couldn't get the centroid of the target object.")
        return [
            # Teleport IK target to target position
            # Reach for IK target, at affordance position
            {"$type": "humanoid_reach_for_position", 
             "position": target, 
             "id": self.h_id, 
             "length": self.reach_action_length, 
             "arm": self.reach_arm}
        ]

    def init_scene(self) -> None:
        ReachForAffordancePoint.EMPTY_OBJECT_IDS.clear()
        commands = [TDWUtils.create_empty_room(12, 12)]
        commands.extend(self.get_add_object_with_affordance_points(model_name="basket_18inx18inx12iin_wicker",
                                                                   object_id=self.t_id,
                                                                   position={"x": 0, "y": 0.35, "z": 0},
                                                                   rotation={"x": 0, "y": 0, "z": 0}))
        commands.extend([self.get_add_object(model_name="live_edge_coffee_table",
                                             object_id=9999,
                                             position={"x": 0, "y": 0, "z": 0},
                                             rotation={"x": 0, "y": 20, "z": 0},
                                             library="models_core.json"),
                         self.get_add_object(model_name="chair_billiani_doll",
                                             object_id=5555,
                                             position={"x": -0.3, "y": 0, "z": -2},
                                             rotation={"x": 0, "y": 63.25, "z": 0},
                                             library="models_core.json"),
                          {"$type": "set_kinematic_state", "id": self.t_id, "is_kinematic": True, "use_gravity": False},
                          {"$type": "set_kinematic_state", "id": 9999, "is_kinematic": True, "use_gravity": False},
                          {"$type": "add_humanoid",
                           "name": "ha_proto_v1a",
                           "position": {"x": 0, "y": 0, "z": -0.525},
                           "url": "file:///" + "D://TDW_Strategic_Plan_2021//Humanoid_Agent//HumanoidAgent_proto_V1//AssetBundles//Windows//non_t_pose",
                           #"url": "file:///" + "D://HumanoidAgent//HumanoidAgent_proto_V1//AssetBundles//Windows//non_t_pose",
                           "id": self.h_id},
                          {"$type": "send_humanoids",
                           "ids": [self.h_id],
                           "frequency": "always"},
                          {"$type": "send_transforms",
                           "ids": [self.t_id],
                           "frequency": "always"}])
        # Request EmptyObjects and Bounds data.
        commands.extend([{"$type": "send_empty_objects",
                         "frequency": "always"},
                         {"$type": "send_bounds",
                          "frequency": "always"}])
        self.communicate(commands)

    
    @staticmethod
    def _reset_affordance_points(object_id: int) -> List[dict]:
        """
        :param object_id: The object ID.
        
        :return: A list of commands to reset this object's affordance points.
        """
        
        if object_id not in ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID:
            return []
        commands = []
        for empty_object_id in ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID[object_id]:
            commands.extend([{"$type": "parent_empty_object",
                              "empty_object_id": empty_object_id,
                              "id": object_id},
                             {"$type": "teleport_empty_object",
                              "empty_object_id": empty_object_id,
                              "id": object_id,
                              "position": ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID[object_id][empty_object_id],
                              "absolute": False}])
        return commands


    def drop(self, resp: List[bytes], object_id: int, empty_object_id: int, arm: Arm) -> List[dict]:
        commands = [{"$type": "humanoid_drop_object",
                     "target": object_id,
                     "id": self.h_id,
                     "arm": self.reach_arm}]
        # Get the current position of the target object.
        
        resp = self.communicate([])
        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            # Find the transform data.
            if r_id == "tran":
                t = Transforms(r)
                for j in range(t.get_num()):
                    if t.get_id(j) == object_id:
                        tgt_position = TDWUtils.array_to_vector3(np.array(t.get_position(j)))
                        offset = ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID[object_id][empty_object_id]
                        home_position = {"x": tgt_position["x"] + offset["z"], "y": tgt_position["y"] + offset["y"],
                                         "z": tgt_position["z"] + offset["x"]}
        commands.append({"$type": "teleport_object_local", 
                         "position": home_position,
                         "id": object_id})
        
        """                
        offset = ReachForAffordancePoint.AFFORDANCE_POINTS_BY_OBJECT_ID[object_id][empty_object_id]
        commands.extend([{"$type": "translate_object_by", 
                         "position": {"x": -offset["z"], "y": -offset["y"], "z": -offset["x"]},
                         "absolute": False,
                         "id": object_id},
                        {"$type": "rotate_object_to", 
                         "rotation": {"w": 1.0, "x": 0, "y": 0, "z": 0}, "id": object_id}])
        """
        commands.extend(ReachForAffordancePoint._reset_affordance_points(self.t_id))
        return commands


    def run(self):
        walk_record = HumanoidAnimationLibrarian().get_record("walking_2")

        # Make Unity's framerate match that of the animation clip.
        self.communicate({"$type": "set_target_framerate", "framerate": walk_record.framerate})

        self.init_scene()

        self.communicate(TDWUtils.create_avatar(position={"x": -4.42, "y": 1.5, "z": 5.95}, look_at={"x": 0, "y": 1.0, "z": -3}))

        resp = self.communicate([])

        self.reach_arm = "left"
        commands = self.reach_for(resp=resp, arm=Arm.left, target=self.t_id, hand_position=np.array([0, 0, 0]))
        self.communicate(commands) 

        frame = 0
        while frame < self.reach_action_length:
            self.communicate([])
            frame += 1
        
        # Grasp the object that was just reached for. The object is parented to the affordance empty game object.
        self.communicate({"$type": "humanoid_grasp_object", 
                          "target": self.t_id, 
                          "affordance_id": int(self.affordance_id), 
                          "id": self.h_id, 
                          "arm": self.reach_arm})

        for i in range(2):
            # Move the arm holding the object, to a reasonable carrying position.     
            self.communicate([{"$type": "humanoid_reach_for_position", 
                               "position": {"x": uniform(-0.75, 0.75), "y": uniform(0.75, 2.0), "z": uniform(0, 0.1)}, 
                               "target": self.t_id, 
                               "affordance_id": int(self.affordance_id), 
                               "id": self.h_id,
                               "length": self.reset_action_length, 
                               "arm": self.reach_arm},
                              {"$type": "humanoid_reset_held_object_rotation", 
                               "target": self.t_id, 
                               "affordance_id": int(self.affordance_id), 
                               "id": self.h_id,
                               "length": self.reset_action_length, 
                               "arm": self.reach_arm}])
            frame = 0
            while frame < self.reset_action_length:
                self.communicate([])
                frame += 1

            sleep(1)


        # Place the basket back onto the table surface.     
        self.communicate([{"$type": "humanoid_reach_for_position", 
                          "position": {"x": 0, "y": 0.655, "z": 0.1}, 
                          "target": self.t_id, 
                          "affordance_id": int(self.affordance_id), 
                          "id": self.h_id,
                          "length": self.reset_action_length, 
                          "arm": self.reach_arm},
                         {"$type": "humanoid_reset_held_object_rotation", 
                          "target": self.t_id, 
                          "affordance_id": int(self.affordance_id), 
                          "id": self.h_id,
                          "length": self.reset_action_length, 
                          "arm": self.reach_arm}])
        frame = 0
        while frame < self.reset_action_length:
            self.communicate([])
            frame += 1

        commands = self.drop(resp=resp, arm=Arm.left, object_id=self.t_id, empty_object_id = int(self.affordance_id))
        self.communicate(commands) 

        
        sleep(0.5)       
        self.communicate({"$type": "humanoid_reset_arm", 
                          "id": self.h_id, 
                          "length": self.reset_action_length, 
                          "arm": self.reach_arm})
        
        for i in range(200):
            self.communicate([])
        



    def get_direction(self, forward: np.array, origin: np.array, target: np.array) -> bool:
        """
        :param forward: The forward directional vector.
        :param origin: The origin position.
        :param target: The target position.

        :return: True if the target is to the left of the origin by the forward vector; False if it's to the right.
        """
        # Get the heading.
        target_direction = target - origin
        # Normalize the heading.
        #target_direction = target_direction / np.linalg.norm(target_direction)
        perpendicular: np.array = np.cross(forward, target_direction)
        direction = np.dot(perpendicular, QuaternionUtils.UP)
        return direction


if __name__ == "__main__":
    ReachForAffordancePoint(launch_build=False).run()