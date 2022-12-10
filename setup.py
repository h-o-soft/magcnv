from setuptools import setup, find_packages


setup(
	name="magcnv-package",
	version="0.1.0",
	install_requires=["Pillow"],
	packages=find_packages(),
	entry_points={
		"console_scripts": [
			"magcnv=src.app:main"
		]
	}
)
