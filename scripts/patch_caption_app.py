from pathlib import Path
import re

ROOT = Path('upstream')

def edit(rel, fn):
    p = ROOT / rel
    s = p.read_text()
    n = fn(s)
    if n == s:
        raise SystemExit(f'patch made no change: {rel}')
    p.write_text(n)
    print('patched', rel)

def must_replace(s, old, new, label):
    if old not in s:
        raise SystemExit(f'missing patch anchor: {label}')
    return s.replace(old, new)

def patch_android(s):
    s = must_replace(s, 'package = "app.concat.editor"', 'package = "app.autocaption.local"', 'android package')
    s = must_replace(s, 'apk_name = "Concat"', 'apk_name = "AutoCaptionLocal"', 'apk name')
    s = must_replace(s, 'label = "Concat"', 'label = "AutoCaption Local"', 'android label')
    return s
edit('src/crates/concat-android/Cargo.toml', patch_android)

def patch_transcriber(s):
    start = s.index('const KNOWN_MODELS: &[KnownModel] = &[')
    end = s.index('];', start) + 2
    block = '''const KNOWN_MODELS: &[KnownModel] = &[
    KnownModel {
        id: "base.en",
        label: "Base English",
        blurb: "Recommended. Good accuracy with a smaller download.",
        approx_bytes: 147_400_000,
        sha256: "",
        english_only: true,
    },
    KnownModel {
        id: "small.en",
        label: "Small English",
        blurb: "Higher accuracy. Larger download and slower on phones.",
        approx_bytes: 487_600_000,
        sha256: "",
        english_only: true,
    },
];'''
    return s[:start] + block + s[end:]
edit('src/crates/concat-speech/src/transcribe.rs', patch_transcriber)

def patch_app(s):
    s = must_replace(s, 'title: "Concat";', 'title: "AutoCaption Local";', 'window title')
    s = must_replace(s, 'min-width: 900px;', 'min-width: 360px;', 'min width')
    s = must_replace(s, 'min-height: 560px;', 'min-height: 480px;', 'min height')
    s = must_replace(s,
        '    callback captions-cancel();\n',
        '    callback captions-cancel();\n    callback captions-download-base();\n    callback captions-download-small();\n',
        'caption callback declarations')
    s = must_replace(s,
        '    callback speech-cancel();\n',
        '    callback speech-cancel();\n    callback speech-download-compact();\n    callback speech-download-full();\n',
        'speech callback declarations')
    s = must_replace(s,
        '        cancel => { root.captions-cancel(); }\n',
        '        cancel => { root.captions-cancel(); }\n        download-base => { root.captions-download-base(); }\n        download-small => { root.captions-download-small(); }\n',
        'caption dialog forwarding')
    s = must_replace(s,
        '        cancel => { root.speech-cancel(); }\n',
        '        cancel => { root.speech-cancel(); }\n        download-compact => { root.speech-download-compact(); }\n        download-full => { root.speech-download-full(); }\n',
        'speech dialog forwarding')
    return s
edit('src/crates/concat/ui/app.slint', patch_app)

def patch_captions(s):
    s = must_replace(s,
        '    callback cancel();\n',
        '    callback cancel();\n    callback download-base();\n    callback download-small();\n',
        'caption dialog callbacks')
    old = '''            if !root.data.ready: Text {
                text: I18n.t("Download a transcriber model in Settings › Transcriber first.");
                color: Theme.fg-muted;
                font-size: Theme.fs-sm;
                wrap: word-wrap;
            }'''
    new = '''            if !root.data.ready: VerticalLayout {
                spacing: 8px;
                Text {
                    text: "Choose an offline English caption model:";
                    color: Theme.fg-muted;
                    font-size: Theme.fs-sm;
                    wrap: word-wrap;
                }
                Button {
                    block: true;
                    primary: true;
                    label: "Download Base English · ~147 MB · Recommended";
                    clicked => { root.download-base(); }
                }
                Button {
                    block: true;
                    label: "Download Small English · ~488 MB · Higher accuracy";
                    clicked => { root.download-small(); }
                }
            }'''
    s = must_replace(s, old, new, 'caption model chooser')
    return s
edit('src/crates/concat/ui/dialogs/captions.slint', patch_captions)

def patch_speech(s):
    s = must_replace(s,
        '    callback cancel();\n',
        '    callback cancel();\n    callback download-compact();\n    callback download-full();\n',
        'speech dialog callbacks')
    old = '''            if !root.data.ready: Text {
                text: I18n.t("Download a voice model in Settings › Speech first.");
                color: Theme.fg-muted;
                font-size: Theme.fs-sm;
                wrap: word-wrap;
            }'''
    new = '''            if !root.data.ready: VerticalLayout {
                spacing: 8px;
                Text {
                    text: "Choose an offline Kokoro voice model:";
                    color: Theme.fg-muted;
                    font-size: Theme.fs-sm;
                    wrap: word-wrap;
                }
                Button {
                    block: true;
                    primary: true;
                    label: "Download Kokoro Compact · ~132 MB · Recommended";
                    clicked => { root.download-compact(); }
                }
                Button {
                    block: true;
                    label: "Download Kokoro Full · ~349 MB";
                    clicked => { root.download-full(); }
                }
            }'''
    s = must_replace(s, old, new, 'speech model chooser')
    return s
edit('src/crates/concat/ui/dialogs/speech.slint', patch_speech)

