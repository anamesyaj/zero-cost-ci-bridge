from pathlib import Path

p = Path("upstream/src/crates/concat-host/src/playback.rs")
s = p.read_text()

old = '''fn build_stream(
    device: &cpal::Device,
    rx: &Arc<Mutex<mpsc::Receiver<Msg>>>,
    shared: &Arc<Shared>,
    events: &Arc<dyn PlaybackEvents>,
    last_active: &Arc<Mutex<Vec<ActiveClip>>>,
) -> Result<BuiltStream, String> {
    use cpal::traits::DeviceTrait;

    let config = device
        .default_output_config()
        .map_err(|error| format!("no default output config: {error}"))?;
    let sample_format = config.sample_format();
    let config: cpal::StreamConfig = config.into();

    match sample_format {
        cpal::SampleFormat::F32 => {
            stream_for::<f32>(device, &config, rx, shared, events, last_active)
        }
        cpal::SampleFormat::I16 => {
            stream_for::<i16>(device, &config, rx, shared, events, last_active)
        }
        cpal::SampleFormat::U16 => {
            stream_for::<u16>(device, &config, rx, shared, events, last_active)
        }
        other => Err(format!("unsupported sample format {other:?}")),
    }
}'''

new = '''fn build_stream(
    device: &cpal::Device,
    rx: &Arc<Mutex<mpsc::Receiver<Msg>>>,
    shared: &Arc<Shared>,
    events: &Arc<dyn PlaybackEvents>,
    last_active: &Arc<Mutex<Vec<ActiveClip>>>,
) -> Result<BuiltStream, String> {
    use cpal::traits::DeviceTrait;

    // Android's AAudio backend can report a nominal "default" such as
    // 44.1 kHz float even on devices whose reliable media path is 48 kHz
    // PCM16.  Video editors care more about universal, stable playback than
    // about a float output stream, so try Android's native media-friendly
    // formats first and only then fall back to CPAL's chosen default.
    #[cfg(target_os = "android")]
    {
        let candidates = [
            (
                cpal::SampleFormat::I16,
                cpal::StreamConfig {
                    channels: 2,
                    sample_rate: cpal::SampleRate(48_000),
                    buffer_size: cpal::BufferSize::Default,
                },
            ),
            (
                cpal::SampleFormat::F32,
                cpal::StreamConfig {
                    channels: 2,
                    sample_rate: cpal::SampleRate(48_000),
                    buffer_size: cpal::BufferSize::Default,
                },
            ),
            (
                cpal::SampleFormat::I16,
                cpal::StreamConfig {
                    channels: 2,
                    sample_rate: cpal::SampleRate(44_100),
                    buffer_size: cpal::BufferSize::Default,
                },
            ),
        ];

        let mut errors = Vec::new();
        for (sample_format, config) in candidates {
            let result = match sample_format {
                cpal::SampleFormat::I16 => {
                    stream_for::<i16>(device, &config, rx, shared, events, last_active)
                }
                cpal::SampleFormat::F32 => {
                    stream_for::<f32>(device, &config, rx, shared, events, last_active)
                }
                _ => unreachable!(),
            };
            match result {
                Ok(stream) => {
                    log::info!(
                        "Android audio output: {:?}, {} ch @ {} Hz",
                        sample_format,
                        config.channels,
                        config.sample_rate.0
                    );
                    return Ok(stream);
                }
                Err(error) => errors.push(format!(
                    "{:?} {}ch@{}: {}",
                    sample_format, config.channels, config.sample_rate.0, error
                )),
            }
        }

        let default = device
            .default_output_config()
            .map_err(|error| format!("no default output config: {error}; tried {}", errors.join(" | ")))?;
        let sample_format = default.sample_format();
        let config: cpal::StreamConfig = default.into();
        log::warn!(
            "Android fixed audio formats failed ({}); trying CPAL default {:?} {}ch@{}",
            errors.join(" | "),
            sample_format,
            config.channels,
            config.sample_rate.0
        );
        return match sample_format {
            cpal::SampleFormat::F32 => {
                stream_for::<f32>(device, &config, rx, shared, events, last_active)
            }
            cpal::SampleFormat::I16 => {
                stream_for::<i16>(device, &config, rx, shared, events, last_active)
            }
            cpal::SampleFormat::U16 => {
                stream_for::<u16>(device, &config, rx, shared, events, last_active)
            }
            other => Err(format!("unsupported sample format {other:?}")),
        };
    }

    #[cfg(not(target_os = "android"))]
    {
        let config = device
            .default_output_config()
            .map_err(|error| format!("no default output config: {error}"))?;
        let sample_format = config.sample_format();
        let config: cpal::StreamConfig = config.into();

        match sample_format {
            cpal::SampleFormat::F32 => {
                stream_for::<f32>(device, &config, rx, shared, events, last_active)
            }
            cpal::SampleFormat::I16 => {
                stream_for::<i16>(device, &config, rx, shared, events, last_active)
            }
            cpal::SampleFormat::U16 => {
                stream_for::<u16>(device, &config, rx, shared, events, last_active)
            }
            other => Err(format!("unsupported sample format {other:?}")),
        }
    }
}'''

if old not in s:
    raise SystemExit("build_stream anchor missing")
s = s.replace(old, new, 1)
p.write_text(s)
print("Patched Android audio output to prefer 48 kHz stereo PCM16")
