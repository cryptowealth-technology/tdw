# Benchmark

`from tdw.add_ons.benchmark import Benchmark`

Benchmark the FPS over a given number of frames.

```python
from tdw.controller import Controller
from tdw.add_ons.benchmark import Benchmark

c = Controller()
b = Benchmark()
b.start()
c.add_ons.append(b)
while b.fps < 0:
    c.communicate([])
b.stop()
c.communicate({"$type": "terminate"})
print(b.speed)
```

***

## Fields

- `commands` These commands will be appended to the commands of the next `communicate()` call.

- `initialized` If True, this module has been initialized.

- `times` A list of time elapsed per `communicate()` call.

***

## Functions

#### \_\_init\_\_

**`Benchmark()`**

(no parameters)

#### get_initialization_commands

**`self.get_initialization_commands()`**

_Returns:_  A list of commands that will initialize this module.

#### before_send

**`self.before_send(commands)`**

This is called before sending commands to the build. By default, this function doesn't do anything.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| commands |  List[dict] |  | The commands that are about to be sent to the build. |

### on_send

**`self.on_send(resp)`**

This is called after commands are sent to the build and a response is received.

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| resp |  List[bytes] |  | The response from the build. |

#### start

**`self.start()`**

Start bencharking each `communicate()` call and clear `self.times`.

#### stop

**`self.stop()`**

Stop benchmarking each `communicate()` call.

#### get_speed

**`self.get_speed()`**

_Returns:_  The average time elapsed per `communicate()` call.
