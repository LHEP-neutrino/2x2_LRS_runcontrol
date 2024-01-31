from setuptools import setup, find_packages


setup(
    name="adc64",
    version="0.0.1",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "adc64 = adc64.cli:adc64",
        ]
    },
    description="CLI for remote control AFI ADC64 boards",
    author="Green Lab",
    classifiers=["Intended Audience :: Information Technology",
                 "Operating System :: POSIX :: Linux",
                 "Programming Language :: Python",
                 "Programming Language :: Python :: 3",
                 "Programming Language :: Python :: 3.6"]
)
