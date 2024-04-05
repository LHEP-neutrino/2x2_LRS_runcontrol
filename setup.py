from setuptools import setup, find_packages

setup(
    name="lrsctrl",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "lrsctrl = lrsctrl.cli:lrsctrl",
        ]
    },
    description="2x2 Light Readout DAQ Run Control",
    author="Livio Calivers; Greenlab",
    classifiers=["Intended Audience :: Information Technology",
                 "Operating System :: POSIX :: Linux",
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 3.6"]
)