from concurrent.futures import ThreadPoolExecutor, Future


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


def make_class_methods_threaded():
    def wrapper(cls):
        cls_init = cls.__init__

        def __init__(self, *args, **kwargs):
            self._threadpool = ThreadPoolExecutor(1, cls.__name__)
            cls_init(self, *args, **kwargs)

        cls.__init__ = __init__
        cls_method_names = [
            a for a in dir(cls)
            if callable(getattr(cls, a)) and not a.startswith("__")
        ]
        for m in cls_method_names:
            prev_method = getattr(cls, m)

            def threaded_method(self, *args, **kwargs) -> Future:
                return self._threadpool.submit(prev_method, self, *args, **kwargs)
            setattr(cls, m, threaded_method)
        return cls

    return wrapper
