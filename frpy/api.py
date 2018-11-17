# flake8: noqa: F401
""" A Simple Implementation for Functional Reactive Programming

*Require python Python 3.6+*

This module is heavily inspired by flyd (https://github.com/paldepind/flyd),
with some important design decisions:

1. The atomic update feature is not ported
    The atomic update is quite useful but adds too much complexity in my
    opinion, also the performance gain should not be too much since
    the diamond style dependencies may be avoided in many scenarios
2. Racial conditions are handled by a central event loop, a.k.a a clock stream
    Python unlike js has no event loop, and the new async API is not easy
    to use in this case. We use the conception of clock when necessary
    with asyncio event loops underhood, per thread has its clock
3. No end stream mechanism is implemented
    End streams are useful but may introduce too much dynamism and it has an
    implact on the complexity of implementation. It may be added in the future
    after thorough consideration is taken

Example
-------

>>> counter1 = iter(range(1, 1000))
>>> counter2 = iter(range(-1, -1000, -1))
>>> clk, tick = clock()
>>> sp = fmap(lambda _: next(counter1), repeat(1, clk))
>>> sn = fmap(lambda _: next(counter2), repeat(2, clk))
>>> sns = scan(lambda acc, x: acc + x, 0, sn)
>>> sm = merge([sp, sns])
>>> each(print, sm)
>>> tick()
"""
from .core import Stream, clock
from .op import fmap, repeat, scan, changed, \
    where, merge, trace, flatten, diff, each, timeout, fmap_async, \
    delay