def patch_settings(s):
    s = s.replace('title: I18n.t("Settings");', 'title: "AI Models";')
    for label in ['General', 'Appearance', 'Remote', 'About']:
        pat = re.compile(r'\n\s*PageTab \{\n\s*label: I18n\.t\("' + re.escape(label) + r'"\);.*?\n\s*\}', re.S)
        s, n = pat.subn('', s, count=1)
        if n != 1:
            raise SystemExit(f'could not remove settings tab {label}')
    s = s.replace('label: I18n.t("Transcriber");', 'label: "Auto Captions";')
    s = s.replace('current: root.data.tab == 2;', 'current: root.data.tab != 3;', 1)
    s = s.replace('label: I18n.t("Speech");', 'label: "AI Speech";')
    s = s.replace('if root.data.tab == 2: VerticalLayout {', 'if root.data.tab != 3: VerticalLayout {')
    return s
edit('src/crates/concat/ui/dialogs/settings.slint', patch_settings)

def patch_tray(s):
    anchors = [
        'label: I18n.t("Add track");',
        'label: I18n.t("Razor (B)");',
        'label: I18n.t("Split at playhead (S, or ⌘B for every clip)");',
        'label: I18n.t("Delete selected");',
        'label: I18n.t("Pan tool");',
        'label: I18n.t("Snap to edges");',
    ]
    for a in anchors:
        s = must_replace(s, a, 'visible: false;\n            ' + a, 'tray '+a)
    s = must_replace(s, '            glyph: Glyph.merge;\n', '            visible: false;\n            glyph: Glyph.merge;\n', 'merge hidden')
    s = s.replace('label: I18n.t("Generate Captions");', 'label: "AUTO CAPTION";')
    s = s.replace('label: I18n.t("Text to Speech");', 'label: "AI SPEECH";')
    return s
edit('src/crates/concat/ui/timeline/tray.slint', patch_tray)

def patch_start(s):
    s = must_replace(s, 'text: I18n.t("New project");', 'text: "AutoCaption Local";', 'start title')
    s = must_replace(s,
        'text: I18n.t("These settings apply to the whole edit and cannot be changed later.");',
        'text: "Offline auto captions and AI speech. Create a project, then import one video.";',
        'start subtitle')
    s = must_replace(s,
        'text: root.data.busy ? I18n.t("Creating…") : I18n.t("Create");',
        'text: root.data.busy ? "Creating…" : "Start caption project";',
        'start button')
    return s
edit('src/crates/concat/ui/start.slint', patch_start)

def patch_studio(s):
    pat = re.compile(r'    /// Probes the files on a worker and adds what probed as media\.\n    pub fn import\(&mut self, paths: Vec<std::path::PathBuf>\) \{.*?\n    \}\n\n    /// Decodes art', re.S)
    m = pat.search(s)
    if not m:
        raise SystemExit('could not find Studio::import')
    new_fn = '''    /// Probes the files on a worker, imports them, and immediately places
    /// them at 0:00. Caption-first Android builds should not make the user
    /// visit a media bin before transcription can begin.
    pub fn import(&mut self, paths: Vec<std::path::PathBuf>) {
        if paths.is_empty() || self.session.is_none() {
            return;
        }
        spawn(
            move || {
                paths
                    .iter()
                    .map(|path| media::probe(&path.to_string_lossy()))
                    .collect::<Vec<_>>()
            },
            |studio, _, _, results| {
                let mut commands = Vec::new();
                let mut imported_paths = Vec::new();
                let mut failures = Vec::new();
                for result in results {
                    match result {
                        Ok(summary) => {
                            imported_paths.push(summary.path.clone());
                            commands.push(Command::AddMedia {
                                item: summary.to_new_media(),
                            });
                        }
                        Err(error) => failures.push(error),
                    }
                }
                let added = commands.len();
                if !commands.is_empty() {
                    studio.apply(Command::Batch { commands });
                    let mut selected = None;
                    for path in imported_paths {
                        let media_id = studio
                            .project()
                            .media
                            .iter()
                            .find(|item| item.path == path)
                            .map(|item| item.id.clone());
                        if let Some(media_id) = media_id {
                            if let Some(clip_id) = studio.apply(Command::AddClipAtFirstFree {
                                media_id,
                                start: 0.0,
                            }) {
                                selected = Some(clip_id);
                            }
                        }
                    }
                    if let Some(clip_id) = selected {
                        studio.selection = vec![clip_id];
                    }
                }
                if let Some(error) = failures.first() {
                    studio.notify(&crate::host::probe_error(error), true);
                } else if added > 0 {
                    studio.notify(
                        "Video ready — tap AUTO CAPTION or AI SPEECH",
                        false,
                    );
                }
            },
        );
    }

    /// Decodes art'''
    return s[:m.start()] + new_fn + s[m.end():]
edit('src/crates/concat/src/studio.rs', patch_studio)

def patch_lib(s):
    s = must_replace(s,
        '''    app.on_captions_cancel(on_window!(|state| {
        state.captions_cancel();
    }));
''',
        '''    app.on_captions_cancel(on_window!(|state| {
        state.captions_cancel();
    }));
    app.on_captions_download_base(on_window!(|state| {
        state.refresh_models();
        state.model_download("base.en");
    }));
    app.on_captions_download_small(on_window!(|state| {
        state.refresh_models();
        state.model_download("small.en");
    }));
''',
        'caption download handlers')
    s = must_replace(s,
        '''    app.on_speech_cancel(on_window!(|state| {
        state.speech_cancel();
    }));
''',
        '''    app.on_speech_cancel(on_window!(|state| {
        state.speech_cancel();
    }));
    app.on_speech_download_compact(on_window!(|state| {
        state.refresh_models();
        state.model_download("kokoro-int8-multi-lang-v1_0");
    }));
    app.on_speech_download_full(on_window!(|state| {
        state.refresh_models();
        state.model_download("kokoro-multi-lang-v1_0");
    }));
''',
        'speech download handlers')
    return s
edit('src/crates/concat/src/lib.rs', patch_lib)

print('AutoCaption Local patch complete')
