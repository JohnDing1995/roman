import logging
from collections import namedtuple
from collections.abc import Mapping
from pathlib import PurePosixPath

from ..observer import BuildObserver

logger = logging.getLogger(__name__)

BACKENDS = {
    'docker': 'apluslms_roman.backends.docker.DockerBackend',
}


BuildTask = namedtuple('BuildTask', [
    'path',
    'steps',
])


def clean_image_name(image):
    if ':' not in image:
        image += ':latest'
    return image


class BuildStep:
    """
    img: docker image
    cmd: If not None, docker command
    mnt: If not None, course data is mounted to this path in RW mode
    env: If not None, dict that is given as environment for the image
    ref: Name/index of the step
    """
    __slots__ = ('img', 'cmd', 'mnt', 'env', 'name', 'ref')

    @classmethod
    def from_config(cls, index, data):
        if isinstance(data, Mapping):
            if 'img' not in data:
                raise RuntimeError(
                    "Missing image name (img) in step configuration: {}".format(data))
            return cls(
                index,
                data['img'],
                data.get('cmd'),
                data.get('mnt'),
                data.get('env'),
                data.get('name'),
            )
        return cls(index, clean_image_name(data))

    def __init__(self, ref, img, cmd=None, mnt=None, env=None, name=None):
        self.ref = ref
        self.img = clean_image_name(img)
        self.cmd = cmd if (cmd is None or isinstance(cmd, str)) else tuple(cmd)
        self.mnt = mnt
        self.env = dict(env) if env else {}
        self.name = name

    def __str__(self):
        return self.name or str(self.ref)


class BuildResult:
    __slots__ = ('code', 'error', 'step')

    def __init__(self, code=0, error=None, step=None):
        self.code = code
        self.error = error
        self.step = step
        assert self.ok or step is not None, "step is required for failed result"

    @property
    def ok(self):
        return self.code == 0 and self.error is None

    def __str__(self):
        if self.ok:
            return "Build ok"
        error = self.error or 'exit code {}'.format(self.code)
        return "Build failed on step {}: {}".format(self.step, error)


Environment = namedtuple('Environment', [
    'uid',
    'gid',
    'environ',
])


class Backend:
    WORK_SIZE = '100M'
    WORK_PATH = '/work'

    def __init__(self, environment: Environment):
        self.environment = environment

    def prepare(self, task: BuildTask, observer: BuildObserver):
        raise NotImplementedError

    def build(self, task: BuildTask, observer: BuildObserver):
        """
            Returns BuildResult
        """
        raise NotImplementedError

    def verify(self):
        """Verify that connections to backend is working
        Returns:
          On success: None
          On failure: exception or error string
        """
        raise NotImplementedError

    def version_info(self):
        pass

    def get_host_path(self, original):
        mapping = self.environment.environ.get('directory_map', {})
        if not mapping:
            return original
        logger.debug("Get mapping from environment:%s", mapping)
        path = PurePosixPath(original)
        for container, host in mapping.items():
            try:
                logger.debug("Mapping:%s:%s", container, host)
                return str(PurePosixPath(host, path.relative_to(container)))
            except ValueError:
                logger.error("Error when composing new path!")
                continue
        return ValueError("Unable to map path '%s' to any backend host path" % (path))
