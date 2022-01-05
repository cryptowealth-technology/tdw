from enum import Enum
from json import loads
from pathlib import Path
from pkg_resources import resource_filename
from typing import Tuple, List, Union, Dict, Optional
import numpy as np
from tdw.tdw_utils import TDWUtils
from tdw.controller import Controller
from tdw.librarian import ModelLibrarian, ModelRecord
from tdw.scene_data.region_bounds import RegionBounds
from tdw.scene_data.scene_bounds import SceneBounds
from tdw.add_ons.add_on import AddOn
from tdw.cardinal_direction import CardinalDirection


class _VerticalSpatialRelation(Enum):
    """
    Enum values to define vertical spatial relations.
    """

    on_top_of = 1
    on_shelf = 2


class _ObjectBounds:
    """
    Object bound positions based on cached object bounds and the position of the root object, assuming no rotation.
    """
    def __init__(self, record: ModelRecord, root_object_position: Dict[str, float]):
        """
        :param record: The model record.
        :param root_object_position: The position of the root object.
        """

        self.x_min: float = root_object_position["x"] + record.bounds["left"]["x"]
        self.x_max: float = root_object_position["x"] + record.bounds["right"]["x"]
        self.z_min: float = root_object_position["z"] + record.bounds["front"]["z"]
        self.z_max: float = root_object_position["z"] + record.bounds["back"]["z"]

    def is_inside(self, x: float, z: float) -> bool:
        """
        :param x: The x coordinate.
        :param z: The z coordinate.

        :return: True if position (x, z) is within the bounds of this object.
        """

        return self.x_min <= x <= self.x_max and self.z_min <= z <= self.z_max


