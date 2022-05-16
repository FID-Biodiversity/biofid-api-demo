from setuptools import setup

requirements = [
    'bs4',
    'kaleido',
    'requests',
    'jupyter',
    'lxml',
    'numpy',
    'plotly',
    'pandas',
    'sparqlwrapper'
]

setup(
    name='BIOfid API Demo',
    version='1.0',
    description='Tools to use to demonstrate the BIOfid API',
    license="AGPLv3",
    long_description='',
    long_description_content_type="text/markdown",
    author='Adrian Pachzelt',
    author_email='a.pachzelt@ub.uni-frankfurt.de',
    url="https://www.biofid.de",
    download_url='https://github.com/FID-Biodiversity/biofid-api-demo',
    packages=['scripts'],
    package_data={'scripts': ['data/*.xml']},
    include_package_data=True,
    python_requires='>=3.7',
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest',
        ]
    }
)
