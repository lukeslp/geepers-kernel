import os

from setuptools import setup

install_requires = open("requirements.txt", "r").read().split("\n")

setup(
    name="monarchmoney",
    description="Monarch Money API for Python with CLI and LLM Integration",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/hammem/monarchmoney",
    author="hammem",
    author_email="hammem@users.noreply.github.com",
    license="MIT",
    keywords="monarch money, financial, money, personal finance, cli, ai, llm",
    install_requires=install_requires,
    packages=["monarchmoney", "cli", "cli.commands"],
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    entry_points={
        'console_scripts': [
            'mm=cli.main:cli',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Topic :: Office/Business :: Financial",
        "Environment :: Console",
    ],
)
