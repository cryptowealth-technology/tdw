# RegionBounds

`from scene_data.region_bounds import RegionBounds`

Data for the bounds of a region in a scene. In an interior scene, this usually corresponds to a room.

***

## Fields

- `region_id` The ID of the region.

- `center` The center of the region.

- `bounds` The bounds of the region.

- `x_min` Minimum x positional coordinate of the room.

- `y_min` Minimum y positional coordinate of the room.

- `z_min` Minimum z positional coordinate of the room.

- `x_max` Maximum x positional coordinate of the room.

- `y_max` Maximum y positional coordinate of the room.

- `z_max` Maximum z positional coordinate of the room.

***

## Functions

#### \_\_init\_\_

**`RegionBounds(scene_regions, i)`**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| scene_regions |  SceneRegions |  | The scene regions output data. |
| i |  int |  | The index of this scene in env.get_num() |

#### is_inside

**`self.is_inside(x, z)`**


| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| x |  float |  | The x coordinate. |
| z |  float |  | The z coordinate. |

_Returns:_  True if position (x, z) is in the scene.

