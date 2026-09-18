from pathlib import Path

ROOT = Path("upstream")

def edit(rel, fn):
    p = ROOT / rel
    s = p.read_text()
    n = fn(s)
    if n == s:
        raise SystemExit(f"v3 patch made no change: {rel}")
    p.write_text(n)
    print("v3 patched", rel)

def patch_settings(s):
    start = s.index("export component SettingsDialog inherits Modal")
    component = r'''export component SettingsDialog inherits Modal {
    in property <SettingsData> data;
    in property <[ModelData]> transcribers;
    in property <[ModelData]> voices;
    in property <[string]> languages;
    in property <[SystemFactData]> system-facts;
    in property <string> system-report;

    callback page-changed(index: int);
    callback show-log();
    callback language-changed(index: int);
    callback theme-changed(dark: bool);
    callback playhead-stops-changed(on: bool);
    callback custom-context-actions-changed(on: bool);
    callback download-source-changed(index: int);
    callback download-base-edited(text: string);
    callback server-enabled-changed(on: bool);
    callback server-listen-edited(text: string);
    callback server-token-edited(text: string);
    callback server-token-generated();
    callback model-activated(id: string);
    callback model-download(id: string);
    callback model-cancel(id: string);
    callback model-remove(id: string);

    open: root.data.open;
    title: "AI Models";
    glyph: Glyph.settings;

    // Phone-first: never exceed the actual window.
    surface-width: root.width - 16px;
    surface-height: root.height - 24px;

    VerticalLayout {
        padding-bottom: 8px;
        spacing: 0px;

        Rectangle {
            height: 52px;

            HorizontalLayout {
                padding-left: 12px;
                padding-right: 12px;
                padding-top: 8px;
                padding-bottom: 8px;

                SegmentedControl {
                    horizontal-stretch: 1;
                    options: ["Auto Captions", "AI Speech"];
                    current: root.data.tab == 3 ? 1 : 0;
                    changed(index) => {
                        root.page-changed(index == 0 ? 2 : 3);
                    }
                }
            }
        }

        Rectangle {
            height: 1px;
            background: Theme.line;
        }

        PaneScroll {
            vertical-stretch: 1;

            if root.data.tab != 3: VerticalLayout {
                DialogSection {
                    first: true;
                    title: "Auto Caption Models";

                    Text {
                        text: "Download once, then transcription works offline.";
                        color: Theme.fg-muted;
                        font-size: Theme.fs-sm;
                        wrap: word-wrap;
                    }

                    for model in root.transcribers: ModelRow {
                        model: model;
                        activated => { root.model-activated(model.id); }
                        download => { root.model-download(model.id); }
                        cancel => { root.model-cancel(model.id); }
                        remove => { root.model-remove(model.id); }
                    }

                    Text {
                        text: root.data.disk;
                        color: Theme.fg-muted;
                        font-family: Theme.font-technical;
                        font-size: Theme.fs-sm;
                        wrap: word-wrap;
                    }
                }
            }

            if root.data.tab == 3: VerticalLayout {
                DialogSection {
                    first: true;
                    title: "AI Speech Models";

                    Text {
                        text: "Kokoro runs locally after the model is downloaded.";
                        color: Theme.fg-muted;
                        font-size: Theme.fs-sm;
                        wrap: word-wrap;
                    }

                    for model in root.voices: ModelRow {
                        model: model;
                        activated => { root.model-activated(model.id); }
                        download => { root.model-download(model.id); }
                        cancel => { root.model-cancel(model.id); }
                        remove => { root.model-remove(model.id); }
                    }

                    Text {
                        text: root.data.disk;
                        color: Theme.fg-muted;
                        font-family: Theme.font-technical;
                        font-size: Theme.fs-sm;
                        wrap: word-wrap;
                    }
                }
            }
        }
    }
}
'''
    return s[:start] + component

edit("src/crates/concat/ui/dialogs/settings.slint", patch_settings)

def patch_captions(s):
    old = "    surface-width: 480px;"
    if old not in s:
        raise SystemExit("caption surface-width anchor missing")
    return s.replace(old, "    surface-width: root.width - 16px;", 1)
edit("src/crates/concat/ui/dialogs/captions.slint", patch_captions)

def patch_speech(s):
    old = "    surface-width: 520px;"
    if old not in s:
        raise SystemExit("speech surface-width anchor missing")
    return s.replace(old, "    surface-width: root.width - 16px;", 1)
edit("src/crates/concat/ui/dialogs/speech.slint", patch_speech)

print("AutoCaption Local v3 responsive phone sheets patch complete")
