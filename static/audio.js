/* Shared speaker for Chat and Learn.
 *
 * iPhones only let audio start from a tap, which a reply arriving seconds later
 * isn't. One element unlocked on the first tap can then play anything, so every
 * sound in the app goes through it.
 */
(() => {
  "use strict";

  const player = new Audio();
  player.setAttribute("playsinline", "");
  let finishCurrent = null;
  let unlocked = false;

  function toBlobUrl(b64, mime) {
    const raw = atob(b64);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
    return URL.createObjectURL(new Blob([bytes], { type: mime }));
  }

  /** A twentieth of a second of silence, as a wav. */
  function silentWav() {
    const dataSize = 4410;
    const bytes = new Uint8Array(44 + dataSize);
    const view = new DataView(bytes.buffer);
    [[0, "RIFF"], [8, "WAVEfmt "], [36, "data"]].forEach(([at, text]) => {
      for (let i = 0; i < text.length; i += 1) bytes[at + i] = text.charCodeAt(i);
    });
    view.setUint32(4, 36 + dataSize, true);
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, 44100, true);
    view.setUint32(28, 88200, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    view.setUint32(40, dataSize, true);
    return URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
  }

  /** End whatever is playing; its play() promise resolves. */
  function stop() {
    player.pause();
    if (finishCurrent) finishCurrent();
  }

  /**
   * Play base64 audio, replacing anything already playing. Resolves when it ends, fails
   * or is replaced; `onBlocked` runs if the browser refuses to start it.
   */
  function play(b64, { mime = "audio/wav", onBlocked } = {}) {
    stop();
    return new Promise((resolve) => {
      const url = toBlobUrl(b64, mime);
      const finish = () => {
        if (finishCurrent !== finish) return;
        finishCurrent = null;
        player.removeEventListener("ended", finish);
        player.removeEventListener("error", finish);
        URL.revokeObjectURL(url);
        resolve();
      };
      finishCurrent = finish;
      player.addEventListener("ended", finish);
      player.addEventListener("error", finish);
      player.src = url;
      player.play().catch((err) => {
        if (onBlocked) onBlocked(err);
        finish();
      });
    });
  }

  function unlock() {
    if (unlocked || finishCurrent) return;
    unlocked = true;
    player.src = silentWav();
    // A sound that started meanwhile isn't ours to pause.
    player.play().then(() => { if (!finishCurrent) player.pause(); }).catch(() => { unlocked = false; });
  }

  // iPhones count the end of a touch as the tap, not the start.
  for (const name of ["pointerup", "touchend", "click", "keydown"]) {
    document.addEventListener(name, unlock, true);
  }

  window.KaiwaAudio = { play, stop };
})();
