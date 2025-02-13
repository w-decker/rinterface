from setuptools import setup, find_packages

setup(
    name="rinterface",
    version="0.0.2",
    author="Will Decker",
    author_email="will.decker@gatech.edu",
    description="Quickly interface with R in Python",
    url="https://github.com/w-decker/rinterface",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering"
    ]

)