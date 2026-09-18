from pathlib import Path

ROOT = Path("upstream")

def edit(rel, fn):
    p = ROOT / rel
    s = p.read_text()
    n = fn(s)
    if n == s:
        raise SystemExit(f"native-audio patch made no change: {rel}")
    p.write_text(n)
    print("patched", rel)

def patch_cargo(s):
    anchor = '''memmap2 = "0.9"

[lints]'''
    repl = '''memmap2 = "0.9"

[target.'cfg(target_os = "android")'.dependencies]
# Native Android AudioTrack fallback. CPAL/AAudio is silent on some devices
# even though decoding/mixing succeeds, so phone builds write PCM to the
# platform media sink directly.
jni = "0.21"
ndk-context = "0.1"

[lints]'''
    if anchor not in s:
        raise SystemExit("concat-host Cargo anchor missing")
    return s.replace(anchor, repl, 1)

edit("src/crates/concat-host/Cargo.toml", patch_cargo)

def patch_playback(s):
    marker = '''/// Owns the output stream for the life of the app, rebuilding it whenever
/// it dies or the default device changes.
'''
    if marker not in s:
        raise SystemExit("supervisor marker missing")

    android_impl = r'''
#[cfg(target_os = "android")]
struct AndroidAudioTrack {
    track: jni::objects::GlobalRef,
}

#[cfg(target_os = "android")]
impl AndroidAudioTrack {
    const RATE: i32 = 48_000;
    const CHANNEL_OUT_STEREO: i32 = 12;
    const ENCODING_PCM_16BIT: i32 = 2;
    const STREAM_MUSIC: i32 = 3;
    const MODE_STREAM: i32 = 1;

    fn with_env<R>(
        f: impl FnOnce(&mut jni::JNIEnv<'_>) -> Result<R, String>,
    ) -> Result<R, String> {
        let ctx = ndk_context::android_context();
        // SAFETY: android-activity initializes ndk-context before android_main.
        let vm = unsafe { jni::JavaVM::from_raw(ctx.vm().cast()) }
            .map_err(|error| format!("AudioTrack JavaVM: {error}"))?;
        let mut env = vm
            .attach_current_thread()
            .map_err(|error| format!("AudioTrack attach thread: {error}"))?;
        f(&mut env)
    }

    fn new() -> Result<Self, String> {
        use jni::objects::JValue;

        Self::with_env(|env| {
            let min = env
                .call_static_method(
                    "android/media/AudioTrack",
                    "getMinBufferSize",
                    "(III)I",
                    &[
                        JValue::Int(Self::RATE),
                        JValue::Int(Self::CHANNEL_OUT_STEREO),
                        JValue::Int(Self::ENCODING_PCM_16BIT),
                    ],
                )
                .map_err(|error| format!("AudioTrack.getMinBufferSize: {error}"))?
                .i()
                .map_err(|error| format!("AudioTrack buffer result: {error}"))?;
            if min <= 0 {
                return Err(format!("AudioTrack invalid minimum buffer size {min}"));
            }

            // At least 100 ms of stereo PCM16. The blocking writer paces
            // playback, while this cushion avoids OEM underruns.
            let buffer_size = min.max((Self::RATE * 2 * 2) / 10);
            let local = env
                .new_object(
                    "android/media/AudioTrack",
                    "(IIIIII)V",
                    &[
                        JValue::Int(Self::STREAM_MUSIC),
                        JValue::Int(Self::RATE),
                        JValue::Int(Self::CHANNEL_OUT_STEREO),
                        JValue::Int(Self::ENCODING_PCM_16BIT),
                        JValue::Int(buffer_size),
                        JValue::Int(Self::MODE_STREAM),
                    ],
                )
                .map_err(|error| format!("AudioTrack constructor: {error}"))?;

            let state = env
                .call_method(&local, "getState", "()I", &[])
                .map_err(|error| format!("AudioTrack.getState: {error}"))?
                .i()
                .map_err(|error| format!("AudioTrack state result: {error}"))?;
            // AudioTrack.STATE_INITIALIZED == 1.
            if state != 1 {
                return Err(format!("AudioTrack did not initialize (state {state})"));
            }

            let track = env
                .new_global_ref(local)
                .map_err(|error| format!("AudioTrack global ref: {error}"))?;
            env.call_method(track.as_obj(), "setVolume", "(F)I", &[JValue::Float(1.0)])
                .map_err(|error| format!("AudioTrack.setVolume: {error}"))?;
            env.call_method(track.as_obj(), "play", "()V", &[])
                .map_err(|error| format!("AudioTrack.play: {error}"))?;

            log::info!(
                "Android native AudioTrack ready: stereo PCM16 @ 48000 Hz, buffer {} bytes",
                buffer_size
            );
            Ok(Self { track })
        })
    }

    fn write(&self, samples: &[i16]) -> Result<usize, String> {
        use jni::objects::{JObject, JValue};

        Self::with_env(|env| {
            env.push_local_frame(8)
                .map_err(|error| format!("AudioTrack local frame: {error}"))?;
            let result = (|| {
                let array = env
                    .new_short_array(samples.len() as i32)
                    .map_err(|error| format!("AudioTrack short array: {error}"))?;
                env.set_short_array_region(&array, 0, samples)
                    .map_err(|error| format!("AudioTrack copy samples: {error}"))?;
                let array_obj = JObject::from(array);
                let written = env
                    .call_method(
                        self.track.as_obj(),
                        "write",
                        "([SII)I",
                        &[
                            JValue::Object(&array_obj),
                            JValue::Int(0),
                            JValue::Int(samples.len() as i32),
                        ],
                    )
                    .map_err(|error| format!("AudioTrack.write: {error}"))?
                    .i()
                    .map_err(|error| format!("AudioTrack write result: {error}"))?;
                if written < 0 {
                    return Err(format!("AudioTrack.write returned {written}"));
                }
                Ok(written as usize)
            })();
            // SAFETY: the result object is unused; this only frees locals
            // created by this write on the long-lived audio thread.
            unsafe {
                let _ = env.pop_local_frame(&JObject::null());
            }
            result
        })
    }

    fn flush(&self) {
        use jni::objects::JValue;
        let _ = Self::with_env(|env| {
            let _ = env.call_method(self.track.as_obj(), "pause", "()V", &[]);
            let _ = env.call_method(self.track.as_obj(), "flush", "()V", &[]);
            let _ = env.call_method(self.track.as_obj(), "play", "()V", &[]);
            let _ = env.call_method(
                self.track.as_obj(),
                "setVolume",
                "(F)I",
                &[JValue::Float(1.0)],
            );
            Ok(())
        });
    }

    fn release(&self) {
        let _ = Self::with_env(|env| {
            let _ = env.call_method(self.track.as_obj(), "stop", "()V", &[]);
            let _ = env.call_method(self.track.as_obj(), "release", "()V", &[]);
            Ok(())
        });
    }
}

#[cfg(target_os = "android")]
fn supervise_stream(
    rx: mpsc::Receiver<Msg>,
    shared: Arc<Shared>,
    events: Arc<dyn PlaybackEvents>,
    last_active: Arc<Mutex<Vec<ActiveClip>>>,
) {
    // 20 ms at 48 kHz. Small enough for responsive seeking, large enough to
    // avoid JNI overhead becoming significant.
    const FRAMES: usize = 960;
    const CHANNELS: usize = 2;
    let mut clips: Vec<ActiveClip> = locked(&last_active).clone();
    let mut playing = shared.playing.load(Ordering::Relaxed);
    let mut position =
        shared.position_micros.load(Ordering::Relaxed) as f64 / 1_000_000.0;
    let step = 1.0 / f64::from(PCM_RATE);

    let mut track: Option<AndroidAudioTrack> = None;
    let mut reported = false;

    loop {
        while let Ok(message) = rx.try_recv() {
            match message {
                Msg::SetClips(next) => {
                    clips = next.clone();
                    *locked(&last_active) = next;
                }
                Msg::Play(at) => {
                    position = at;
                    playing = true;
                    if let Some(out) = track.as_ref() {
                        out.flush();
                    }
                }
                Msg::Pause => playing = false,
                Msg::Seek(at) => {
                    position = at;
                    if let Some(out) = track.as_ref() {
                        out.flush();
                    }
                }
            }
        }

        if track.is_none() {
            match AndroidAudioTrack::new() {
                Ok(out) => {
                    track = Some(out);
                    reported = false;
                }
                Err(error) => {
                    if !reported {
                        report(
                            events.as_ref(),
                            format!("native Android audio unavailable: {error}; retrying"),
                        );
                        reported = true;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(500));
                    continue;
                }
            }
        }

        if !playing {
            shared
                .position_micros
                .store((position * 1_000_000.0) as u64, Ordering::Relaxed);
            std::thread::sleep(std::time::Duration::from_millis(10));
            continue;
        }

        let mut pcm = vec![0i16; FRAMES * CHANNELS];
        for frame in pcm.chunks_exact_mut(CHANNELS) {
            let mut left = 0.0f32;
            let mut right = 0.0f32;
            for clip in &clips {
                let local = position - clip.start;
                if local < 0.0 || local >= clip.duration {
                    continue;
                }
                let gain = gain_at(clip, local);
                if gain <= 0.0 {
                    continue;
                }
                let read = local * f64::from(PCM_RATE);
                let index = read.floor() as u64;
                let fraction = (read - read.floor()) as f32;
                let source = &clip.pcm;
                left += gain
                    * (source.sample(index, 0) * (1.0 - fraction)
                        + source.sample(index + 1, 0) * fraction);
                right += gain
                    * (source.sample(index, 1) * (1.0 - fraction)
                        + source.sample(index + 1, 1) * fraction);
            }

            frame[0] = (left.clamp(-1.0, 1.0) * i16::MAX as f32).round() as i16;
            frame[1] = (right.clamp(-1.0, 1.0) * i16::MAX as f32).round() as i16;
            position += step;
        }

        let written = match track.as_ref().expect("created above").write(&pcm) {
            Ok(written) => written,
            Err(error) => {
                report(events.as_ref(), format!("native Android audio write failed: {error}"));
                if let Some(out) = track.take() {
                    out.release();
                }
                std::thread::sleep(std::time::Duration::from_millis(100));
                continue;
            }
        };

        // A short write is rare but legal. Roll back the part we advanced
        // but Android did not consume, so video/audio clocks stay aligned.
        let frames_written = written / CHANNELS;
        if frames_written < FRAMES {
            position -= (FRAMES - frames_written) as f64 * step;
        }
        shared
            .position_micros
            .store((position * 1_000_000.0) as u64, Ordering::Relaxed);
    }
}

'''

    s = s.replace(marker, android_impl + marker, 1)

    # The existing CPAL supervisor is desktop-only now. Android uses the
    # native AudioTrack supervisor above.
    old = '''fn supervise_stream(
    rx: mpsc::Receiver<Msg>,'''
    # There are now two occurrences; target the second (existing one), by
    # locating it after the original documentation marker.
    first = s.index("fn supervise_stream(")
    second = s.index("fn supervise_stream(", first + 1)
    s = s[:second] + '#[cfg(not(target_os = "android"))]\n' + s[second:]

    return s

edit("src/crates/concat-host/src/playback.rs", patch_playback)

print("AutoCaption Local native Android AudioTrack patch complete")
