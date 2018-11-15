""" functional programming utilities to use with frp api """


def const(value):
    def f(*args, **kw):
        return value

    return f


def pipe(*funcs):
    '''
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
