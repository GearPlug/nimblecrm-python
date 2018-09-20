import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(name='nimblecrm-python',
      version='0.1.0',
      description='API wrapper for NimblerCRM written in Python',
      long_description=read('README.md'),
      url='https://github.com/GearPlug/nimblecrm-python',
      author='Nerio Rincon',
      author_email='nrincon.mr@gmail.com',
      license='GPL',
      packages=['nimblercrm'],
      install_requires=[
          'requests',
      ],
      zip_safe=False)
