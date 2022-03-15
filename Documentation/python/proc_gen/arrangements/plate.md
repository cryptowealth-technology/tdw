# Plate

`from tdw.proc_gen.arrangements.plate import Plate`

A kitchen plate.

- The plate model is chosen randomly; see `TableSetting.MODEL_CATEGORIES["plate"]`.
- The plate might have food on it; see `food_probability` in the constructor.
  - The possible food categories are `TableSetting.FOOD_CATEGORIES`.
  - See `TableSetting.MODEL_CATEGORIES` for a list of models within those categories.
  - The position of the food is perturbed randomly.
  - The rotation of the food is random.

***

## Fields

- `root_object_id` The ID of the root object.

- `object_ids` A list of all of the object IDs in this arrangement.

- `object_ids` A list of all of the object IDs in this arrangement.

***

## Class Variables

| Variable | Type | Description | Value |
| --- | --- | --- | --- |
| `MODEL_CATEGORIES` | Dict[str, List[str]] | A dictionary of all of the models that may be used for procedural generation. Key = The category. Value = A list of model names. Note that this category overlaps with, but is not the same as, `model_record.wcategory`; see: `Arrangement.get_categories_and_wcategories()`. | `loads(Path(resource_filename(__name__, "data/models.json")).read_text())` |
| `DEFAULT_CELL_SIZE` | float | The default span used for arranging objects next to each other. | `0.6096` |
| `INSIDE_OF` | Dict[str, List[str]] | A dictionary of categories that can be inside of other categories. Key = A category. Value = A list of categories of models that can inside of the key category. | `loads(Path(resource_filename(__name__, "data/inside_of.json")).read_text())` |
| `ENCLOSED_BY` | Dict[str, List[str]] | A dictionary of categories that can be enclosed by other categories. Key = A category. Value = A list of categories of models that can enclosed by the key category. | `loads(Path(resource_filename(__name__, "data/enclosed_by.json")).read_text())` |
| `FOOD_CATEGORIES` | List[str] | The categories of possible food models. | `["apple", "banana", "chocolate", "orange", "sandwich"]` |
| `ON_TOP_OF` | Dict[str, List[str]] | A dictionary of categories that can be on top of other categories. Key = A category. Value = A list of categories of models that can be on top of the key category. | `loads(Path(resource_filename(__name__, "data/on_top_of.json")).read_text())` |

***

## Functions

#### \_\_init\_\_

**`Plate(food_probability, position)`**

**`Plate(food_probability, model=None, position, rng=None)`**

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| food_probability |  float |  | The probability of placing food on the plate. |
| model |  Union[str, ModelRecord] | None | Either the name of the model (in which case the model must be in `models_core.json`), or a `ModelRecord`, or None. If None, a random model is selected. |
| position |  Dict[str, float] |  | The position of the root object. This might be adjusted. |
| rng |  np.random.RandomState  | None | The random number generator. If None, a new random number generator is created. |

#### get_categories_and_wcategories

**`Arrangement.get_categories_and_wcategories()`**

_(Static)_

_Returns:_  A dictionary of the categories of every model that can be used by `Arrangement` and their corresponding `wcategory` and `wnid`. Key = The model name. Value = A dictionary with the following keys: `"category"` (the `ProcGenObjects` category), `"wcategory"` (the value of `record.wcategory`), and `"wnid"` (the value of `record.wnid`).

#### get_commands

**`self.get_commands()`**

_Returns:_  A list of commands that will generate the arrangement.