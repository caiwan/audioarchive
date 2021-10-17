from setuptools import setup, find_namespace_packages

test_requirements = ["pytest"]

setup(
    name="cai-tapearchive",
    version="0.1",
    packages=find_namespace_packages(
        include=["taskgrinder.*"], exclude=["tests", "*.tests", "tests.*", "*.tests.*"]
    ),
    install_requires=[
        # TODO: Versions?
        "pyyaml",
        "dataclasses-json",
    ],
    test_requires=test_requirements,
    extras_require={"test": test_requirements},
    entry_points={
        "console_scripts": [
            "organize-tapes=tapearchive.organize:main"
            "import-tapes=tapearchive.import:main"
            "process-tapes=tapearchive.main:main"
        ]
    },
)
