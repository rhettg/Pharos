from distutils.core import setup
import glob

setup(
    name="Pharos", 
    version="0.0.1", 
    scripts=['bin/pharosd'],
    packages=['pharos', 'pharos.views'],
    package_data={'pharos.views': ['*.mustache']},
    data_files=[
                ('docs/pharos/', ['docs/config_sample.py']),
                ('share/pharos/', glob.glob('static/*'))
               ]
    #py_modules=['pharos']
    # packages="pharos"
)
