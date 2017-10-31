from setuptools import setup

setup(name='nimblercrm',
      version='0.1',
      description='API wrapper for NimblerCRM written in Python',
      url='https://github.com/GearPlug/nimblecrm-python',
      author='Nerio Rincon',
      author_email='nrincon.mr@gmail.com',
      license='GPL',
      packages=['nimblercrm'],
      install_requires=[
          'requests',
      ],
      zip_safe=False)
