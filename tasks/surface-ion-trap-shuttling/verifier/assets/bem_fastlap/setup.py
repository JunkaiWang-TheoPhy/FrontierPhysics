from pathlib import Path

import numpy
from Cython.Distutils import build_ext
from setuptools import Extension, setup


ROOT = Path(__file__).parent
FASTLAP = ROOT / "fastlap"

setup(
    name="iontrap-fastlap",
    version="1.0.0",
    description="FastLap boundary-element solver bindings for ion-trap electrostatics",
    license="GPL-3.0-or-later",
    py_modules=[],
    cmdclass={"build_ext": build_ext},
    ext_modules=[
        Extension(
            "iontrap_fastlap",
            sources=[
                str(ROOT / "fastlap.pyx"),
                str(ROOT / "fastlap_support.c"),
                str(FASTLAP / "fastlap.c"),
                str(FASTLAP / "calcp.c"),
                str(FASTLAP / "direct.c"),
                str(FASTLAP / "memtracker.c"),
                str(FASTLAP / "mulDisplay.c"),
                str(FASTLAP / "mulDo.c"),
                str(FASTLAP / "mulMats.c"),
                str(FASTLAP / "mulGlobal.c"),
                str(FASTLAP / "mulMulti.c"),
                str(FASTLAP / "mulLocal.c"),
                str(FASTLAP / "mulSetup.c"),
            ],
            include_dirs=[str(FASTLAP), numpy.get_include()],
        )
    ],
)
