from typing import TypeVar, List, Any
from .core import Stream, combine

T = TypeVar('T')
S = TypeVar('S')


def merge(ss: List[Stream[Any]], topics: List[Any] = None) -> Stream[Any]:
    """ merge multiple streams
    >>> t = []
    >>> s1 = Stream(None)
    >>> s2 = Stream(None)
    >>> ms = merge([s1, s2])
    >>> ms.hook = t.append
    >>> s1(1)
    >>> s1(5)
    >>> s2(7)
    >>> s1(1)
    >>> s2(8)
    >>> t
    [1, 5, 7, 1, 8]

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
