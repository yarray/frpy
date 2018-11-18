"""
 .. testsetup::
       from frpy.api import Stream
"""
from typing import TypeVar, Generic, List, Callable, Tuple, Any
import asyncio
import time

T = TypeVar('T')
S = TypeVar('S')


def _once(f: Callable, cond=lambda *_: True):
    ''' make the function as stale after it's called extractly once '''

    def g(*args, **kw):
        if cond(*args, **kw):
            f(*args, **kw)
            g.stale = True

    return g


class Stream(Generic[T]):
    """ Stream: The elemental class of frp

    mainly two operations will be used:

    * s() to get current value
    * s(value) to push an event

    Example
    -------
    Basic query/push operations

    >>> from frpy.api import Stream
    >>> s = Stream(None)
    >>> s.trace = print
    >>> s(42)
    42
    >>> s()
    42
    >>> s.listeners.append(lambda _, x: print(x + 1))
    >>> s(10)
    10
    11
    """

    def __init__(self, clock, trace=None):
        self.value: T = None
        self.listeners: List[Callable[[Stream[T], T], None]] = []
        self.clock = clock or self
        self.trace = trace  # function to be call when setting value

    def __call__(self, value=None):
        """
        when call without parameter, get, otherwise set

        Unless it's the origin stream (clock), when the value is set,
        listeners will not be called directly but scheduled as a one-time
        listener appended to the listener list of the clock. This approach
        provides a breadth first order of trggering and ensure that:

        1. Streams with a farther distance to the origin stream will always
        get the value LATER so that event ordering will be intuitive.
        2. All events triggered by one tick will happen in THAT tick prior
        to the subsequent tick so that concurrency issues will not bother.
        """

        def update(*_):
            if self.trace is not None:
                self.trace(value)
            self.value = value
            self.listeners = [
                f for f in self.listeners if not getattr(f, 'stale', False)
            ]
            for f in self.listeners:
                f(self, value)

        if value is None:
            return self.value

        else:
            if self.clock == self:
                update()
            else:
                self.clock.listeners.append(_once(update))

    def listen(self, notify: Callable[['Stream[T]', T], None]):
        if self.value is not None:
            notify(self, self.value)
        self.listeners.append(notify)


def combine(fn: Callable[[List[Stream[Any]], Stream[T], Stream[Any], T], None],
            deps: List[Stream[Any]]) -> Stream[T]:
    """ Combine several upstream streams into a new one

    Example
    -------
    Update
    >>> clk = Stream(None)
    >>> s1 = Stream(clk)
    >>> s2 = Stream(clk)

    Parameters
    ----------
    fn : Callable[[List[Stream[Any]], Stream[T], Stream[Any]], None]
        combining function: (dependents, self, src) -> None
            - dependents
            - self: The returned stream
            - src: The stream who triggers the updating
    deps : List[Stream[Any]]
        dependent streams

    Returns
    -------
    Stream[T]
    """
    s: Stream[T] = Stream(deps[0].clock)

    def notify(src, value):
        s(fn(deps, s, src, value))

    for dep in deps:
        if dep() is not None:
            notify(dep, dep())
        dep.listeners.append(notify)

    return s


def clock(loop: asyncio.AbstractEventLoop = None,
          time_res=0) -> Tuple[Stream[float], Callable[[], None]]:
    """ create a clock stream producing the real world time,
    using an infinite async loop

    Parameters
    ----------
    loop : asyncio.AbstractEventLoop, optional
        async event loop
    time_res : int, optional
        seconds to sleep before next tick, set it to positive decimals
        if only performance issue exists

    Returns
    -------
    Tuple[Stream[float], Callable[[], None]]
        A clock stream and a function to start the clock (run forever)
    """
    loop = loop or asyncio.get_event_loop()
    clk: Stream[float] = Stream(None)

    async def feed_clock(time_block):
        while True:
            clk(time.time())
            await asyncio.sleep(time_block)

    def run():
        loop.run_forever()

    asyncio.ensure_future(feed_clock(time_res), loop=loop)
    return clk, run


if __name__ == '__main__':
    import doctest
    doctest.testmod()
