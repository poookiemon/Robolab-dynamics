from setuptools import setup, find_packages

setup(

    name='contractiondb',
    version='0.1',
    description='Python interface for the ContractionDB',
    author='Niklas Mertsch',
    author_email='niklas.mertsch@stud.uni-goettingen.de',
    license='MIT',
    python_requires='>=3.6',
    packages=find_packages(),
    install_requires=[
        "mysql-connector-python",
        'numpy',
    ],
    zip_safe=False
)
