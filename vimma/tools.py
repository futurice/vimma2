import importlib
import itertools

def subclassmodels(c, exclude_modules=[], p=lambda x: not x._meta.abstract):
    return filter(lambda x: not any(map(x.__module__.startswith, exclude_modules)),
            filter(p, subclasses(c)))

def subclasses(c):
    return list(itertools.chain.from_iterable(map(subclasses, c.__subclasses__())))\
            + c.__subclasses__()

def get_import(module, thing):
    m = importlib.import_module(module)
    return getattr(m, thing)
