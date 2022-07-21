from setuptools import setup, find_namespace_packages

requirements = [
    # TODO: Versions?
    "pyyaml",
    "tqdm",
    "dataclasses-json",
    "atomic",
    "redis",
    # "flask",
    # "flask-restful",
    # "librosa",
    "waiting",
    "mwclient",
    "numpy",
    "librosa",
]

test_requirements = [
    # TODO: Versions?
    "pytest",
    "pytest-docker",
]

setup(
    name="cai-tapearchive",
    version="0.1",
    packages=find_namespace_packages(include=["tapearchive.*", "tq.*"], exclude=["tests", "*.tests", "tests.*", "*.tests.*"]),
    install_requires=requirements,
    test_requires=test_requirements,
    extras_require={"test": test_requirements},
    entry_points={
        "console_scripts": [
            "organize-catalog=tapearchive.organize:main",
            "import-catalog=tapearchive.import:main",
            "audio-processor=tapearchive.main:main",
            "find-keys=tapearchive.find_keys:main",
        ]
    },
)
