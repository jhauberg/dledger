# Executable distribution

`dledger` can be packaged down into a single-file executable using [PyInstaller](https://www.pyinstaller.org) ([GitHub](https://github.com/pyinstaller/)).

At time of writing and as of version 4.10 of `PyInstaller`, the following steps can be taken to produce a working executable.

Note that the executable will _only_ be compatible with the platform it was built on; i.e. if you're on macOS and run these steps, you'll end up with a macOS-only build; similarly, if you run them on Windows, you'll get a Windows-only build.

## 1) Install PyInstaller

```shell
$ pip3 install pyinstaller
```

## 2) Write a script to run the `dledger` module, for example:

**[run.py](run.py)**
```python
from dledger.__main__ import main

if __name__ == "__main__":
    main()
```

Place this script in the project root so that it is relative to the `dledger` directory (i.e. same place as we'll usually find `setup.py`).

## 3) Run PyInstaller

From project root, relative to the script you just wrote (assuming it's called `run.py`), run PyInstaller:

```shell
$ pyinstaller run.py --name dledger --onefile
```

We add `--name` argument to prevent it from defaulting to name the exectuable `run`, in this case.

## 4) Distribute executable

If everything went as expected, an executable has now been built at `dist/dledger`. In principle, this executable can now be distributed in a release.

There's likely to be issues with this, especially on macOS where notarization is basically required- but other than that, should be smooth sailing.

User will have to place this executable in `/usr/local/bin/` to install it, or run in place by `./dledger --help`.

# Disclaimer

I have only tried this on macOS; results may vary on other platforms.

Additionally, executable is probably going to be a bit fat and not as optimized as it could be, but that's the price we pay for convenience.
