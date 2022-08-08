from setuptools import setup, find_packages
# with open('requirements.txt') as fp:
#     install_requires = fp.read()
setup(
    name='pyRippleViewer',
    version='0.1',
    packages=find_packages(),
    license='Creative Commons Attribution-Noncommercial-Share Alike license',
    # install_requires=install_requires,
    long_description=open('README.md').read(),
)
