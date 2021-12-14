import numpy as np
from typing import List


class KitchenSet:
    """
    A matching set of plates, forks, knives, etc.
    """

    """:class_var
    Plate model name.
    """
    PLATE: str = "plate06"
    """:class_var
    Knife model names.
    """
    KNIVES: List[str] = ["vk0007_steak_knife", "vk0014_dinner_knife_subd2", "vk0055_tableknife"]
    """:class_var
    Fork model names.
    """
    FORKS: List[str] = ["pcylinder222", "vk0010_dinner_fork_subd0", "vk0011_dessert_fork_subd0",
                        "vk0056_tablefork", "vk0067_fishfork"]
    """:class_var
    Spoon model names.
    """
    SPOONS: List[str] = ["vk0002_teaspoon", "vk0054_teaspoon", "vk0058_tablespoon",
                         "vk0060_dessertspoon", "vk0078_fruitspoon", "vk0080_soupspoon"]
    """:class_var
    Wine glass model names.
    """
    WINE_GLASSES: List[str] = ["b04_cantate_crystal_wine_glass", "b04_wineglass", "glass1", "glass2", "glass3"]
    """:class_var
    Mug model name.
    """
    MUG: str = "mug"

    def __init__(self, rng: np.random.RandomState = None):
        """
        :param rng: The random number generator. If None, a new random number generator is created.
        """

        if rng is None:
            rng = np.random.RandomState()
        """:field
        The knife model name.
        """
        self.knife: str = rng.choice(KitchenSet.KNIVES)
        """:field
        The fork model name.
        """
        self.fork: str = rng.choice(KitchenSet.FORKS)
        """:field
        The spoon model name.
        """
        self.spoon: str = rng.choice(KitchenSet.SPOONS)
        """:field
        The wine glass model name.
        """
        self.wine_glass: str = rng.choice(KitchenSet.WINE_GLASSES)