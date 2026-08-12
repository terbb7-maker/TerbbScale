const MESSAGE = {
  LOAD: "LOAD",
  EXEC: "EXEC",
  WRITE_FILE: "WRITE_FILE",
  READ_FILE: "READ_FILE",
  DELETE_FILE: "DELETE_FILE",
  ERROR: "ERROR",
};

let runnerPromise = null;

export async function compositeVideoOverlay(videoBlob, overlayBlob) {
  const runner = await getRunner();
  const token = crypto.randomUUID().replaceAll("-", "");
  const inputName = `${token}_input.mp4`;
  const overlayName = `${token}_overlay.png`;
  const outputName = `${token}_output.mp4`;
  try {
    await runner.write(inputName, new Uint8Array(await videoBlob.arrayBuffer()));
    await runner.write(overlayName, new Uint8Array(await overlayBlob.arrayBuffer()));
    const exitCode = await runner.exec([
      "-y",
      "-i", inputName,
      "-loop", "1",
      "-i", overlayName,
      "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto:shortest=1[vout]",
      "-map", "[vout]",
      "-map", "0:a?",
      "-c:v", "libx264",
      "-preset", "ultrafast",
      "-tune", "zerolatency",
      "-crf", "23",
      "-pix_fmt", "yuv420p",
      "-c:a", "aac",
      "-shortest",
      outputName,
    ]);
    const bytes = await runner.read(outputName);
    if (exitCode !== 0 || !bytes?.byteLength) {
      throw new Error(`A renderização do vídeo não foi concluída (${exitCode}).`);
    }
    return new Blob([bytes], { type: "video/mp4" });
  } finally {
    await Promise.allSettled([
      runner.remove(inputName),
      runner.remove(overlayName),
      runner.remove(outputName),
    ]);
  }
}

async function getRunner() {
  if (!runnerPromise) {
    runnerPromise = createRunner().catch((error) => {
      runnerPromise = null;
      throw error;
    });
  }
  return runnerPromise;
}

async function createRunner() {
  const worker = new Worker(chrome.runtime.getURL("vendor/ffmpeg/ffmpeg-worker.js"));
  let sequence = 0;
  const pending = new Map();
  worker.onmessage = ({ data }) => {
    if (!pending.has(data?.id)) return;
    const { resolve, reject } = pending.get(data.id);
    pending.delete(data.id);
    if (data.type === MESSAGE.ERROR) reject(new Error(String(data.data || "FFmpeg falhou.")));
    else resolve(data.data);
  };
  worker.onerror = (event) => {
    const error = new Error(event.message || "O processador de vídeo parou inesperadamente.");
    for (const { reject } of pending.values()) reject(error);
    pending.clear();
  };

  const call = (type, data, transfer = []) => new Promise((resolve, reject) => {
    const id = sequence++;
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, type, data }, transfer);
  });
  await call(MESSAGE.LOAD, {
    coreURL: chrome.runtime.getURL("vendor/ffmpeg/ffmpeg-core.js"),
    wasmURL: chrome.runtime.getURL("vendor/ffmpeg/ffmpeg-core.wasm"),
    workerURL: chrome.runtime.getURL("vendor/ffmpeg/ffmpeg-core.worker.js"),
  });
  return {
    exec: (args) => call(MESSAGE.EXEC, { args, timeout: 600_000 }),
    write: (path, data) => call(MESSAGE.WRITE_FILE, { path, data }, [data.buffer]),
    read: (path) => call(MESSAGE.READ_FILE, { path, encoding: "binary" }),
    remove: (path) => call(MESSAGE.DELETE_FILE, { path }),
  };
}
