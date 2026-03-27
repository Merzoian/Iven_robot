import asyncio
import time

import numpy as np
import pyaudio

from robot_logging import log_event

_ctx = None


def initialize(context):
    global _ctx
    _ctx = context


def _safe_device_info(p, index):
    try:
        return p.get_device_info_by_index(index)
    except Exception:
        return None


def open_audio_streams(p):
    """Open mic/speaker streams with channel/device fallbacks to avoid ALSA channel mismatch crashes."""
    mic_candidates = [_ctx.MIC_INDEX, None]
    mic = None
    last_err = None
    for idx in mic_candidates:
        for ch in (1,):
            try:
                kwargs = {
                    "format": pyaudio.paInt16,
                    "channels": ch,
                    "rate": _ctx.SAMPLE_RATE,
                    "input": True,
                    "frames_per_buffer": _ctx.CHUNK,
                }
                if idx is not None:
                    kwargs["input_device_index"] = idx
                mic = p.open(**kwargs)
                _ctx.MIC_CHANNELS = ch
                default_index = idx if idx is not None else p.get_default_input_device_info()["index"]
                mic_info = _safe_device_info(p, default_index)
                if mic_info:
                    print(f"Mic device: {mic_info.get('name', 'unknown')} channels={_ctx.MIC_CHANNELS}")
                    log_event(
                        _ctx.logger,
                        "info",
                        "audio_input_opened",
                        device=mic_info.get("name", "unknown"),
                        channels=_ctx.MIC_CHANNELS,
                    )
                break
            except Exception as e:
                last_err = e
        if mic:
            break
    if mic is None:
        raise RuntimeError(f"Unable to open microphone stream: {last_err}")

    spk_candidates = [_ctx.SPEAKER_INDEX, None]
    spk = None
    last_err = None
    for idx in spk_candidates:
        max_out = 2
        if idx is not None:
            info = _safe_device_info(p, idx)
            if info:
                max_out = int(max(1, info.get("maxOutputChannels", 2)))
        for ch in (1, 2):
            if ch > max_out:
                continue
            try:
                kwargs = {
                    "format": pyaudio.paInt16,
                    "channels": ch,
                    "rate": _ctx.SAMPLE_RATE,
                    "output": True,
                }
                if idx is not None:
                    kwargs["output_device_index"] = idx
                spk = p.open(**kwargs)
                _ctx.SPEAKER_CHANNELS = ch
                default_index = idx if idx is not None else p.get_default_output_device_info()["index"]
                spk_info = _safe_device_info(p, default_index)
                if spk_info:
                    print(f"Speaker device: {spk_info.get('name', 'unknown')} channels={_ctx.SPEAKER_CHANNELS}")
                    log_event(
                        _ctx.logger,
                        "info",
                        "audio_output_opened",
                        device=spk_info.get("name", "unknown"),
                        channels=_ctx.SPEAKER_CHANNELS,
                    )
                break
            except Exception as e:
                last_err = e
        if spk:
            break
    if spk is None:
        try:
            mic.close()
        except Exception:
            pass
        raise RuntimeError(f"Unable to open speaker stream: {last_err}")

    return mic, spk


async def playback_worker(spk):
    while not _ctx.shutdown_requested:
        raw_16k_bytes = await _ctx.audio_queue.get()
        _ctx.is_ivan_talking = True
        _ctx.last_tts_audio_ts = time.time()
        try:
            audio_array = np.frombuffer(raw_16k_bytes, dtype=np.int16)

            if _ctx.maestro and audio_array.size:
                rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                if rms < _ctx.JAW_RMS_THRESHOLD:
                    target = _ctx.JAW_CLOSED
                else:
                    target = _ctx.JAW_CLOSED + int(
                        min((rms - _ctx.JAW_RMS_THRESHOLD) / 11, _ctx.JAW_OPEN_MAX - _ctx.JAW_CLOSED)
                    )
                _ctx.maestro.set_target(_ctx.CH_JAW, target)

            audio_48k_mono = np.repeat(audio_array, 3).astype(np.int16)
            if _ctx.SPEAKER_CHANNELS == 2:
                audio_out = np.column_stack((audio_48k_mono, audio_48k_mono)).ravel().tobytes()
            else:
                audio_out = audio_48k_mono.tobytes()
            await asyncio.to_thread(spk.write, audio_out)

        except Exception as e:
            log_event(_ctx.logger, "warning", "playback_error", error=str(e))
            print(f"Playback error: {e}")
        finally:
            _ctx.audio_queue.task_done()
            if _ctx.audio_queue.empty():
                if _ctx.maestro:
                    _ctx.maestro.set_target(_ctx.CH_JAW, _ctx.JAW_CLOSED)
                _ctx.is_ivan_talking = False


async def send_mic(session, mic):
    while not _ctx.shutdown_requested:
        try:
            if _ctx.is_ivan_talking and (time.time() - _ctx.last_tts_audio_ts) > 1.2:
                _ctx.is_ivan_talking = False
                if _ctx.maestro:
                    _ctx.maestro.set_target(_ctx.CH_JAW, _ctx.JAW_CLOSED)
            if not _ctx.is_ivan_talking:
                raw_data = mic.read(_ctx.CHUNK, exception_on_overflow=False)
                audio_array = np.frombuffer(raw_data, dtype=np.int16)
                await session.send_realtime_input(
                    audio={"mime_type": "audio/pcm;rate=16000", "data": audio_array[::3].tobytes()}
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.005)


async def send_camera(session, camera_mgr):
    if not _ctx.CAMERA_AVAILABLE:
        return

    while not _ctx.shutdown_requested:
        try:
            if _ctx.is_ivan_talking or not _ctx.audio_queue.empty():
                await asyncio.sleep(0.12)
                continue
            if camera_mgr.latest_jpeg:
                await session.send_realtime_input(
                    video={"mime_type": "image/jpeg", "data": camera_mgr.latest_jpeg}
                )
                await asyncio.sleep(_ctx.MODEL_FRAME_INTERVAL_S)
            else:
                await asyncio.sleep(0.04)
        except asyncio.CancelledError:
            raise
        except Exception:
            await asyncio.sleep(0.2)
