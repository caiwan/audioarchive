import abc

"""
TODO: 
- https://pypi.org/project/ShazamAPI/
- https://github.com/echonest/pyechonest
- https://pypi.org/project/python-acrcloud/
- https://audd.io/
"""


class AbstractAudioIdentifier(abc.ABC):
    pass


class ShazamWrapper(AbstractAudioIdentifier):
    pass


class EchonestWrapper(AbstractAudioIdentifier):
    pass


class AcrcloudWrapper(AbstractAudioIdentifier):
    pass


class AuddIoWrapper(AbstractAudioIdentifier):
    pass
