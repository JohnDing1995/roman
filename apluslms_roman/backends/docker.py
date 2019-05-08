import docker
from os.path import join

from apluslms_yamlidator.utils.decorator import cached_property

from ..utils.translation import _
from . import (
    Backend,
    BuildResult,
)


Mount = docker.types.Mount


class DockerBackend(Backend):
    name = 'docker'
    debug_hint = _("""Do you have docker-ce installed and running?
Are you in local 'docker' group? Have you logged out and back in after joining?
You might be able to add yourself to that group with 'sudo adduser docker'.""")

    @cached_property
    def _client(self):
        env = self.environment.environ
        kwargs = {}
        version = env.get('DOCKER_VERSION', None)
        if version:
            kwargs['version'] = version
        timeout = env.get('DOCKER_TIMEOUT', None)
        if timeout:
            kwargs['timeout'] = timeout
        return docker.from_env(environment=env, **kwargs)

    def _run_opts(self, task, step):
        env = self.environment

        opts = dict(
            image=step.img,
            command=step.cmd,
            environment=step.env,
            user='{}:{}'.format(env.uid, env.gid),
        )

        # mounts and workdir
        if step.mnt:
            opts['mounts'] = [Mount(step.mnt, task.path, type='bind', read_only=False)]
            opts['working_dir'] = step.mnt
        else:
            wpath = self.WORK_PATH
            opts['mounts'] = [
                Mount(wpath, None, type='tmpfs', read_only=False, tmpfs_size=self.WORK_SIZE),
                Mount(join(wpath, 'src'), task.path, type='bind', read_only=True),
                Mount(join(wpath, 'build'), join(task.path, '_build'), type='bind', read_only=False),
            ]
            opts['working_dir'] = wpath

        return opts

    def prepare(self, task, observer):
        client = self._client
        for i, step in enumerate(task.steps):
            name = step.name or i
            observer.start_step(name)
            image, tag = step.img.split(':', 1)
            try:
                img = client.images.get(step.img)
            except docker.errors.ImageNotFound:
                observer.manager_msg(name, "Downloading image {}".format(step.img))
                img = client.images.pull(image, tag)
            finally:
                observer.end_step(name)

    def build(self, task, observer):
        client = self._client
        for i, step in enumerate(task.steps):
            name = step.name or str(i)
            observer.start_step(name)
            opts = self._run_opts(task, step)
            observer.manager_msg(name, "Running container {}:".format(opts['image']))
            container = client.containers.create(**opts)

            try:
                container.start()

                for line in container.logs(stderr=True, stream=True):
                    observer.container_msg(name, line.decode('utf-8'))

                ret = container.wait(timeout=10)
                code = ret.get('StatusCode', None)
                error = ret.get('Error', None)

                if code or error:
                    return BuildResult(code, error, name)
            finally:
                container.remove()
                observer.end_step(name)
        return BuildResult()

    def verify(self):
        try:
            client = self._client
            client.ping()
        except Exception as e:
            return "{}: {}".format(e.__class__.__name__, e)

    def version_info(self):
        version = self._client.version()
        if not version:
            return

        out = []
        okeys = ['Version', 'ApiVersion', 'MinAPIVersion', 'GoVersion', 'BuildTime', 'GitCommit', 'Experimental', 'Os', 'Arch', 'KernelVersion']
        version['Name'] = 'Client'
        components = version.pop('Components', [])
        components.insert(0, version)

        for component in components:
            name = component.pop('Name', '-')
            if 'Details' in component:
                component.update(component.pop('Details'))
            out.append("Docker {}:".format(name))
            keys = okeys + [k for k in component.keys() if k not in okeys]
            for key in keys:
                if key in component:
                    val = component[key]
                    if isinstance(val, dict):
                        out.append("  {}:".format(key))
                        for k, v in val.items(): out.append("    {}: {}".format(k, v))
                    elif isinstance(val, list):
                        out.append("  {}:".format(key))
                        for v in val: out.append("   - {}".format(v))
                    else:
                        out.append("  {}: {}".format(key, val))

        return '\n'.join(out)
