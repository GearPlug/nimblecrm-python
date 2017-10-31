from setuptools import setup

setup(name='nimblecrm',
      version='0.1',
      description='API wrapper for NimbleCRM written in Python',
      url='https://github.com/GearPlug/nimblecrm-python',
      author='Nerio Rincon',
      author_email='nrincon.mr@gmail.com',
      license='GPL',
      packages=['nimblecrm'],
      install_requires=[
          'requests',
      ],
      zip_safe=False)
