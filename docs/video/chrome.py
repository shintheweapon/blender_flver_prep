"""
Headless Chrome, driven over the DevTools protocol: load a page built by
``scenes.page``, move it to a time and capture a PNG.

Needs the ``websocket-client`` package. Set ``CHROME`` to the browser's path
when it is not in the default place.
"""

import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request

import websocket

def default_chrome():
    """Where Chrome installs on Windows, under the system's ``ProgramFiles`` folder."""
    return os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe")


def chrome_path():
    """The Chrome executable: ``CHROME`` if set, else the default install, else one on PATH."""
    path = os.environ.get("CHROME") or default_chrome()
    if os.path.isfile(path):
        return path
    return shutil.which("chrome") or shutil.which("google-chrome") or path


class Chrome:
    """
    One headless Chrome page of a fixed size.

    Parameters
    ----------
    width, height : int
        The page size in pixels.

    Raises
    ------
    RuntimeError
        When Chrome does not open its debugging port.
    """

    def __init__(self, width, height):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.profile = tempfile.mkdtemp(prefix="video_chrome_")
        self.process = subprocess.Popen(
            [chrome_path(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             f"--remote-debugging-port={port}", f"--user-data-dir={self.profile}",
             f"--window-size={width},{height}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tabs = None
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
                break
            except OSError:
                time.sleep(0.1)
        if tabs is None:
            self.close()
            raise RuntimeError("Chrome did not open its debugging port")
        url = next(tab for tab in tabs if tab["type"] == "page")["webSocketDebuggerUrl"]
        self.socket = websocket.create_connection(url, timeout=120)
        self.next_id = 0
        self.call("Page.enable")
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1,
                  mobile=False)
        # the pages are dark, so the figures must use their dark colours, whatever the system's setting
        self.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])

    def call(self, method, **params):
        """
        Send one DevTools command and return its result.

        Raises
        ------
        RuntimeError
            When the command fails.
        """
        self.next_id += 1
        self.socket.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            message = json.loads(self.socket.recv())
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def evaluate(self, expression):
        """
        Run JavaScript in the page and wait for its promise.

        Raises
        ------
        RuntimeError
            When the script throws.
        """
        result = self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in result:
            raise RuntimeError(f"page script failed: {result['exceptionDetails'].get('text')}")
        return result.get("result", {}).get("value")

    def load(self, path):
        """
        Open an HTML file and wait until it is laid out (``window.ready``).

        Parameters
        ----------
        path : str
        """
        self.call("Page.navigate", url="file:///" + os.path.abspath(path).replace("\\", "/"))
        for _ in range(300):
            if self.evaluate("typeof window.ready") == "object":
                break
            time.sleep(0.05)
        self.evaluate("window.ready.then(() => true)")

    def capture(self, t=0.0):
        """
        The page at ``t`` seconds as PNG bytes.

        Parameters
        ----------
        t : float

        Returns
        -------
        bytes
        """
        self.evaluate(f"window.setTime({t:.4f})")
        return base64.b64decode(self.call("Page.captureScreenshot", format="png")["data"])

    def close(self):
        """Close the page and the browser, and remove its profile."""
        try:
            self.socket.close()
        except (AttributeError, OSError):
            pass
        self.process.kill()
        self.process.wait()
        shutil.rmtree(self.profile, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
