(function () {
  "use strict";

  const REQUEST_SUFFIX = ".request.json";
  const RESPONSE_SUFFIX = ".response.json";
  const REQUEST_FILENAME = /^[A-Za-z0-9][A-Za-z0-9_-]*\.request\.json$/;

  function nodeDependencies() {
    if (typeof require !== "function") {
      return null;
    }

    try {
      return {
        fs: require("fs"),
        path: require("path"),
      };
    } catch (_error) {
      return null;
    }
  }

  function isPositiveFiniteInteger(value) {
    return typeof value === "number" && Number.isFinite(value) && value > 0 && Math.floor(value) === value;
  }

  function start(options) {
    if (
      options === null ||
      typeof options !== "object" ||
      !isPositiveFiniteInteger(options.maxRequests)
    ) {
      return null;
    }

    const dependencies = nodeDependencies();
    if (dependencies === null) {
      return null;
    }

    try {
      if (!dependencies.fs.statSync(options.exchangeDirectory).isDirectory()) {
        return null;
      }
    } catch (_error) {
      return null;
    }

    let watcher = null;
    let closed = false;
    let attempts = 0;
    const attemptedFilenames = Object.create(null);

    function close() {
      if (closed) {
        return;
      }
      closed = true;
      if (watcher !== null) {
        watcher.close();
      }
    }

    function processRequestEvent(_eventType, filename) {
      if (
        closed ||
        typeof filename !== "string" ||
        !REQUEST_FILENAME.test(filename) ||
        attemptedFilenames[filename] === true
      ) {
        return;
      }

      attemptedFilenames[filename] = true;
      attempts += 1;
      try {
        if (
          typeof window === "undefined" ||
          window.SceneManager === undefined ||
          window.SceneManager === null ||
          window.SceneManager._scene === undefined ||
          window.SceneManager._scene === null ||
          window.FHVisibleBridgeFileTransport === undefined ||
          window.FHVisibleBridgeFileTransport === null ||
          typeof window.FHVisibleBridgeFileTransport.processSnapshotFiles !== "function"
        ) {
          return;
        }

        const token = filename.slice(0, -REQUEST_SUFFIX.length);
        const requestPath = dependencies.path.join(options.exchangeDirectory, filename);
        const responsePath = dependencies.path.join(
          options.exchangeDirectory,
          token + RESPONSE_SUFFIX,
        );
        window.FHVisibleBridgeFileTransport.processSnapshotFiles(
          requestPath,
          responsePath,
          window.SceneManager._scene,
        );
      } finally {
        if (attempts >= options.maxRequests) {
          close();
        }
      }
    }

    try {
      watcher = dependencies.fs.watch(options.exchangeDirectory, processRequestEvent);
    } catch (_error) {
      return null;
    }

    return Object.freeze({ close: close });
  }

  window.FHVisibleBridgeSnapshotWatcher = Object.freeze({ start: start });
})();
