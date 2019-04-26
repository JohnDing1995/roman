from os import environ, getuid, getegid
from os.path import isdir, join

from apluslms_yamlidator.utils.decorator import cached_property

from .backends import BACKENDS, BuildTask, BuildStep, Environment
from .observer import StreamObserver
from .utils.importing import import_string


class Builder:
    def __init__(self, engine, config, observer=None):
        if not isdir(config.dir):
            raise ValueError("config.dir isn't a directory.")
        self.config = config
        self.path = config.dir
        self._engine = engine
        self._observer = observer or StreamObserver()


    def get_steps(self, refs: list = None):
        steps = [BuildStep.from_config(i, step) for i, step in enumerate(self.config.steps)]
        if refs:
            name_dict = {step.name: step for step in steps}
            step_list = [int(ref) if ref.isdigit() else ref for ref in refs]
            try:
                steps = [steps[ref] if isinstance(ref, int) else name_dict[ref] for ref in step_list]
            except KeyError as e:
                raise ValueError("No step named " + str(e))
            except IndexError as e:
                raise ValueError("A step index was too big. Remember, indexing begins with 0.")
        return steps

    def build(self, step_refs: list = None):
        backend = self._engine.backend
        observer = self._observer
        steps = self.get_steps(step_refs)
        task = BuildTask(self.path, steps)
        observer.enter_prepare()
        backend.prepare(task, observer)
        observer.enter_build()
        result = backend.build(task, observer)
        observer.done(data=result)
        return result


class Engine:
    def __init__(self, backend_class=None, settings=None):
        if backend_class is None:
            if settings and 'backend' in settings:
                backend_class = settings['backend']
            else:
                from .backends.docker import DockerBackend as backend_class
        if isinstance(backend_class, str):
            if '.' not in backend_class:
                backend_class = BACKENDS.get(backend_class, backend_class)
            backend_class = import_string(backend_class)
        self._backend_class = backend_class

        name = getattr(backend_class, 'name', None) or backend_class.__name__.lower()
        env_prefix = name.upper() + '_'
        env = {k: v for k, v in environ.items() if k.startswith(env_prefix)}
        if settings:
            for k, v in settings.get(name, {}).items():
                if v is not None and v != '':
                    env[env_prefix + k.replace('-', '_').upper()] = v
        self._environment = Environment(getuid(), getegid(), env)

    @cached_property
    def backend(self):
        return self._backend_class(self._environment)

    def verify(self):
        return self.backend.verify()

    def version_info(self):
        return self.backend.version_info()

    def create_builder(self, *args, **kwargs):
        return Builder(self, *args, **kwargs)