class ProcGenObjects(AddOn):
    """
    Procedurally arrange objects using spatial relations and categories.
    For example, certain object categories can be *on top of* other object categories.

    Note that proc-gen object categories overlap with `record.wcategory` but are not the same.
    Note also that not all objects in a wcategory suitable for proc-gen and so aren't used by this add-on.
    To determine all models in a proc-gen category and the corresponding wcategory:

    ```python
    from tdw.add_ons.proc_gen_objects import ProcGenObjects

    for proc_gen_category in ProcGenObjects.PROC_GEN_CATEGORY_TO_WCATEGORY:
        wcategory = ProcGenObjects.PROC_GEN_CATEGORY_TO_WCATEGORY[proc_gen_category]
        print(f"Proc-gen category: {proc_gen_category}", f"wcategory: {wcategory}")
        for model_name in ProcGenObjects.MODEL_CATEGORIES[proc_gen_category]:
            print(f"\t{model_name}")
    ```
    """

    # Cache the model librarian.
    if "models_core.json" not in Controller.MODEL_LIBRARIANS:
        Controller.MODEL_LIBRARIANS["models_core.json"] = ModelLibrarian("models_core.json")
    """:class_var
    The names of models suitable for proc-gen. Key = The category. Value = A list of model names.
    """
    MODEL_CATEGORIES: Dict[str, List[str]] = loads(Path(resource_filename(__name__, "proc_gen_objects/models.json")).read_text())
    """:class_var
    Objects in these categories will be kinematic.
    """
    KINEMATIC_CATEGORIES: List[str] = Path(resource_filename(__name__, "proc_gen_objects/kinematic_categories.txt")).read_text().split("\n")
    """:class_var
    Data for shelves. Key = model name. Value = Dictionary: "size" (a 2-element list), "ys" (list of shelf y's).
    """
    SHELVES: Dict[str, dict] = loads(Path(resource_filename(__name__, "proc_gen_objects/shelves.json")).read_text())
    """:class_var
    Parameters for rectangular arrangements. Key = Category. Value = Dictionary (`"cell_size"`, `"density"`).
    """
    RECTANGULAR_ARRANGEMENTS: Dict[str, dict] = loads(Path(resource_filename(__name__, "proc_gen_objects/rectangular_arrangements.json")).read_text())
    """:class_var
    A mapping of proc-gen categories to record wcategories.
    """
    PROC_GEN_CATEGORY_TO_WCATEGORY: Dict[str, str] = loads(Path(resource_filename(__name__, "proc_gen_objects/procgen_category_to_wcategory.json")).read_text())
    """:class_var
    Categories that should only appear once in a scene.
    """
    UNIQUE_CATEGORIES: List[str] = Path(resource_filename(__name__, "proc_gen_objects/unique_categories.txt")).read_text().split("\n")
    _TABLE_SHAPES: Dict[str, List[str]] = Path(resource_filename(__name__, "proc_gen_objects/table_shapes.json")).read_text().split("\n")
    _WALL_DEPTH: float = 0.28
    _CANONICAL_ROTATIONS: Dict[str, float] = loads(Path(resource_filename(__name__, "proc_gen_objects/canonical_rotations.json")).read_text())

    def __init__(self, random_seed: int = None):
        """
        :param random_seed: The random seed. If None, a random seed is randomly selected.
        """

        super().__init__()
        if random_seed is None:
            """:field
            The random number generator.
            """
            self.rng: np.random.RandomState = np.random.RandomState()
        else:
            self.rng = np.random.RandomState(random_seed)
        """:field
        The [scene bounds](../scene_data/SceneBounds.md). This is set on the second `communicate()` call.
        """
        self.scene_bounds: Optional[SceneBounds] = None
        # Get the vertical spatial relations.
        vertical_spatial_relations_data = loads(Path(resource_filename(__name__, "proc_gen_objects/vertical_spatial_relations.json")).read_text())
        self._vertical_spatial_relations: Dict[_VerticalSpatialRelation, Dict[str, List[str]]] = dict()
        for r in vertical_spatial_relations_data:
            self._vertical_spatial_relations[_VerticalSpatialRelation[r]] = dict()
            for c in vertical_spatial_relations_data[r]:
                self._vertical_spatial_relations[_VerticalSpatialRelation[r]][c] = vertical_spatial_relations_data[r][c]
        self._used_unique_categories: List[str] = list()

    def get_initialization_commands(self) -> List[dict]:
        self._used_unique_categories.clear()
        self.scene_bounds = None
        # Set the wood type.
        kitchen_counter_wood_type = self.rng.choice(["white_wood", "wood_beach_honey"])
        kitchen_counters = ProcGenObjects.MODEL_CATEGORIES["kitchen_counter"]
        ProcGenObjects.MODEL_CATEGORIES["kitchen_counter"] = [k for k in kitchen_counters if kitchen_counter_wood_type in k]
        kitchen_cabinets = ProcGenObjects.MODEL_CATEGORIES["wall_cabinet"]
        ProcGenObjects.MODEL_CATEGORIES["wall_cabinet"] = [k for k in kitchen_cabinets if kitchen_counter_wood_type in k]
        return [{"$type": "send_scene_regions"}]

    def on_send(self, resp: List[bytes]) -> None:
        if self.scene_bounds is None:
            self.scene_bounds = SceneBounds(resp=resp)

    def add_shelf(self, position: Union[np.array, Dict[str, float]], rotation: float,
                  region: int = 0, direction: CardinalDirection = None) -> Optional[ModelRecord]:
        """
        Procedurally generate a shelf with objects on each shelf.

        :param position: The position of the root object as either a numpy array or a dictionary.
        :param rotation: The root object's rotation in degrees around the y axis; all other objects will be likewise rotated.
        :param region: The index of the region in `self.scene_bounds`.
        :param direction: If not None, offset the position along this direction.

        :return: The model record of the root object. If no models were added to the scene, this is None.
        """

        record, root_object_id, position = self._get_root_object(category="shelf", position=position, region=region,
                                                                 direction=direction)
        if record is None:
            return None
        size = (ProcGenObjects.SHELVES[record.name]["size"][0], ProcGenObjects.SHELVES[record.name]["size"][1])
        # Add objects to each shelf.
        on_shelf_categories = self._vertical_spatial_relations[_VerticalSpatialRelation.on_shelf]["shelf"]
        child_object_ids: List[int] = list()
        for y in ProcGenObjects.SHELVES[record.name]["ys"]:
            object_top = {"x": position["x"], "y": y + position["y"], "z": position["z"]}
            cell_size, density = self._get_rectangular_arrangement_parameters(category="shelf")
            object_commands, object_ids = self._get_rectangular_arrangement(size=size,
                                                                            categories=on_shelf_categories,
                                                                            center=object_top,
                                                                            cell_size=cell_size,
                                                                            density=density)
            child_object_ids.extend(object_ids)
            self.commands.extend(object_commands)
        # Rotate everything.
        self._add_rotation_commands(parent_object_id=root_object_id,
                                    child_object_ids=child_object_ids,
                                    rotation=rotation,
                                    parent_object_name=record.name)
        return record

    def add_kitchen_counter(self, position: Union[np.array, Dict[str, float]], rotation: float,
                            region: int = 0, direction: CardinalDirection = None) -> Optional[ModelRecord]:
        """
        Procedurally generate a kitchen counter with objects on it.
        Sometimes, a kitchen counter will have a microwave, which can have objects on top of it.
        There will never be more than 1 microwave in the scene.

        :param position: The position of the root object as either a numpy array or a dictionary.
        :param rotation: The root object's rotation in degrees around the y axis; all other objects will be likewise rotated.
        :param region: The index of the region in `self.scene_bounds`.
        :param direction: If not None, offset the position along this direction.

        :return: The model record of the root object. If no models were added to the scene, this is None.
        """

        # Add objects on the kitchen counter.
        if self.rng.random() < 0.5 or "microwave" not in self._used_unique_categories:
            return self._get_objects_on_top_of(position=position, rotation=rotation, region=region,
                                               category="kitchen_counter", direction=direction)
        # Add a microwave on the kitchen counter.
        else:
            record, root_object_id, object_position = self._get_root_object(category="kitchen_counter",
                                                                            position=position,
                                                                            region=region,
                                                                            direction=direction)
            if record is None:
                return None
            # Rotate the kitchen counter.
            self._add_rotation_commands(parent_object_id=root_object_id, child_object_ids=[], rotation=rotation,
                                        parent_object_name=record.name)
            # Get the top position of the kitchen counter.
            object_top = {"x": object_position["x"],
                          "y": record.bounds["top"]["y"] + object_position["y"],
                          "z": object_position["z"]}
            # Add a microwave and add objects on top of the microwave.
            self._get_objects_on_top_of(position=object_top, rotation=rotation, region=region, category="microwave",
                                        parent=record)
            return record

    def add_kitchen_table(self, position: Union[np.array, Dict[str, float]], rotation: float, region: int = 0,
                          table_settings: bool = True, plate_model_name: str = None, fork_model_name: str = None,
                          knife_model_name: str = None, spoon_model_name: str = None,
                          centerpiece_model_name: str = None) -> Optional[ModelRecord]:
        """
        Add a kitchen table with chairs around it.
        Optionally, add forks, knives, spoons, coasters, and cups.
        The plates sometimes have food on them.
        Sometimes, there is a large object (i.e. a bowl or jug) in the center of the table.

        :param position: The position of the root object as either a numpy array or a dictionary.
        :param rotation: The root object's rotation in degrees around the y axis; all other objects will be likewise rotated.
        :param region: The index of the region in `self.scene_bounds`.
        :param table_settings: If True, add tables settings (plates, forks, knives, etc.) in front of each chair.
        :param plate_model_name: If not None, this is the model name of the plates. If None, the plate is `plate06`.
        :param fork_model_name: If not None, this is the model name of the forks. If None, the model name of the forks is random (all fork objects use the same model).
        :param knife_model_name: If not None, this is the model name of the knives. If None, the model name of the knives is random (all knife objects use the same model).
        :param spoon_model_name: If not None, this is the model name of the spoons. If None, the model name of the spoons is random (all spoon objects use the same model).
        :param centerpiece_model_name: If not None, this is the model name of the centerpiece. If None, the model name of the centerpiece is random.

        :return: The model record of the root object. If no models were added to the scene, this is None.
        """

        if plate_model_name is None:
            plate_model_name = "plate06"
        if fork_model_name is None:
            forks = ProcGenObjects.MODEL_CATEGORIES["fork"]
            fork_model_name = forks[self.rng.randint(0, len(forks))]
        if knife_model_name is None:
            knives = ProcGenObjects.MODEL_CATEGORIES["knife"]
            knife_model_name = knives[self.rng.randint(0, len(knives))]
        if spoon_model_name is None:
            spoons = ProcGenObjects.MODEL_CATEGORIES["spoon"]
            spoon_model_name = spoons[self.rng.randint(0, len(spoons))]
        if centerpiece_model_name is None:
            centerpiece_categories = ["jug", "vase", "pot", "bowl", "pan"]
            centerpiece_category = centerpiece_categories[self.rng.randint(0, len(centerpiece_categories))]
            centerpieces = ProcGenObjects.MODEL_CATEGORIES[centerpiece_category]
            centerpiece_model_name = centerpieces[self.rng.randint(0, len(centerpieces))]
        # Add the table.
        record, root_object_id, object_position = self._get_root_object(category="table", position=position,
                                                                        region=region)
        if record is None:
            return None
        child_object_ids: List[int] = list()
        # Get the shape of the table.
        table_shape = ""
        for shape in ProcGenObjects._TABLE_SHAPES:
            if record.name in ProcGenObjects._TABLE_SHAPES[shape]:
                table_shape = shape
                break
        assert table_shape != "", f"Unknown table shape for {record.name}"
        # Get the size, top, and bottom of the table.
        top = {"x": object_position["x"],
               "y": record.bounds["top"]["y"],
               "z": object_position["z"]}
        bottom = {"x": object_position["x"],
                  "y": 0,
                  "z": object_position["z"]}
        bottom_arr = TDWUtils.vector3_to_array(bottom)
        top_arr = TDWUtils.vector3_to_array(top)
        # Get a random chair model name.
        chairs = ProcGenObjects.MODEL_CATEGORIES["chair"]
        chair_model_name: str = chairs[self.rng.randint(0, len(chairs))]
        chair_record = Controller.MODEL_LIBRARIANS["models_core.json"].get_record(chair_model_name)
        chair_bound_points: List[np.array] = list()
        # Add chairs around the table.
        if table_shape == "square_or_circle":
            for side in ["left", "right", "front", "back"]:
                chair_bound_points.append(np.array([record.bounds[side]["x"] + object_position["x"],
                                                    0,
                                                    record.bounds[side]["z"] + object_position["z"]]))
        # Add chairs around the longer sides of the table.
        else:
            table_extents = TDWUtils.get_bounds_extents(bounds=record.bounds)
            if table_extents[0] > table_extents[2]:
                for side in ["front", "back"]:
                    chair_bound_points.extend([np.array([record.bounds[side]["x"] + object_position["x"],
                                                         0,
                                                         table_extents[2] * 0.25 + object_position["z"]]),
                                               np.array([record.bounds[side]["x"] + object_position["x"],
                                                         0,
                                                         table_extents[2] * 0.75 + object_position["z"]])])
            else:
                for side in ["left", "right"]:
                    chair_bound_points.extend([np.array([table_extents[0] * 0.25 + object_position["x"],
                                                         0,
                                                         record.bounds[side]["z"] + object_position["z"]]),
                                               np.array([table_extents[0] * 0.75 + object_position["x"],
                                                         0,
                                                         record.bounds[side]["z"] + object_position["z"]])])
        # Add the chairs.
        for chair_bound_point in chair_bound_points:
            chair_position = self._get_chair_position(chair_record=chair_record,
                                                      table_bottom=bottom_arr,
                                                      table_bound_point=chair_bound_point)
            object_id = Controller.get_unique_id()
            child_object_ids.append(object_id)
            # Add the chair.
            self.commands.extend(Controller.get_add_physics_object(model_name=chair_model_name,
                                                                   position=TDWUtils.array_to_vector3(chair_position),
                                                                   object_id=object_id,
                                                                   library="models_core.json"))
            # Look at the bottom-center and add a little rotation for spice.
            self.commands.extend([{"$type": "object_look_at_position",
                                   "position": bottom,
                                   "id": object_id},
                                  {"$type": "rotate_object_by",
                                   "angle": float(self.rng.uniform(-20, 20)),
                                   "id": object_id,
                                   "axis": "yaw"}])
        # Add table settings.
        if table_settings:
            for bound in ["left", "right", "front", "back"]:
                table_bound_point = np.array([record.bounds[bound]["x"] + object_position["x"],
                                              0,
                                              record.bounds[bound]["z"] + object_position["z"]])
                # Get a position for the plate.
                # Get the vector towards the center.
                v = np.array([object_position["x"], object_position["z"]]) - \
                    np.array([table_bound_point[0], table_bound_point[2]])
                # Get the normalized direction.
                v = v / np.linalg.norm(v)
                # Move the plates inward.
                v *= float(self.rng.uniform(0.15, 0.2))
                # Get a slightly perturbed position.
                plate_position = np.array([float(table_bound_point[0] + v[0] + self.rng.uniform(-0.03, 0.03)),
                                          top_arr[1],
                                          float(table_bound_point[2] + v[1] + self.rng.uniform(-0.03, 0.03))])
                # Add the plate.
                object_id = Controller.get_unique_id()
                child_object_ids.append(object_id)
                self.commands.extend(Controller.get_add_physics_object(model_name=plate_model_name,
                                                                       position=TDWUtils.array_to_vector3(plate_position),
                                                                       object_id=object_id,
                                                                       library="models_core.json"))
                # Get the direction from the plate to the center.
                v = np.array([object_position["x"], object_position["z"]]) - \
                    np.array([plate_position[0], plate_position[2]])
                v / np.linalg.norm(v)
                # Get the positions of the fork, knife, and spoon.
                q = v * self.rng.uniform(0.2, 0.3)
                fork_position = np.array([plate_position[0] - q[1] + self.rng.uniform(-0.03, 0.03),
                                          plate_position[1],
                                          plate_position[2] + q[0] + self.rng.uniform(-0.03, 0.03)])
                # Get the knife position.
                q = v * self.rng.uniform(0.2, 0.3)
                knife_position = np.array([plate_position[0] + q[1] + self.rng.uniform(-0.03, 0.03),
                                           plate_position[1],
                                           plate_position[2] - q[0] + self.rng.uniform(-0.03, 0.03)])
                q = v * self.rng.uniform(0.3, 0.4)
                spoon_position = np.array([plate_position[0] + q[1] + self.rng.uniform(-0.03, 0.03),
                                           plate_position[1]])
                # Get the rotation of the fork, knife, and spoon.
                if bound == "left":
                    rotation = 90
                elif bound == "right":
                    rotation = 270
                elif bound == "front":
                    rotation = 180
                else:
                    rotation = 0
                # Add a fork.
                object_id = Controller.get_unique_id()
                child_object_ids.append(object_id)
                self.commands.extend(Controller.get_add_physics_object(model_name=fork_model_name,
                                                                       object_id=object_id,
                                                                       position=TDWUtils.array_to_vector3(fork_position),
                                                                       rotation={"x": 0,
                                                                                 "y": rotation + float(self.rng.uniform(-15, 15)),
                                                                                 "z": 0},
                                                                       library="models_core.json"))
                # Add a knife.
                object_id = Controller.get_unique_id()
                child_object_ids.append(object_id)
                self.commands.extend(Controller.get_add_physics_object(model_name=knife_model_name,
                                                                       object_id=object_id,
                                                                       position=TDWUtils.array_to_vector3(knife_position),
                                                                       rotation={"x": 0,
                                                                                 "y": rotation + float(self.rng.uniform(-15, 15)),
                                                                                 "z": 0},
                                                                       library="models_core.json"))
                # Add a spoon.
                object_id = Controller.get_unique_id()
                child_object_ids.append(object_id)
                self.commands.extend(Controller.get_add_physics_object(model_name=spoon_model_name,
                                                                       object_id=object_id,
                                                                       position=TDWUtils.array_to_vector3(spoon_position),
                                                                       rotation={"x": 0,
                                                                                 "y": rotation + float(self.rng.uniform(-15, 15)),
                                                                                 "z": 0},
                                                                       library="models_core.json"))
                # Add a cup.
                if self.rng.random() > 0.33:
                    # Get the position of the cup.
                    q = v * self.rng.uniform(0.2, 0.3)
                    r = v * self.rng.uniform(0.25, 0.3)
                    cup_position = np.array([plate_position[0] + q[1] + r[0] + self.rng.uniform(-0.03, 0.03),
                                             plate_position[1],
                                             plate_position[2] - q[0] + r[1] + self.rng.uniform(-0.03, 0.03)])
                    # Add a coaster.
                    if self.rng.random() > 0.5:
                        coasters = ProcGenObjects.MODEL_CATEGORIES["coaster"]
                        coaster_model_name: str = coasters[self.rng.randint(0, len(coasters))]
                        object_id = Controller.get_unique_id()
                        child_object_ids.append(object_id)
                        self.commands.extend(Controller.get_add_physics_object(model_name=coaster_model_name,
                                                                               position=TDWUtils.array_to_vector3(cup_position),
                                                                               rotation={"x": 0, "y": float(self.rng.randint(-25, 25)), "z": 0},
                                                                               object_id=object_id,
                                                                               library="models_core.json"))
                        coaster_record = Controller.MODEL_LIBRARIANS["models_core.json"].get_record(coaster_model_name)
                        y = cup_position[1] + coaster_record.bounds["top"]["y"]
                    else:
                        y = cup_position[1]
                    # Add a cup or wine glass.
                    if self.rng.random() > 0.5:
                        cup_category = "cup"
                    else:
                        cup_category = "wineglass"
                    cups = ProcGenObjects.MODEL_CATEGORIES[cup_category]
                    cup_model_name = cups[self.rng.randint(0, len(cups))]
                    # Add the cup.
                    object_id = Controller.get_unique_id()
                    child_object_ids.append(object_id)
                    self.commands.extend(Controller.get_add_physics_object(model_name=cup_model_name,
                                                                           object_id=object_id,
                                                                           position={"x": float(cup_position[0]),
                                                                                     "y": y,
                                                                                     "z": float(cup_position[2])},
                                                                           rotation={"x": 0,
                                                                                     "y": float(self.rng.uniform(0, 360)),
                                                                                     "z": 0},
                                                                           library="models_core.json"))
                plate_height = Controller.MODEL_LIBRARIANS["models_core.json"].get_record(plate_model_name).bounds["top"]["y"]
                # Add food.
                if self.rng.random() < 0.66:
                    food_categories = ["apple", "banana", "chocolate", "orange", "sandwich"]
                    food_category: str = food_categories[self.rng.randint(0, len(food_categories))]
                    food = ProcGenObjects.MODEL_CATEGORIES[food_category]
                    food_model_name = food[self.rng.randint(0, len(food))]
                    food_position = [plate_position[0] + self.rng.uniform(-0.05, 0.05),
                                     plate_position[1] + plate_height,
                                     plate_position[2] + self.rng.uniform(-0.05, 0.05)]
                    object_id = Controller.get_unique_id()
                    child_object_ids.append(object_id)
                    self.commands.extend(Controller.get_add_physics_object(model_name=food_model_name,
                                                                           object_id=object_id,
                                                                           position=TDWUtils.array_to_vector3(food_position),
                                                                           rotation={"x": 0,
                                                                                     "y": rotation + float(self.rng.uniform(0, 360)),
                                                                                     "z": 0},
                                                                           library="models_core.json"))
        # Add a centerpiece.
        if self.rng.random() < 0.75:
            object_id = Controller.get_unique_id()
            child_object_ids.append(object_id)
            self.commands.extend(Controller.get_add_physics_object(model_name=centerpiece_model_name,
                                                                   object_id=object_id,
                                                                   position={"x": object_position["x"] + float(self.rng.uniform(-0.1, 0.1)),
                                                                             "y": float(top_arr[1]),
                                                                             "z": object_position["z"] + float(self.rng.uniform(-0.1, 0.1))},
                                                                   rotation={"x": 0,
                                                                             "y": float(self.rng.uniform(0, 360)),
                                                                             "z": 0},
                                                                   library="models_core.json"))
        self._add_rotation_commands(parent_object_id=root_object_id,
                                    child_object_ids=child_object_ids,
                                    rotation=rotation,
                                    parent_object_name=record.name)
        return record

    def add_kitchen_counters_and_appliances(self, region: int = 0) -> None:
        # Decide which layout to use.
        roll = self.rng.random()
        room = self.scene_bounds.rooms[region]
        if room.bounds[0] > room.bounds[2]:
            long_walls = [CardinalDirection.north, CardinalDirection.south]
            short_walls = [CardinalDirection.west, CardinalDirection.east]
        else:
            long_walls = [CardinalDirection.east, CardinalDirection.west]
            short_walls = [CardinalDirection.north, CardinalDirection.south]
        # Straight.
        if roll < 1. / 5:
            wall = long_walls[self.rng.randint(0, len(long_walls))]
            position = self._get_lateral_arrangement_start_position(wall=wall, region=region)
            categories = ["refrigerator", "kitchen_counter", "sink", "dishwasher", "stove", "kitchen_counter"]
            if self.rng.random() < 0.5:
                categories.reverse()
            self._add_lateral_arrangement(wall=wall, position=position, categories=categories)
        # Parallel.
        elif roll < 2. / 5:
            if self.rng.random() < 0.5:
                long_walls.reverse()
            for wall, categories in zip(long_walls, [["refrigerator", "kitchen_counter", "sink", "dishwasher"],
                                                     ["kitchen_counter", "stove", "kitchen_counter", "kitchen_counter"]]):
                if self.rng.random() < 0.5:
                    categories.reverse()
                position = self._get_lateral_arrangement_start_position(wall=wall, region=region)
                self._add_lateral_arrangement(wall=wall, position=position, categories=categories)
        # L-shaped.
        elif roll < 3. / 5:
            # TODO add the corner piece!
            long_wall = long_walls[self.rng.randint(0, len(long_walls))]
            position = self._get_lateral_arrangement_start_position(wall=long_wall, region=region)
            categories = ["kitchen_counter", "dishwasher", "sink", "kitchen_counter", "stove", "kitchen_counter"]
            if self.rng.random() < 0.5:
                categories.reverse()
            self._add_lateral_arrangement(wall=long_wall, position=position, categories=categories)
            # Add the other side.
            short_wall = short_walls[self.rng.randint(0, len(short_walls))]
            position = self._get_lateral_arrangement_start_position(wall=short_wall, region=region, offset_corner=True)
            categories = ["kitchen_counter", "kitchen_counter", "refrigerator", "shelf", "kitchen_counter"]
            self._add_lateral_arrangement(wall=short_wall, position=position, categories=categories)
        # U-shaped or G-shaped.
        else:
            # TODO add the corner piece!
            if self.rng.random():
                long_walls.reverse()
            wall = long_walls[0]
            position = self._get_lateral_arrangement_start_position(wall=wall, region=region)
            categories = ["kitchen_counter", "dishwasher", "sink", "kitchen_counter", "kitchen_counter", "kitchen_counter"]
            if self.rng.random() < 0.5:
                categories.reverse()
            self._add_lateral_arrangement(wall=wall, position=position, categories=categories)
            # Add the other side.
            if self.rng.random():
                short_walls.reverse()
            wall = short_walls[0]
            position = self._get_lateral_arrangement_start_position(wall=wall, region=region, offset_corner=True)
            categories = ["kitchen_counter", "kitchen_counter", "refrigerator", "shelf", "kitchen_counter"]
            if self.rng.random() < 0.5:
                categories.reverse()
            self._add_lateral_arrangement(wall=wall, position=position, categories=categories)
            # Add the other-other side.
            wall = short_walls[1]
            position = self._get_lateral_arrangement_start_position(wall=wall, region=region, offset_corner=True)
            categories = ["kitchen_counter", "stove", "kitchen_counter", "kitchen_counter"]
            if self.rng.random() < 0.5:
                categories.reverse()
            self._add_lateral_arrangement(wall=wall, position=position, categories=categories)
            # G-shaped.
            if roll > .4 / 5:
                wall = long_walls[1]
                position = self._get_lateral_arrangement_start_position(wall=wall, region=region, offset_corner=True)
                categories = ["kitchen_counter", "kitchen_counter"]
                self._add_lateral_arrangement(wall=wall, position=position, categories=categories)

    def _get_root_object(self, category: str, position: Union[np.array, Dict[str, float]], region: int = 0,
                         parent: ModelRecord = None,
                         direction: CardinalDirection = None) -> Tuple[Optional[ModelRecord], int, Dict[str, float]]:
        """
        Try to add a root object to the scene.

        :param category: The category of the root object.
        :param position: The position of the root object as either a numpy array or a dictionary.
        :param region: The index of the region in `self.scene_bounds`.
        :param parent: The record of the parent object.
        :param direction: If not None, offset the position along this direction.

        :return: Tuple: A model record (None if the object wasn't added), the object ID (-1 if the object wasn't added), the object position as a dictionary.
        """

        region_bounds = self.scene_bounds.rooms[region]
        # Get the root object position as a dictionary.
        if isinstance(position, dict):
            object_position = position
        elif isinstance(position, np.ndarray) or isinstance(position, list):
            object_position = TDWUtils.array_to_vector3(position)
        else:
            raise Exception(f"Invalid position argument: {position}")
        # Get the possible root objects.
        record, object_position = self._get_model_that_fits_in_region(model_names=ProcGenObjects.MODEL_CATEGORIES[category][:],
                                                                      object_position=object_position,
                                                                      region_bounds=region_bounds,
                                                                      parent=parent,
                                                                      direction=direction)
        if record is None:
            return None, -1, object_position
        # Record that this category has been used.
        if category in ProcGenObjects.UNIQUE_CATEGORIES:
            self._used_unique_categories.append(category)
        root_object_id = Controller.get_unique_id()
        self.commands.extend(Controller.get_add_physics_object(model_name=record.name,
                                                               position=object_position,
                                                               library="models_core.json",
                                                               object_id=root_object_id,
                                                               kinematic=category in ProcGenObjects.KINEMATIC_CATEGORIES))
        return record, root_object_id, object_position

    def _get_objects_on_top_of(self, category: str, position: Union[np.array, Dict[str, float]], rotation: float,
                               region: int = 0, parent: ModelRecord = None,
                               direction: CardinalDirection = None) -> Optional[ModelRecord]:
        """
        Add a root object and add objects on  top of it.

        :param category: The category of the root object.
        :param position: The position of the root object.
        :param rotation: The rotation of the root object.
        :param region: The index of the region in `self.scene_bounds`.
        :param parent: The record of the parent object. Can be None.
        :param direction: The direction from the previous object.

        :return: A model record if anything was added to the scene.
        """

        record, root_object_id, object_position = self._get_root_object(category=category, position=position,
                                                                        region=region, parent=parent,
                                                                        direction=direction)
        if record is None:
            return None
        model_size = TDWUtils.get_bounds_extents(bounds=record.bounds)
        # Get the top position of the object.
        object_top = {"x": object_position["x"],
                      "y": record.bounds["top"]["y"] + object_position["y"],
                      "z": object_position["z"]}
        # Get the dimensions of the object's occupancy map.
        cell_size, density = self._get_rectangular_arrangement_parameters(category=category)
        surface_size = (model_size[0] * 0.8, model_size[2] * 0.8)
        # Add objects on top of the root object.
        object_commands, object_ids = self._get_rectangular_arrangement(size=surface_size,
                                                                        categories=self._vertical_spatial_relations[_VerticalSpatialRelation.on_top_of][category],
                                                                        center=object_top,
                                                                        cell_size=cell_size,
                                                                        density=density)
        self.commands.extend(object_commands)
        # Rotate everything.
        self._add_rotation_commands(parent_object_name=record.name, parent_object_id=root_object_id,
                                    child_object_ids=object_ids, rotation=rotation)
        return record

    def _add_lateral_arrangement(self, wall: CardinalDirection, position: Union[np.array, Dict[str, float]],
                                 categories: List[str], region: int = 0) -> None:
        """
        Add objects along a direction defined by `wall`. The objects can have other child objects.

        :param wall: The wall as a [`CardinalDirection`](../cardinal_direction.md). This determines the rotation and direction of the arrangement. For example, an arrangement 'along' the `north` wall will run `west` to `east` and the objects will be rotated by 0 degrees.
        :param position: The position of the first object.
        :param categories: An *ordered* list of categories; each object will be added in this order.
        :param region: The index of the region in `self.scene_bounds`.
        """

        if wall == CardinalDirection.north:
            direction = CardinalDirection.east
            rotation: int = 180
        elif wall == CardinalDirection.south:
            direction = CardinalDirection.east
            rotation = 0
        elif wall == CardinalDirection.west:
            direction = CardinalDirection.north
            rotation = 270
        elif wall == CardinalDirection.east:
            direction = CardinalDirection.north
            rotation = 90
        else:
            raise Exception(wall)
        # Get the root object position as a dictionary.
        if isinstance(position, dict):
            object_position = position
        elif isinstance(position, np.ndarray) or isinstance(position, list):
            object_position = TDWUtils.array_to_vector3(position)
        else:
            raise Exception(f"Invalid position argument: {position}")
        # Get each object.
        for category in categories:
            # Add a kitchen counter.
            if category == "kitchen_counter":
                record = self.add_kitchen_counter(position={k: v for k, v in object_position.items()},
                                                  rotation=rotation,
                                                  region=region,
                                                  direction=direction)
                if record is None:
                    return
            # Add a shelf.
            elif category == "shelf":
                record = self.add_shelf(position={k: v for k, v in object_position.items()},
                                        rotation=rotation,
                                        region=region,
                                        direction=direction)
                if record is None:
                    return
            else:
                record, position = self._get_model_that_fits_in_region(model_names=ProcGenObjects.MODEL_CATEGORIES[category],
                                                                       object_position={k: v for k, v in object_position.items()},
                                                                       region_bounds=self.scene_bounds.rooms[region],
                                                                       direction=direction)
                # No object fits.
                if record is None:
                    return
                # Add the object.
                if record.name in ProcGenObjects._CANONICAL_ROTATIONS:
                    r = rotation + ProcGenObjects._CANONICAL_ROTATIONS[record.name]
                else:
                    r = rotation
                self.commands.extend(Controller.get_add_physics_object(model_name=record.name,
                                                                       object_id=Controller.get_unique_id(),
                                                                       position=position,
                                                                       rotation={"x": 0, "y": r, "z": 0},
                                                                       library="models_core.json",
                                                                       kinematic=True))
            # Update the position.
            extents = TDWUtils.get_bounds_extents(bounds=record.bounds)
            if category == "shelf":
                i = extents[2]
            else:
                i = extents[0]
            if direction == CardinalDirection.north or direction == CardinalDirection.south:
                object_position["z"] += i
            else:
                object_position["x"] += i

    def _get_lateral_arrangement_start_position(self, wall: CardinalDirection, region: int = 0,
                                                offset_corner: bool = False) -> Dict[str, float]:
        """
        :param wall: The wall.
        :param region: The ID of the region.
        :param offset_corner: If True, offset the corner.

        :return: The starting position for a lateral arrangement along the wall.
        """

        offset = 0.6081842 * 2
        room = self.scene_bounds.rooms[region]
        if wall == CardinalDirection.north:
            position = {"x": room.x_min + ProcGenObjects._WALL_DEPTH,
                        "y": 0,
                        "z": room.z_max - ProcGenObjects._WALL_DEPTH}
            if offset_corner:
                position["x"] -= offset
        elif wall == CardinalDirection.south:
            position = {"x": room.x_min + ProcGenObjects._WALL_DEPTH,
                        "y": 0,
                        "z": room.z_min + ProcGenObjects._WALL_DEPTH}
            if offset_corner:
                position["x"] += offset
        elif wall == CardinalDirection.west:
            position = {"x": room.x_max - ProcGenObjects._WALL_DEPTH,
                        "y": 0,
                        "z": room.z_min - ProcGenObjects._WALL_DEPTH}
            if offset_corner:
                position["z"] += offset
        elif wall == CardinalDirection.east:
            position = {"x": room.x_min + ProcGenObjects._WALL_DEPTH,
                        "y": 0,
                        "z": room.z_min + ProcGenObjects._WALL_DEPTH}
            if offset_corner:
                position["z"] += offset
        else:
            raise Exception(wall)
        return position

    def _get_rectangular_arrangement(self, size: Tuple[float, float], center: Union[np.array, Dict[str, float]],
                                     categories: List[str], density: float = 0.4,
                                     cell_size: float = 0.05) -> Tuple[List[dict], List[int]]:
        """
        Get a random arrangement of objects in a rectangular space.

        :param size: The size of the rectangle in worldspace coordinates.
        :param center: The position of the center of the rectangle.
        :param categories: Models will be randomly chosen from these categories.
        :param density: The probability of a "cell" in the arrangement being empty. Lower value = a higher density of small objects.
        :param cell_size: The size of each cell in the rectangle. This controls the minimum size of objects and the density of the arrangement.

        :return: Tuple: A list of commands to add the objects, the IDs of the objects.
        """

        # Get numpy array and dictionary representations of the center position.
        if isinstance(center, dict):
            center_dict = center
        else:
            center_dict = TDWUtils.array_to_vector3(center)
        if size[0] > size[1]:
            size = (size[1], size[0])
        # Get the x, z positions.
        xs: np.array = np.arange(cell_size, size[0] - cell_size, cell_size)
        zs: np.array = np.arange(cell_size, size[1] - cell_size, cell_size)
        # Get the occupancy map.
        occupancy_map: np.array = np.zeros(shape=(len(xs), len(zs)), dtype=bool)
        # Print a warning about bad categories.
        bad_categories = [c for c in categories if c not in ProcGenObjects.MODEL_CATEGORIES]
        if len(bad_categories) > 0:
            print(f"WARNING! Invalid model categories: {bad_categories}")
        # Get the semi-minor axis of the rectangle's size.
        semi_minor_axis = (size[0] if size[0] < size[1] else size[1]) - (cell_size * 2)
        # Get valid objects.
        model_sizes: Dict[str, float] = dict()
        model_cell_sizes: List[int] = list()
        models_and_categories: Dict[str, str] = dict()
        for category in categories:
            if category not in ProcGenObjects.MODEL_CATEGORIES:
                continue
            # Get objects small enough to fit within the rectangle.
            for model_name in ProcGenObjects.MODEL_CATEGORIES[category]:
                record = Controller.MODEL_LIBRARIANS["models_core.json"].get_record(model_name)
                model_size = TDWUtils.get_bounds_extents(bounds=record.bounds)
                model_semi_major_axis = model_size[0] if model_size[0] > model_size[2] else model_size[2]
                if model_semi_major_axis < semi_minor_axis:
                    model_sizes[model_name] = model_semi_major_axis
                    model_cell_sizes.append(int(model_semi_major_axis / cell_size) + 1)
                    models_and_categories[model_name] = category
        commands: List[dict] = list()
        object_ids: List[int] = list()
        # Get all of the sizes in occupancy map space.
        model_cell_sizes = list(set(model_cell_sizes))
        model_cell_sizes.reverse()
        for ix, iz in np.ndindex(occupancy_map.shape):
            # Exclude edges.
            if ix == 0 or ix == occupancy_map.shape[0] - 1 or iz == 0 or iz == occupancy_map.shape[1]:
                continue
            # This position is already occupied. Sometimes, skip a position.
            if occupancy_map[ix][iz] or self.rng.random() < density:
                continue
            # Get the minimum object semi-major axis.
            sma = model_cell_sizes[0]
            for mcs in model_cell_sizes:
                # Stop if the the semi-major axis doesn't fit (it would fall off the edge).
                if ix - mcs < 0 or ix + mcs >= occupancy_map.shape[0] or iz - mcs < 0 or iz + mcs >= occupancy_map.shape[1]:
                    break
                else:
                    # Define the circle.
                    circle_mask = TDWUtils.get_circle_mask(shape=(occupancy_map.shape[0], occupancy_map.shape[1]),
                                                           row=ix, column=iz, radius=mcs)
                    # There is overlap. Stop here.
                    if np.count_nonzero((circle_mask == True) & (occupancy_map == True)) > 0:
                        break
                    else:
                        sma = mcs
            # Get all objects that fit.
            model_names = [m for m in model_sizes if int(model_sizes[m] / cell_size) <= sma]
            if len(model_names) == 0:
                continue
            # Choose a random model.
            model_name: str = model_names[self.rng.randint(0, len(model_names))]
            # Get the position. Perturb it slightly.
            x = (ix * cell_size) + self.rng.uniform(-cell_size * 0.025, cell_size * 0.025)
            z = (iz * cell_size) + self.rng.uniform(-cell_size * 0.025, cell_size * 0.025)
            # Offset from the center.
            x += center_dict["x"] - size[0] / 2 + cell_size
            z += center_dict["z"] - size[1] / 2 + cell_size
            # Cache the object ID.
            object_id = Controller.get_unique_id()
            # Set the rotation.
            model_category = models_and_categories[model_name]
            object_ids.append(object_id)
            if model_category in ProcGenObjects.KINEMATIC_CATEGORIES:
                object_rotation = 0
            else:
                object_rotation = self.rng.uniform(0, 360)
            # Add the object.
            commands.extend(Controller.get_add_physics_object(model_name=model_name,
                                                              position={"x": x, "y": center_dict["y"], "z": z},
                                                              rotation={"x": 0, "y": object_rotation, "z": 0},
                                                              object_id=object_id,
                                                              library="models_core.json"))
            # Record the position on the occupancy map.
            occupancy_map[TDWUtils.get_circle_mask(shape=(occupancy_map.shape[0], occupancy_map.shape[1]),
                                                   row=ix, column=iz, radius=sma) == True] = True
        return commands, object_ids

    @staticmethod
    def _get_rectangular_arrangement_parameters(category: str) -> Tuple[float, float]:
        """
        :param category: The category

        :return: Tuple: The cell size and density.
        """

        if category not in ProcGenObjects.RECTANGULAR_ARRANGEMENTS:
            return 0.05, 0.4
        return ProcGenObjects.RECTANGULAR_ARRANGEMENTS[category]["cell_size"], ProcGenObjects.RECTANGULAR_ARRANGEMENTS[category]["density"]

    @staticmethod
    def _model_fits_in_region(record: ModelRecord, position: Dict[str, float], region_bounds: RegionBounds) -> bool:
        """
        :param record: The model record.
        :param position: The position of the object.
        :param region_bounds: The region (room) bounds.

        :return: True if the model fits in the region.
        """

        # Get the (x, z) positions of the bounds.
        for point in [[record.bounds["left"]["x"] + position["x"], record.bounds["left"]["z"] + position["z"]],
                      [record.bounds["right"]["x"] + position["x"], record.bounds["right"]["z"] + position["z"]],
                      [record.bounds["front"]["x"] + position["x"], record.bounds["front"]["z"] + position["z"]],
                      [record.bounds["back"]["x"] + position["x"], record.bounds["back"]["z"] + position["z"]],
                      [record.bounds["center"]["x"] + position["x"], record.bounds["center"]["z"] + position["z"]]]:
            if not region_bounds.is_inside(x=point[0], z=point[1]):
                return False
        return True

    def _get_model_that_fits_in_region(self, model_names: List[str], object_position: Dict[str, float],
                                       region_bounds: RegionBounds, parent: ModelRecord = None,
                                       direction: CardinalDirection = None) -> Tuple[Optional[ModelRecord], Optional[Dict[str, float]]]:
        self.rng.shuffle(model_names)
        # Get the first object, if any, that fits in the region bounds.
        got_model_name = False
        record = Controller.MODEL_LIBRARIANS["models_core.json"].records[0]
        position = {"x": 0, "y": 0, "z": 0}
        for mn in model_names:
            record = Controller.MODEL_LIBRARIANS["models_core.json"].get_record(mn)
            # Offset the position.
            if direction is not None:
                extents = TDWUtils.get_bounds_extents(bounds=record.bounds)
                if direction == CardinalDirection.north:
                    position = {"x": object_position["x"] - extents[0] / 4,
                                "y": object_position["y"],
                                "z": object_position["z"] + extents[2] / 2}
                elif direction == CardinalDirection.south:
                    position = {"x": object_position["x"] + extents[0] / 4,
                                "y": object_position["y"],
                                "z": object_position["z"] - extents[2] / 2}
                elif direction == CardinalDirection.west:
                    position = {"x": object_position["x"] - extents[0] / 2,
                                "y": object_position["y"],
                                "z": object_position["z"] - extents[2] / 4}
                elif direction == CardinalDirection.east:
                    position = {"x": object_position["x"] + extents[0] / 2,
                                "y": object_position["y"],
                                "z": object_position["z"] + extents[2] / 4}
                else:
                    raise Exception(direction)
            else:
                position = object_position
            if ProcGenObjects._model_fits_in_region(record=record, position=position,
                                                    region_bounds=region_bounds) and \
                    (parent is None or self._fits_inside(parent, record)):
                got_model_name = True
                break
        if not got_model_name:
            return None, None
        else:
            return record, position

    def _add_rotation_commands(self, parent_object_name: str, parent_object_id: int, child_object_ids: List[int], rotation: float) -> None:
        """
        Add commands to parent the child objects to the parent object, rotate the parent object, and unparent the child objects.

        :param parent_object_name: The name of the parent object.
        :param parent_object_id: The ID of the parent object.
        :param child_object_ids: The IDs of the child objects.
        :param rotation: The rotation of the parent object.
        """

        if parent_object_name in ProcGenObjects._CANONICAL_ROTATIONS:
            r = rotation + ProcGenObjects._CANONICAL_ROTATIONS[parent_object_name]
        else:
            r = rotation
        # Parent all objects to the root object.
        for child_object_id in child_object_ids:
            self.commands.append({"$type": "parent_object_to_object",
                                  "id": child_object_id,
                                  "parent_id": parent_object_id})
        # Rotate the root object.
        self.commands.append({"$type": "rotate_object_by",
                              "angle": r,
                              "id": parent_object_id,
                              "axis": "yaw",
                              "is_world": True,
                              "use_centroid": False})
        # Unparent all of the objects from the root object.
        for child_object_id in child_object_ids:
            self.commands.append({"$type": "unparent_object",
                                  "id": child_object_id})

    @staticmethod
    def _fits_inside(parent: ModelRecord, child: ModelRecord) -> bool:
        """
        :param parent: The record of the parent object.
        :param child: The record of the child object.

        :return: True if the child object fits in the the parent object.
        """

        parent_extents = TDWUtils.get_bounds_extents(parent.bounds)
        child_extents = TDWUtils.get_bounds_extents(child.bounds)
        return parent_extents[0] > child_extents[0] and parent_extents[2] > child_extents[2]

    def _get_chair_position(self, chair_record: ModelRecord, table_bottom: np.array,
                            table_bound_point: np.array) -> np.array:
        """
        :param chair_record: The chair model record.
        :param table_bottom: The bottom-center position of the table.
        :param table_bound_point: The bounds position.

        :return: A position for a chair around the table.
        """

        position_to_center = table_bound_point - table_bottom
        position_to_center_normalized = position_to_center / np.linalg.norm(position_to_center)
        # Scoot the chair back by half of its front-back extent.
        half_extent = (np.linalg.norm(TDWUtils.vector3_to_array(chair_record.bounds["front"]) -
                                      TDWUtils.vector3_to_array(chair_record.bounds["back"]))) / 2
        # Move the chair position back. Add some randomness for spice.
        chair_position = table_bound_point + (position_to_center_normalized *
                                              (half_extent + self.rng.uniform(-0.1, -0.05)))
        chair_position[1] = 0
        return chair_position
