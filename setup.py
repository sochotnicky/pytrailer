from distutils.core import setup

setup(name='pytrailer',
      version='0.6.1',
      description='Module to simplify access to movies on apple.com/trailers',
      author='Stanislav Ochotnicky',
      author_email='sochotnicky@gmail.com',
      url='http://github.com/sochotnicky/pytrailer',
      install_requires=["python-dateutil >= 1.5"],
      py_modules=['pytrailer'],
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
                   'Programming Language :: Python :: 2.6',
                   'Topic :: Software Development :: Libraries',
                   'Topic :: Multimedia :: Video'],
      keywords="movie trailer apple module",
      license="LGPL-3",
      platforms=["any"],
     )
