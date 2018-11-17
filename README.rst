frpy: minimal functional reactive programming powered by modern python
================================================================================

*Require python Python 3.6+*

This module is heavily inspired by `flyd`_,
with some important design decisions:

1. The atomic update feature is not ported

   The atomic update is quite useful but adds too much complexity in my
   opinion, also the performance gain should not be too much since
   the diamond style dependencies may be avoided in many scenarios.

2. Racial conditions are handled by a central event loop, a.k.a a clock stream

   Python unlike js has no event loop, and the new async API is not easy
   to use in this case. We use the conception of clock when necessary
   with asyncio event loops underhood, per thread has its clock.

3. No end stream mechanism is implemented

   End streams are useful but may introduce too much dynamism and it has an
   implact on the complexity of implementation. It may be added in the future
   after thorough consideration is taken.

Example
-----------

.. code-block:: python

    clk, tick = clock()
    sp = sequence(1, iter(range(1, 1000)), clk)
    sn = sequence(2, iter(range(-1, -1000, -1)), clk)
    sns = scan(lambda acc, x: acc + x, 0, sn)
    sm = merge([sp, sns])
    each(print, sm)
    tick()

For detailed docs please refer to `API Doc`_.

.. _API Doc: https://frpy.readthedocs.io/en/latest/index.html
.. _flyd: https://github.com/paldepind/flyd
