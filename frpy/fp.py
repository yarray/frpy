from typing import Callable, TypeVar
""" functional programming utilities to use with frp api """

T = TypeVar('T')


def const(value: T) -> Callable[..., T]:
    """ a function ignore input and output const value

    >>> f = const(123)
    >>> f()
    123
    >>> f('aaa', 'bbb')
    123

    Parameters
    ----------
    value : T
        value to return

    Returns
    -------
    Callable[..., T]
        the function to return value
    """

    def f(*args, **kw):
        return value

    return f


def soft(fn):
    """ a function ignore input and call wrapped function without args,
    (a "soft" version of the original function)

    >>> s = iter(range(0, 10))
    >>> g = lambda: next(s)
    >>> f = soft(g)
    >>> f('whatever', 456)
    0
    >>> f('xxx')
    1

    Parameters
    ----------
    fn : Callable[[], T]
        function to return value

    Returns
    -------
    Callable[..., T]
        the function to call and return value
    """

    def f(*args, **kw):
        return fn()

    return f


def pipe(*funcs):
    '''
    >>> from frpy.fp import pipe
    >>> add1 = lambda x: x + 1
    >>> add2 = lambda x: x + 2
    >>> pipe(add1, add2)(2)
    5
    '''

    def func(ts):
        res = funcs[0](ts)
        for f in funcs[1:]:
            res = f(res)
        return res

    return func
