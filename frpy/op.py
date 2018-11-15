import time
import math
import asyncio
from typing import Callable, TypeVar, Any, Generic, Union  # noqa F401
from typing import Tuple, List, Dict, Deque, AsyncIterator, Awaitable, Deque  # noqa F401
from collections import deque
from .core import Stream, combine

T = TypeVar('T')
S = TypeVar('S')


# constructors
def repeat(interval: float, clock: Stream[T]) -> Stream[T]:
    """ repeatedly inject unix timestamp

    Parameters
    ----------
    interval : float
        interval between events
    clock : Stream[T]
        clock stream of world

    Returns
    -------
    Stream[T]
    """

    def g(deps, this, src, value):
        if this() is None or value - this() >= interval:
            return value

    return combine(g, [clock])


# combinators
def fmap(fn: Callable[[T], S], s: Stream[T]) -> Stream[S]:
    """ apply function to every event of a stream
    map operator for Stream the functor

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

    Parameters
    ----------
    fn : Callable[[S, T], S]
        accumulate function, from previous accumulation and arrived event
        to result event
    init : S
        initial value of the accumulation
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[S]
    """
    buffer = [init]

    def g(deps, this, src, value):
        buffer[0] = fn(buffer[0], value)
        return buffer[0]

    return combine(g, [s])


def merge(ss: List[Stream[Any]], topics: List[Any] = None) -> Stream[Any]:
    """ merge multiple streams

    Parameters
    ----------
    ss : List[Stream[Any]]
        streams to be merged
    topics : List[Any], optional
        if provided, events becomes tuples like (topic, original event),
        the i-th topic is applied to the i-th stream

    Returns
    -------
    Stream[Any]
    """

    def g(deps, this, src, value):
        if topics is not None:
            return (topics[ss.index(src)], value)
        return value

    return combine(g, ss)


def window(n: int, s: Stream[T]) -> Stream[List[T]]:
    """ convert to stream of sliding windows of events

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
        current = value
        buffer[0] = current
        return fn(last, current)

    return combine(g, [s])


def changed(eq_fn: Callable[[T, T], bool], s: Stream[T]) -> Stream[T]:
    """ output event when new event is different from the last

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
        if not eq_fn(last, current):
            return current

    return combine(g, [s])


def trace(key_fn: Callable[[T], S], stale: float,
          s: Stream[T]) -> Stream[Stream[T]]:
    """ trace events with the same keys, from a mono stream
    to a stream of streams, each is a tracing stream generating
    when the first event with the key arrives

    Parameters
    ----------
    key_fn : Callable[[T], S]
        function to generate key from the event
    stale : float
        the seconds before a stream gets trimmed if no events arrived
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
        for k, t in updated_at.items():
            if time.time() - t > stale:
                del buffer[key]
                del updated_at[key]
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

    Parameters
    ----------
    ss : Stream[Stream[T]]
        source stream

    Returns
    -------
    Stream[T]
    """
    res: Stream[T] = Stream(ss.clock)
    each(lambda s: s.listeners.append(lambda _, v: res(v)), ss)
    return res


def timeout(t: float, responds: Stream[T], s: Stream[S]) -> Stream[float]:
    """ inject a timeout event if t seconds pass after the last
    event of the source stream and no event from the responding stream has arrived,
    the source stream and the responding stream can be the same

    Parameters
    ----------
    t : float
        limit of elapsed time
    responds : Stream[T]
        responding stream to s
    s : Stream[S]
        source stream (request stream)

    Returns
    -------
    Stream[float]
        timestamps of timeout
    """
    buffer = [time.time()]
    res: Stream[float] = Stream(s.clock)

    def on_s(src, value):
        buffer[0] = time.time()

    def on_respond(src, value):
        buffer[0] = None

    def on_clock(clock, value):
        if buffer[0] is not None and s.clock() - buffer[0] > t:
            res(s.clock())
            buffer[0] = None

    responds.listen(on_respond)
    s.clock.listen(on_clock)
    s.listen(on_s)

    return res


def delay(t: float, s: Stream[T]) -> Stream[T]:
    """ delay every events by specific time
    when delayed t is 0, delay every events by a tick

    Parameters
    ----------
    t : float
        delayed seconds
    s : Stream[T]
        source stream

    Returns
    -------
    Stream[T]
    """
    clock_buffer = [math.inf]
    value_buffer = [None]
    res: Stream[T] = Stream(s.clock)

    def on_t(src, value):
        if value - clock_buffer[0] >= t:
            clock_buffer[0] = math.inf
            res(value_buffer[0])

    def on_s(src, value):
        clock_buffer[0] = s.clock()
        value_buffer[0] = value

    s.clock.listen(on_t)
    s.listen(on_s)

    return res


def each(fn: Callable[[T], None], s: Stream[T]) -> None:
    """ for each event perform an unpure action

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

    s.listen(notify)

    async def a_src():
        while True:
            yield await q.get()

    async def a_res():
        async for v in fn(a_src()):
            res(v)

    asyncio.ensure_future(a_res())
    return res


if __name__ == '__main__':
    import doctest
    doctest.testmod()
