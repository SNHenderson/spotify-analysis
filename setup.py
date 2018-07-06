from setuptools import setup

setup(
    name='spotify_analysis',
    packages=['spotify_analysis'],
    include_package_data=True,
    install_requires=[
        'flask',
        'requests',
        'pandas',
        'gunicorn',
        'matplotlib',
        'sklearn',
        'scipy',
    ],
)
