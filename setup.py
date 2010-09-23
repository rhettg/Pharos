from distutils.core import setup

setup(
    name="Pharos", 
    version="0.0.1", 
    scripts=['bin/pharosd'],
    package_dir={'':'lib'},
    py_modules=['pharos']
    # packages="pharos"
)
