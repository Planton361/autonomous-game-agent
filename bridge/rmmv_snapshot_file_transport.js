(function () {
  "use strict";

  function nodeDependencies() {
    if (typeof require !== "function") {
      return null;
    }

    try {
      const fs = require("fs");
      const TextDecoder = require("util").TextDecoder;
      if (typeof TextDecoder !== "function") {
        return null;
      }
      return { fs: fs, TextDecoder: TextDecoder };
    } catch (_error) {
      return null;
    }
  }

  function readCompleteRequest(fs, TextDecoder, requestPath) {
    let bytes;
    try {
      bytes = fs.readFileSync(requestPath);
    } catch (_error) {
      return null;
    }

    if (bytes.length === 0 || bytes[bytes.length - 1] !== 0x0a) {
      return null;
    }

    try {
      return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    } catch (_error) {
      return null;
    }
  }

  function publishResponse(fs, responsePath, response) {
    try {
      if (fs.existsSync(responsePath)) {
        return false;
      }
    } catch (_error) {
      return false;
    }

    const temporaryPath = responsePath + ".tmp";
    let descriptor = null;
    let temporaryCreated = false;
    try {
      descriptor = fs.openSync(temporaryPath, "wx", 0o600);
      temporaryCreated = true;
      fs.writeSync(descriptor, JSON.stringify(response) + "\n", "utf8");
      fs.fsyncSync(descriptor);
      fs.closeSync(descriptor);
      descriptor = null;

      // A same-directory hard link is atomic and fails if another writer won first.
      fs.linkSync(temporaryPath, responsePath);
      fs.unlinkSync(temporaryPath);
      return true;
    } catch (_error) {
      if (descriptor !== null) {
        try {
          fs.closeSync(descriptor);
        } catch (_closeError) {
          // The original transport failure remains authoritative.
        }
      }
      if (temporaryCreated) {
        try {
          fs.unlinkSync(temporaryPath);
        } catch (_cleanupError) {
          // Fail closed without touching the request or response target.
        }
      }
      return false;
    }
  }

  function processSnapshotFiles(requestPath, responsePath, sceneRoot) {
    const dependencies = nodeDependencies();
    if (
      dependencies === null ||
      typeof window === "undefined" ||
      window.FHVisibleBridge === undefined ||
      window.FHVisibleBridge === null ||
      typeof window.FHVisibleBridge.buildSnapshotResponse !== "function"
    ) {
      return false;
    }

    const request = readCompleteRequest(
      dependencies.fs,
      dependencies.TextDecoder,
      requestPath,
    );
    if (request === null) {
      return false;
    }

    let response;
    try {
      response = window.FHVisibleBridge.buildSnapshotResponse(request, sceneRoot);
    } catch (_error) {
      return false;
    }

    return publishResponse(dependencies.fs, responsePath, response);
  }

  window.FHVisibleBridgeFileTransport = Object.freeze({
    processSnapshotFiles: processSnapshotFiles,
  });
})();
