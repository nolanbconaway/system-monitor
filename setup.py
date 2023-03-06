"""Setup shim for editable installs."""
import setuptools

setuptools.setup(
    name="sys_monitor",
    version="0.1.0",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    install_requires=[
        "python-dotenv==0.*",
        "flask==1.*",
        "gevent==21.*",
        "psycopg2-binary==2.*",
        "bokeh==2.3.0",
        "markupsafe==2.0.1"
    ],
    extras_require=dict(
        dev=[
            "black==20.8b1",
            "pytest==6.2.2",
            "tox==3.23.0",
            "pytest-cov==2.11.1",
            "codecov==2.1.11",
        ],
    ),
)
