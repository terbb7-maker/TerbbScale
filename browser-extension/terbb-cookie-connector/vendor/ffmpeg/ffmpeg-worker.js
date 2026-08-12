// ffmpeg core worker (classic script)
const FFMessageType = {
  LOAD: 'LOAD',
  EXEC: 'EXEC',
  WRITE_FILE: 'WRITE_FILE',
  READ_FILE: 'READ_FILE',
  DELETE_FILE: 'DELETE_FILE',
  ERROR: 'ERROR',
  PROGRESS: 'PROGRESS',
  LOG: 'LOG',
};
const ERROR_UNKNOWN_MESSAGE_TYPE = new Error('unknown message type');
const ERROR_NOT_LOADED = new Error('ffmpeg is not loaded, call `await ffmpeg.load()` first');

let ffmpeg;
const load = async ({ coreURL: _coreURL, wasmURL: _wasmURL, workerURL: _workerURL, }) => {
    const first = !ffmpeg;

    importScripts(_coreURL);
    const coreURL = _coreURL;
    const wasmURL = _wasmURL ? _wasmURL : _coreURL.replace(/.js$/g, ".wasm");
    const workerURL = _workerURL
        ? _workerURL
        : _coreURL.replace(/.js$/g, ".worker.js");
    ffmpeg = await createFFmpegCore({
        mainScriptUrlOrBlob: `${coreURL}#${btoa(JSON.stringify({ wasmURL, workerURL }))}`,
    });
    if (typeof ffmpeg.setLogger === 'function') {
        ffmpeg.setLogger((data) => self.postMessage({ type: FFMessageType.LOG, data }));
    }
    if (typeof ffmpeg.setProgress === 'function') {
        ffmpeg.setProgress((data) => self.postMessage({
            type: FFMessageType.PROGRESS,
            data,
        }));
    }
    return first;
};
const exec = async ({ args, timeout = -1 }) => {
    if (typeof ffmpeg.setTimeout === 'function') {
        ffmpeg.setTimeout(timeout);
    }
    // Debug: report input size if available (assumes first arg after -i)
    try {
        const inputIdx = args.indexOf('-i');
        const inputPath = inputIdx !== -1 ? args[inputIdx + 1] : null;
        if (inputPath && ffmpeg.FS?.stat) {
            const st = ffmpeg.FS.stat(inputPath);
            self.postMessage({
                type: FFMessageType.LOG,
                data: { type: 'stderr', message: `input size=${st.size}` },
            });
        }
    } catch (e) {
        // ignore
    }
    if (typeof ffmpeg.exec === 'function') {
        await Promise.resolve(ffmpeg.exec(...args));
    } else if (typeof ffmpeg.callMain === 'function') {
        ffmpeg.callMain(args);
    } else {
        throw new Error('ffmpeg.exec/callMain is not available');
    }
    const ret = typeof ffmpeg.ret === 'number'
        ? ffmpeg.ret
        : (typeof ffmpeg.exitCode === 'number' ? ffmpeg.exitCode : 0);
    return ret;
};
const writeFile = ({ path, data }) => {
    ffmpeg.FS.writeFile(path, data);
    return true;
};
const readFile = ({ path, encoding }) => ffmpeg.FS.readFile(path, { encoding });
const deleteFile = ({ path }) => {
    try {
        ffmpeg.FS.unlink(path);
    }
    catch (e) {
        // The file may already be absent after a failed render.
    }
    return true;
};

self.onmessage = async ({ data: { id, type, data: _data }, }) => {
    const trans = [];
    let data;
    let abortMsg = null;
    try {
        if (type !== FFMessageType.LOAD && !ffmpeg)
            throw ERROR_NOT_LOADED; // eslint-disable-line
        switch (type) {
            case FFMessageType.LOAD:
                data = await load(_data);
                break;
            case FFMessageType.EXEC:
                data = await exec(_data);
                break;
            case FFMessageType.WRITE_FILE:
                data = writeFile(_data);
                break;
            case FFMessageType.READ_FILE:
                data = readFile(_data);
                break;
            case FFMessageType.DELETE_FILE:
                data = deleteFile(_data);
                break;
            default:
                throw ERROR_UNKNOWN_MESSAGE_TYPE;
        }
    }
    catch (e) {
        abortMsg = e?.message || String(e);
        self.postMessage({
            id,
            type: FFMessageType.ERROR,
            data: e.toString(),
        });
        return;
    }
    if (data instanceof Uint8Array) {
        trans.push(data.buffer);
    }
    self.postMessage({ id, type, data }, trans);
};
