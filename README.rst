frpy: minimal functional reactive programming powered by modern python
================================================================================

*Require python Python 3.6+*

**FRP**, a.k.a. functional reactive programming is a programming paradigm to
model time related system better. As a rather radical idea, FRP mainly exists
in theoretical articles. But its (mental) concept is very useful in some
cases and has been adopted partially in many tools like Elm or React among
others. Among other libraries, frpy is:

* super lightweight, core part is merely 64 lines of code without comments.
* carefully designed clock system, support both clock free style and streams
  running in real world time
* totally thread-safe given a clock exits
* take advantage of async python, allowing near-sequential style style with
  `fmap_async`

Full documentation can be found at `API Doc`_.

Key concepts
------------

**Stream** is a sequence of events. It could also be interpret as states
changed stepwise. Continuous changing values like sin(x) over [0, 1] is not
within the scope unless the changing is sampled as discrete events. Each
stream has a clock property, an *orphan* stream is a stream whose clock is
None.

**Clock** is a stream whose clock is itself. Clock is the most important
concept supporting the Stream to ensure thread-safety and greatly reduce the
pain of concurrency. The simplest clock can be constructed by
``Stream(None)`` whose ``clock`` will be set to self, and the time value can
then be injected manually. However, in most cases other than tests it's
better to use the ``clock`` function to get a self-ticking clock.

Different clocks will provide different levels of capabilities. All clock
with increasing substractable values enables all operators, no matter the
values are real timestamp, natural numbers or event more complex structures
(though the time unit differs). Clocks with non-substractable or
non-increasing values will not support time sensitive operators like
``delay`` or ``timeout``.

Example
-----------

**Clock-free style streams**

.. code-block:: python

    from frpy.api import Stream, fmap, where, merge

    # even items from s1 merged with s2
    s1 = Stream(None)
    s2 = Stream(None)
    s3 = fmap(where(lambda x: x % 2 == 0, s1))
    s4 = merge([s2, s3])
    s4.hook = print
    s1(1)
    s1(2)  # 2
    s1(3)
    s2(10)  # 10
    s1(4)  # 4
    s2(9)  # 9
    s1(5)
    s1(6)  # 6
    # The footprint of s4 is: 2, 10, 4, 9, 6

**Streams with manual clock**

.. code-block:: python

    # even items from s1 delayed by 2 time units
    clk = Stream(None)
    clk.clock = clk
    src = Stream(clk)
    s = delay(2, src)
    s.hook = print
    src(0)
    clk(0)  # src will be set here (the next clock tick)
    src(1)
    clk(1)
    clk(2)  # 0
    clk(3)  # empty since value 1 is odd
    clk(4)  # 2


**Complex case: number accumulation with timeout**

Numbers randomly spawn and accumulated. If the accumulated number reaches a
certain value, output "met!" and start next try. If the accumulated number
does not reach the value after a given period, output "fail!" and start next
try.

This simulation is a simplified "try with timeout" problem, which is quite
uneasy for tranditional sequential paradigm (usually threads or event queues
are necessary and may involve concurrency). Following we provide three
methods with frpy to address this problem, each with only about 20-30 lines
of code.

Method 1: pure stream-style approach

.. code-block:: python

    from frpy.api import Stream, fmap, repeat, scan, changed, \
        merge, each, timeout, clock
    from frpy.fp import soft, const  # functional programming helpers
    from functools import partial as bind

    # options
    value_thres = 3
    time_thres = 1.2

    # init the clock
    clk, tick = clock()

    # construct streams
    sp = fmap(soft(random.random), repeat(0.2, clk))
    term = Stream(clk)
    interrupt = timeout(time_thres, term, term)
    value = merge([sp, fmap(const(-1), term)])
    acc = scan(lambda acc, v: acc + v if v >= 0 else 0, 0, value)
    met = changed(lambda _, y: y <= value_thres, acc)
    each(term, merge([met, interrupt]))

    # hook to print trace
    acc.hook = print
    met.hook = bind(print, 'met!')
    interrupt.hook = bind(print, 'fail!')

    # start clock
    tick()


Method 2: more sequential approach with async generator

.. code-block:: python

    import math
    from frpy.api import Stream, fmap, repeat, merge, fmap_async, clock
    from frpy.fp import soft

    # options
    value_thres = 3
    time_thres = 1.2

    clk, tick = clock()
    sp = fmap(soft(random.random), repeat(0.2, clk))

    # aysnc generator transformation
    async def fn(s):
        acc = 0
        last = math.inf
        async for topic, v in s:
            if topic == 'clock':
                if acc > value_thres:
                    met = True
                if v - last > time_thres or acc > value_thres:
                    yield 'met' if met else 'fail'
                    yield 0
                    met = False
                    acc = 0
                    last = v

            elif topic == 'value':
                acc += v
                yield acc

    # map the transformation over async generators to that over streams
    res = fmap_async(fn, merge([clk, sp], ['clock', 'value']))

    # hook to print trace
    res.hook = print
    tick()

Method 3: state reducer approach resembling React and Elm

.. code-block:: python

    from frpy.api import Stream, fmap, repeat, scan, merge, clock
    from frpy.fp import soft

    # options
    value_thres = 3
    time_thres = 1.2

    clk, tick = clock()
    sp = fmap(soft(random.random), repeat(0.2, clk))
    events = merge([clk, sp], ['clock', 'value'])

    # the reducer function to update state, print directly for convenience
    def update(state: Tuple[float, float], event) -> Tuple[float, float]:
        channel, data = event
        start_at, acc = state
        if channel == 'clock':
            if data - start_at > time_thres:
                print('failed')
                return (data, 0)
            return state
        if channel == 'value':
            new_value = acc + data
            print(new_value)
            if new_value >= value_thres:
                print('met')
                return (time.time(), 0)
            return (start_at, new_value)
        else:
            return state

    # we do not use states so just print changes in reducer
    scan(update, (time.time(), 0), events)
    tick()


For detailed docs please refer to `API Doc`_.

Note
-----

**Thread-safety**

Injecting an event to a stream with a clock is thread-safe since all actions
will be scheduled by its clock. Injecting an event to an orphan stream is *NOT*
thread-safe. Users have to be careful if use streams in a clock-free style.

**Clock compatiblities**

Frpy will try its best to construct compatible streams. For unary operators,
clock will always be proporgated. This also means that orphan streams will
always derives orphan streams. For multiary operators like merge, if all
non-orphan upstreams have the same clock, inherit that clock, otherwise
dettach the stream to be orphan to avoid problems. This behavior is
implemented in the ``combine``. It is highly recommended to avoid mixing
clocks or do that only if with good reason, and always manually set the
derived stream's clock.


**Attribution**

This module is heavily inspired by `flyd`_,
with some important design decisions:

1. The atomic update feature is not ported

   The atomic update is quite useful but adds too much complexity in my
   opinion, also the performance gain should not be too much since
   the diamond style dependencies could be avoided in many scenarios.

2. Racial conditions are handled by a central event loop, a.k.a a clock stream

   Python unlike js has no event loop, and the new async API is not easy
   to use in this case. We use the conception of clock when necessary
   with asyncio event loops underhood. Per thread has its clock.

3. No end stream mechanism is implemented

   End streams are useful but may introduce too much dynamism and it has an
   implact on the complexity ofimplementation. It may be added in the future
   after thorough consideration.


.. _API Doc: https://frpy.readthedocs.io/en/latest/index.html
.. _flyd: https://github.com/paldepind/flyd
.. _Wikipedia: https://en.wikipedia.org/wiki/Functional_reactive_programming
