import time
import asyncio
from typing import Callable, TypeVar
from typing import List, Dict, Deque, AsyncIterator
from collections import deque
from .core import Stream, combine

T = TypeVar('T')
S = TypeVar('S')


def fmap(fn: Callable[[T], S], s: Stream[T]) -> Stream[S]:
    """ apply function to every event of a stream
    map operator for Stream the functor

    >>> # plus 3 to the varying value
    >>> src = Stream(None)
    >>> s = fmap(lambda x: x + 3, src)
    >>> s.hook = print
    >>> src(1)
    4
    >>> src(9)
    12

    Parameters
    ----------
    fn : Callable[[T], S]
        function to process a single event
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[S]
    """

    def g(deps, this, src, value):
        return fn(value)

    return combine(g, [s])


def where(fn: Callable[[T], bool], s: Stream[T]) -> Stream[T]:
    """ preserve events making fn to be true

    >>> # preserve only even number
    >>> src = Stream(None)
    >>> s = where(lambda x: x % 2 == 0, src)
    >>> s.hook = print
    >>> src(17)
    >>> src(4)
    4
    >>> src(10)
    10
    >>> src(5)

    Parameters
    ----------
    fn : Callable[[T], bool]
        when fn is true then preserve the event
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[T]
    """

    def g(deps, this, src, value):
        if fn(value):
            return value

    return combine(g, [s])


def scan(fn: Callable[[S, T], S], init: S, s: Stream[T]) -> Stream[S]:
    """ streams whose event is an accumulation created from the arrived event
    and the previous accumulation

    >>> # add all numbers
    >>> src = Stream(None)
    >>> s = scan(lambda acc, x: acc + x, 0, src)
    >>> s.hook = print
    >>> src(12)
    12
    >>> src(30)
    42

    Parameters
    ----------
    fn : Callable[[S, T], S]
        accumulate function, from previous accumulation and arrived event
        to result event
    init : S
        initial value of the accumulation, if None, use first event as init
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[S]
    """

    def g(deps, this, src, value):
        if this() is None:
            return value if init is None else fn(init, value)
        else:
            return fn(this(), value)

    return combine(g, [s])


def window(n: int, s: Stream[T]) -> Stream[List[T]]:
    """ convert to stream of sliding windows of events

    >>> # sliding window of width 3
    >>> src = Stream(None)
    >>> s = window(3, src)
    >>> s.hook = print
    >>> src(1)
    [1]
    >>> src(2)
    [1, 2]
    >>> src(3)
    [1, 2, 3]
    >>> src(4)
    [2, 3, 4]
    >>> src(5)
    [3, 4, 5]

    Parameters
    ----------
    n : int
        width of the sliding window
    s : Stream[T]
        source stream

    Returns
    -------
    [Stream[List[T]]]
    """
    buffer: Deque[T] = deque(maxlen=n)

    def g(deps, this, src, value):
        buffer.append(value)
        return list(buffer)

    return combine(g, [s])


def diff(fn: Callable[[T, T], S], init: T, s: Stream[T]) -> Stream[S]:
    """ stream of events generated using neighbouring events

    >>> # later minus previous
    >>> src = Stream(None)
    >>> s = diff(lambda x, y: y - x, 0, src)
    >>> s.hook = print
    >>> src(3)
    3
    >>> src(5)
    2
    >>> src(11)
    6

    Parameters
    ----------
    fn : Callable[[T, T], S]
        [description]
    init : T
        [description]
    s : Stream[T]
        [description]

    Returns
    -------
    Stream[S]
        [description]
    """
    buffer = [init]

    def g(deps, this, src, value):
        last = buffer[0]
        buffer[0] = value
        if init is None and this() is None:
            return value
        return fn(last, value)

    return combine(g, [s])


def skip(n: int, s: Stream[T]) -> Stream[T]:
    """ Skip first n events

    >>> s = Stream(None)
    >>> s2 = skip(2, s)
    >>> s2.hook = print
    >>> s(1)
    >>> s(1)
    >>> s(2)
    2
    >>> s(3)
    3

    Parameters
    ----------
    n : int
        the number of events to skip
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[T]
    """
    buffer = [0]

    def g(deps, this, src, value):
        if buffer[0] < n:
            buffer[0] += 1
        else:
            return value

    return combine(g, [s])


def changed(eq_fn: Callable[[T, T], bool], s: Stream[T]) -> Stream[T]:
    """ output event when new event is different from the last

    >>> # detect sharp increasing
    >>> src = Stream(None)
    >>> s = changed(lambda x, y: y - x <= 1, src)
    >>> s.hook = print
    >>> src(12)
    12
    >>> src(13)
    >>> src(14)
    >>> src(17)
    17
    >>> src(18)

    Parameters
    ----------
    eq_fn : Callable[[T, T], bool]
        function to determine whether 2 evengs are equal
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[T]
    """
    buffer = [None]

    def g(deps, this, src, value):
        last = buffer[0]
        current = value
        buffer[0] = current
        if last is None or not eq_fn(last, current):
            return current

    return combine(g, [s])


