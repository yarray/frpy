frpy: minimal functional reactive programming powered by modern python
================================================================================

*Require python Python 3.6+*

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

Key concepts
------------

**Stream** is a sequence of events. It could also be interpret as states
changed stepwise. Continuous changing values like sin(x) over [0,
1] is not within the scope unless the changing is sampled as discrete events.

**Clock** is the most important concept supporting the Stream to ensure
thread-safety and greatly reduce the pain of concurrency. Clock is a special
Stream whose ``clock`` property is itself. The simplest clock can be
constructed by ``Stream(None)`` whose ``clock`` will be set to self, and the
time value can then be injected manually. However, in most cases other than
tests it's better to use the ``clock`` function to get a self-ticking clock.

Different clock will provide differents level of capabilities. All clock
with increasing substractable values enables all operators, no matter the
values are real timestamp, natural numbers or event more complex structures
(though the time unit differs). Clocks with non-substractable or
non-increasing values will not support time sensitive operators like
``delay`` or ``timeout``.

**FRP**, a.k.a. functional reactive programming is a programming paradigm to
model time related system better. As a rather radical idea, FRP mainly exists
in theoretical articles. But its (mental) concept is very useful in some
cases and has been adopted partially in many tools like Elm or React among
others. A comprehensive overview of different types of FRP can be found at

Example
-----------

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
    acc.trace = print
    met.trace = bind(print, 'met!')
    interrupt.trace = bind(print, 'fail!')

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
    res.trace = print
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

    # set output stream and hook print
    out = Stream(clk, trace=print)

    # the reducer function to update state, impure for convenience
    def update(state: Tuple[float, float], event) -> Tuple[float, float]:
        channel, data = event
        start_at, acc = state
        if channel == 'clock':
            if data - start_at > time_thres:
                out('failed')
                return (data, 0)
            return state
        if channel == 'value':
            new_value = acc + data
            out(new_value)
            if new_value >= value_thres:
                out('met')
                return (time.time(), 0)
            return (start_at, new_value)
        else:
            return state

    scan(update, (time.time(), 0), events)
    tick()


For detailed docs please refer to `API Doc`_.

.. _API Doc: https://frpy.readthedocs.io/en/latest/index.html
.. _flyd: https://github.com/paldepind/flyd
