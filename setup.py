from distutils.core import setup

setup(
    name="webnar", 
    version="0.0.1", 
    scripts=['bin/webnard'],
    package_dir={'':'lib'},
    py_modules=['webnar']
    # packages="webnar"
)