def trace(key_fn: Callable[[T], S], stale: float,
          s: Stream[T]) -> Stream[Stream[T]]:
    """ trace events with the same keys, from a mono stream
    to a stream of streams, each is a tracing stream generating
    when the first event with the key arrives

    >>> # create sub streams for different ranges of values
    >>> # every 10 create a stream, 1..10, 11..20 are two sub streams
    >>> src = Stream(None)
    >>> s = trace(lambda x: x // 10, 100, src)
    >>> footprints = []
    >>> def update_footprints(sub):
    ...     i = len(footprints)
    ...     footprints.append([sub()])
    ...     sub.hook = footprints[i].append
    >>> s.hook = update_footprints
    >>> src(1)
    >>> footprints
    [[1]]
    >>> src(21)
    >>> footprints
    [[1], [21]]
    >>> src(2)
    >>> footprints
    [[1, 2], [21]]
    >>> src(15)
    >>> footprints
    [[1, 2], [21], [15]]
    >>> src(11)
    >>> footprints
    [[1, 2], [21], [15, 11]]
    >>> src(7)
    >>> footprints
    [[1, 2, 7], [21], [15, 11]]

    Parameters
    ----------
    key_fn : Callable[[T], S]
        function to generate key from the event
    stale : float
        the seconds before a stream gets trimmed if no events arrived,
        works with real time no matter which lock is provided
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[Stream[T]]
    """
    buffer: Dict[S, Stream[T]] = {}
    updated_at: Dict[S, float] = {}

    def g(deps, this, src, value):
        key = key_fn(value)
        # truncate staled sub streams
        for k, t in list(updated_at.items()):
            if time.time() - t > stale:
                del buffer[k]
                del updated_at[k]
        if key not in buffer.keys():
            s = Stream(deps[0].clock)
            buffer[key] = s
            updated_at[key] = time.time()
            s(value)
            return s
        else:
            buffer[key](value)
            updated_at[key] = time.time()

    return combine(g, [s])


def flatten(ss: Stream[Stream[T]]) -> Stream[T]:
    """ redirect every event in stream of streams to a flattened stream

    >>> # flatten a stream of streams
    >>> s1 = Stream(None)
    >>> s2 = Stream(None)
    >>> s3 = Stream(None)
    >>> ss = Stream(None)
    >>> s = flatten(ss)
    >>> footprint = []
    >>> s.hook = footprint.append
    >>> ss(s1)
    >>> s1(1)
    >>> s1(2)
    >>> ss(s2)
    >>> s1(3)
    >>> s2(11)
    >>> s2(12)
    >>> ss(s3)
    >>> s3(10)
    >>> s1(4)
    >>> s2(13)
    >>> footprint
    [1, 2, 3, 11, 12, 10, 4, 13]

    Parameters
    ----------
    ss : Stream[Stream[T]]
        source stream

    Returns
    -------
    Stream[T]
    """
    res: Stream[T] = Stream(ss.clock)

    def on_new_substream(s):
        s.listeners.append(lambda _, v: res(v))

    each(on_new_substream, ss)
    return res


def each(fn: Callable[[T], None], s: Stream[T]) -> None:
    """ for each event perform an unpure action

    >>> # for each to print
    >>> s = Stream(None)
    >>> each(print, s)
    >>> s(1)
    1
    >>> s(5)
    5
    >>> s(11)
    11

    Parameters
    ----------
    fn : Callable[[T], None]
        the action
    s : Stream[T]
        source stream

    Returns
    -------
    None
    """

    def g(deps, this, src, value):
        fn(value)

    combine(g, [s])


def fmap_async(fn: Callable[[AsyncIterator[T]], AsyncIterator[T]],
               s: Stream[T]) -> Stream[T]:
    """
    map async generator transformer fn to stream transformer

    A running AbstractEventLoop is necessary. The most convenient way
    is to use the clock offered by core.clock

    >>> from frpy.api import Stream, clock
    >>> async def transform(s):
    ...     async for e in s:
    ...         if e % 2 != 0:
    ...             yield e + 1
    >>> clk, tick = clock()
    >>> s = Stream(clk)
    >>> s1 = fmap_async(transform, s)
    >>> footprint = []
    >>> s1.hook = footprint.append
    >>> import threading
    >>> loop = asyncio.get_event_loop()
    >>> t = threading.Thread(target=tick, kwargs={'duration': 0.1, 'loop': loop})  # Note
    >>> t.start()
    >>> s(1)
    >>> s(10)
    >>> s(25)
    >>> s(131)
    >>> s(18)
    >>> t.join()
    >>> footprint
    [2, 26, 132]

    *Note: terminating async routines right after events handled is very hard,
    here just use a reasonable timeout*

    Parameters
    ----------
    fn : Callable[[AsyncIterator[T]], AsyncIterator[T]]
        function from async generator to async generator
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[T]
        result stream
    """
    res: Stream[T] = Stream(s.clock)
    q: asyncio.Queue = asyncio.Queue()

    def notify(src, value):
        q.put_nowait(value)

    s.listeners.append(notify)

    async def a_src():
        while True:
            yield await q.get()

    async def a_res():
        async for v in fn(a_src()):
            res(v)

    asyncio.ensure_future(a_res())
    return res
