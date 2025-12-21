import subprocess
import sys


def install_missing_metadata():
    """Install common packages that cause metadata errors"""
    packages = [
        'importlib-metadata',
        'zipp',
        'typing_extensions',
        'semver',
        'altair',
        'blinker',
        'cachetools',
        'click',
        'gitdb',
        'GitPython',
        'Jinja2',
        'jsonschema',
        'markdown-it-py',
        'mdurl',
        'numpy',
        'pandas',
        'Pillow',
        'protobuf',
        'pyarrow',
        'pydeck',
        'Pygments',
        'PyPDF2',
        'python-dateutil',
        'python-docx',
        'referencing',
        'rich',
        'rpds-py',
        'smmap',
        'tenacity',
        'toml',
        'toolz',
        'tornado',
        'watchdog'
    ]

    for package in packages:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ Installed: {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install: {package}")


if __name__ == "__main__":
    install_missing_metadata()
