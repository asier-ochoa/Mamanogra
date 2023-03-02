def get_function_default_args(func):
    return {
        k: v for k, v
        in zip(
            [
                x for i, x in enumerate(func.__code__.co_varnames)
                if i >= func.__code__.co_argcount - len(func.__defaults__)
            ],
            func.__defaults__
        )
    }
