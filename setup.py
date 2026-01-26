"""Setup shim for editable installs."""
import setuptools

setuptools.setup(
    name="sys_monitor",
    version="0.1.0",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src"),
    install_requires=[
        "python-dotenv==0.15.0",
        "flask==1.1.2",
        "Jinja2==3.0.3",
        "itsdangerous==2.0.1",
        "werkzeug==2.0.3",
        "gevent==21.12.0",
        "psycopg2-binary==2.*",
        "bokeh==2.3.0",
        "numpy==1.*",
        "pandas==1.*",
    ],
    extras_require=dict(
        dev=[
            "black==20.8b1",
            "pytest==6.2.2",
            "tox==3.23.0",
        ],
    ),
)
