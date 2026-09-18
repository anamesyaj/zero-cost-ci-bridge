from pathlib import Path
import re

ROOT = Path("upstream")

def edit(rel, fn):
    p = ROOT / rel
    s = p.read_text()
    n = fn(s)
    if n == s:
        raise SystemExit(f"v2 UI patch made no change: {rel}")
    p.write_text(n)
    print("v2 patched", rel)

def must_replace(s, old, new, label):
    if old not in s:
        raise SystemExit(f"missing v2 patch anchor: {label}")
    return s.replace(old, new, 1)

# ---------------------------------------------------------------------------
# CapCut-style mobile home: one primary New Project action + recent projects.
# No desktop name/location/resolution/frame-rate form.
# ---------------------------------------------------------------------------
def patch_start(s):
    start = s.index("export component StartScreen")
    component = r'''export component StartScreen inherits Rectangle {
    in property <StartData> data;
    in property <[string]> resolutions;
    in property <[string]> rates;
    in property <[RecentProjectData]> recents;

    callback name-edited(name: string);
    callback location-edited(path: string);
    callback browse();
    callback resolution-changed(index: int);
    callback rate-changed(index: int);
    callback create();
    callback open-recent(path: string);
    callback forget-recent(path: string);
    callback dismiss-error();

    background: Theme.page;
    clip: true;

    VerticalLayout {
        padding-left: 20px;
        padding-right: 20px;
        padding-top: 24px;
        padding-bottom: 24px;
        spacing: 16px;
        alignment: start;

        Text {
            text: "Create";
            color: Theme.fg;
            font-size: 30px;
            font-weight: Theme.weight-display;
        }

        Text {
            text: "Offline captions and AI voice, made for quick mobile edits.";
            color: Theme.fg-muted;
            font-size: Theme.fs-lg;
            wrap: word-wrap;
        }

        Rectangle { height: 6px; }

        new-project := Rectangle {
            height: 88px;
            border-radius: 16px;
            background: new-touch.pressed ? Theme.accent-hover : Theme.accent;

            HorizontalLayout {
                padding-left: 18px;
                padding-right: 18px;
                spacing: 14px;

                VerticalLayout {
                    alignment: center;
                    Icon {
                        glyph: Glyph.plus;
                        size: 25px;
                        tint: Theme.on-accent;
                    }
                }

                VerticalLayout {
                    alignment: center;
                    spacing: 3px;

                    Text {
                        text: root.data.busy ? "Opening…" : "New project";
                        color: Theme.on-accent;
                        font-size: 19px;
                        font-weight: Theme.weight-title;
                    }

                    Text {
                        text: "Choose a video from your phone";
                        color: Theme.on-accent.with-alpha(0.78);
                        font-size: Theme.fs;
                    }
                }

                Rectangle { horizontal-stretch: 1; }
            }

            new-touch := TouchArea {
                enabled: !root.data.busy;
                clicked => { root.create(); }
            }
        }

        if root.data.error != "": Rectangle {
            height: error-text.preferred-height + 22px;
            border-radius: 10px;
            background: Theme.danger-soft;

            error-text := Text {
                x: 11px;
                y: 11px;
                width: parent.width - 22px;
                text: root.data.error;
                color: Theme.danger;
                font-size: Theme.fs;
                wrap: word-wrap;
            }

            TouchArea {
                clicked => { root.dismiss-error(); }
            }
        }

        Rectangle { height: 8px; }

        Text {
            text: "Recent projects";
            color: Theme.fg;
            font-size: 18px;
            font-weight: Theme.weight-title;
        }

        if root.recents.length == 0: Rectangle {
            height: 84px;
            border-radius: 12px;
            background: Theme.well;

            Text {
                x: 14px;
                y: 0;
                width: parent.width - 28px;
                height: parent.height;
                text: "Your recent caption projects will appear here.";
                color: Theme.fg-dim;
                font-size: Theme.fs;
                vertical-alignment: center;
                wrap: word-wrap;
            }
        }

        for project[index] in root.recents: Rectangle {\n            visible: index < 4;
            height: 68px;
            border-radius: 12px;
            background: recent-touch.pressed ? Theme.field-active
                : recent-touch.has-hover ? Theme.field-hover : Theme.field;

            HorizontalLayout {
                padding-left: 14px;
                padding-right: 14px;
                spacing: 10px;

                VerticalLayout {
                    alignment: center;
                    Icon {
                        glyph: Glyph.film;
                        size: 20px;
                        tint: Theme.accent;
                    }
                }

                VerticalLayout {
                    horizontal-stretch: 1;
                    alignment: center;
                    spacing: 2px;

                    Text {
                        text: project.name;
                        color: Theme.fg;
                        font-size: Theme.fs-lg;
                        font-weight: Theme.weight-title;
                        overflow: elide;
                    }

                    Text {
                        text: project.detail;
                        color: Theme.fg-dim;
                        font-size: Theme.fs-sm;
                        overflow: elide;
                    }
                }

                VerticalLayout {
                    alignment: center;
                    Text {
                        text: project.when;
                        color: Theme.fg-dim;
                        font-size: Theme.fs-sm;
                    }
                }
            }

            recent-touch := TouchArea {
                clicked => { root.open-recent(project.path); }
            }
        }

        Rectangle { vertical-stretch: 1; }

        Text {
            text: "AUTO CAPTIONS  •  AI SPEECH  •  OFFLINE";
            color: Theme.fg-dim;
            font-size: Theme.fs-sm;
            horizontal-alignment: center;
        }
    }
}
'''
    return s[:start] + component
edit("src/crates/concat/ui/start.slint", patch_start)

# ---------------------------------------------------------------------------
# Mobile top bar: app/project name, Models, Export. No File/Edit/View, panels,
# desktop window controls, or unrelated menus.
# ---------------------------------------------------------------------------
def patch_titlebar(s):
    start = s.index("export component TitleBar")
    component = r'''export component TitleBar inherits Rectangle {
    in property <string> project-name;
    in property <string> status;
    in property <bool> macos: true;
    in property <bool> minimal;
    in property <bool> own-buttons;
    in property <bool> maximized;
    in property <int> menu: -1;

    callback begin-drag();
    callback toggle-maximize();
    callback minimize();
    callback close();
    callback menu-opened(index: int, at-x: length);
    callback open-settings();
    callback add-pane(kind: PaneKind);
    callback export-clicked();

    height: 48px;
    background: Theme.panel;

    Rectangle {
        y: parent.height - 1px;
        width: parent.width;
        height: 1px;
        background: Theme.line;
    }

    HorizontalLayout {
        padding-left: 14px;
        padding-right: 12px;
        spacing: 10px;

        VerticalLayout {
            alignment: center;
            Text {
                text: root.minimal ? "AutoCaption" : root.project-name;
                color: Theme.fg;
                font-size: Theme.fs-lg;
                font-weight: Theme.weight-title;
                overflow: elide;
            }
        }

        Rectangle { horizontal-stretch: 1; }

        models := Rectangle {
            width: 38px;
            height: 32px;
            border-radius: 9px;
            background: models-touch.pressed ? Theme.field-active
                : models-touch.has-hover ? Theme.field-hover : Theme.field;

            Icon {
                x: (parent.width - self.width) / 2;
                y: (parent.height - self.height) / 2;
                glyph: Glyph.settings;
                size: 17px;
                tint: Theme.fg;
            }

            models-touch := TouchArea {
                clicked => { root.open-settings(); }
            }
        }

        if !root.minimal: export-button := Rectangle {
            width: 82px;
            height: 32px;
            border-radius: 9px;
            background: export-touch.pressed ? Theme.accent-hover : Theme.accent;

            HorizontalLayout {
                padding-left: 10px;
                padding-right: 10px;
                spacing: 6px;

                VerticalLayout {
                    alignment: center;
                    Icon {
                        glyph: Glyph.export;
                        size: 13px;
                        tint: Theme.on-accent;
                    }
                }

                Text {
                    text: "Export";
                    color: Theme.on-accent;
                    font-size: Theme.fs;
                    font-weight: Theme.weight-title;
                    vertical-alignment: center;
                }
            }

            export-touch := TouchArea {
                clicked => { root.export-clicked(); }
            }
        }
    }
}
'''
    return s[:start] + component
edit("src/crates/concat/ui/title-bar.slint", patch_titlebar)

# ---------------------------------------------------------------------------
# Fixed two-panel mobile workspace. Rust still provides compact preview +
# timeline seats, but panel splitters are not exposed in the UI.
# ---------------------------------------------------------------------------
def patch_workspace(_s):
    return r'''// SPDX-License-Identifier: AGPL-3.0-or-later
// Mobile caption-first workspace.

import { Theme } from "../theme/theme.slint";
import { Editor } from "../editor.slint";
import { Seat } from "seat.slint";

export component Workspace inherits Rectangle {
    background: Theme.page;

    init => { Editor.workspace-resized(root.width, root.height); }
    changed width => { Editor.workspace-resized(root.width, root.height); }
    changed height => { Editor.workspace-resized(root.width, root.height); }

    for seat in Editor.seats: Seat {
        x: seat.x;
        y: seat.y;
        width: seat.width;
        height: seat.height;
        kind: seat.kind;
        index: seat.index;

        picked(kind) => { Editor.dock-set(seat.index, kind); }
        dropped-on(from, side) => { Editor.dock-dropped(from, seat.index, side); }
        removed => { Editor.dock-remove(seat.index); }
    }
}
'''
edit("src/crates/concat/ui/workspace/workspace.slint", patch_workspace)

# Give preview more room than the timeline on phones.
def patch_dock(s):
    anchor = '''pub fn compact_dock() -> Dock {
    Dock::Split {
        columns: false,
        ratio: 0.5,'''
    repl = '''pub fn compact_dock() -> Dock {
    Dock::Split {
        columns: false,
        ratio: 0.62,'''
    return must_replace(s, anchor, repl, "compact dock ratio")
edit("src/crates/concat/src/dock.rs", patch_dock)

# ---------------------------------------------------------------------------
# Preview: hide desktop pane header and reduce transport to time + play/pause.
# ---------------------------------------------------------------------------
def patch_preview(s):
    s = must_replace(
        s,
        '''        PaneHeader {
            title: I18n.t("Preview");''',
        '''        PaneHeader {
            visible: false;
            height: 0px;
            title: I18n.t("Preview");''',
        "preview header hide",
    )
    marker = "        // ── the transport"
    start = s.index(marker)
    transport = r'''        // Mobile transport: only time and play/pause.
        Rectangle {
            height: 48px;
            background: Theme.panel;

            Rectangle {
                width: parent.width;
                height: 1px;
                background: Theme.line;
            }

            HorizontalLayout {
                padding-left: 14px;
                padding-right: 14px;
                spacing: 10px;

                Text {
                    horizontal-stretch: 1;
                    text: Fmt.frames-timecode(root.playhead, root.frame-rate)
                        + " / " + Fmt.frames-timecode(root.duration, root.frame-rate);
                    color: Theme.fg-muted;
                    font-family: Theme.font-technical;
                    font-size: Theme.fs;
                    vertical-alignment: center;
                }

                VerticalLayout {
                    alignment: center;
                    IconButton {
                        glyph: root.playing ? Glyph.pause : Glyph.play;
                        label: root.playing ? "Pause" : "Play";
                        icon-size: 17px;
                        accent: true;
                        clicked => { root.play-toggled(); }
                    }
                }
            }
        }
    }
}
'''
    return s[:start] + transport
edit("src/crates/concat/ui/workspace/preview-pane.slint", patch_preview)

# ---------------------------------------------------------------------------
# CapCut-like bottom action bar. Only features this app actually exposes.
# ---------------------------------------------------------------------------
def patch_tray(_s):
    return r'''// SPDX-License-Identifier: AGPL-3.0-or-later
// Mobile caption-first action bar.

import { Theme } from "../theme/theme.slint";
import { Glyph, Icon } from "../icons.slint";
import { Editor } from "../editor.slint";
import { TimelineTool } from "model.slint";

component ToolButton inherits Rectangle {
    in property <Glyph> glyph;
    in property <string> label;
    in property <bool> accent;
    callback clicked();

    height: 66px;
    border-radius: 10px;
    background: touch.pressed ? Theme.field-active
        : touch.has-hover ? Theme.field-hover : Colors.transparent;

    VerticalLayout {
        alignment: center;
        spacing: 4px;

        HorizontalLayout {
            alignment: center;
            Icon {
                glyph: root.glyph;
                size: 20px;
                tint: root.accent ? Theme.accent : Theme.fg;
            }
        }

        Text {
            text: root.label;
            color: root.accent ? Theme.accent : Theme.fg-muted;
            font-size: 11px;
            font-weight: root.accent ? Theme.weight-title : Theme.weight-body;
            horizontal-alignment: center;
        }
    }

    touch := TouchArea {
        clicked => { root.clicked(); }
    }
}

export component TimelineTray inherits Rectangle {
    in property <TimelineTool> tool: TimelineTool.select;
    in property <bool> snap: true;
    in property <bool> pan-mode: false;
    in property <int> selected-count;
    in property <string> merge-blocked-because;
    in property <bool> sound-selected;
    in property <bool> title-selected;
    in property <string> readout;

    callback tool-changed(tool: TimelineTool);
    callback snap-changed(snap: bool);
    callback pan-changed(on: bool);
    callback split();
    callback merge();
    callback delete-selected();
    callback captions();
    callback speak();
    callback add-track();
    callback fit();
    callback zoom(factor: float);

    height: 76px;
    background: Theme.panel;

    Rectangle {
        width: parent.width;
        height: 1px;
        background: Theme.line;
    }

    HorizontalLayout {
        padding-left: 4px;
        padding-right: 4px;
        padding-top: 4px;
        padding-bottom: 4px;
        spacing: 2px;

        ToolButton {
            horizontal-stretch: 1;
            glyph: Glyph.film;
            label: "Import";
            clicked => { Editor.import-media(); }
        }

        ToolButton {
            horizontal-stretch: 1;
            glyph: Glyph.text-mark;
            label: "Captions";
            accent: true;
            clicked => { root.captions(); }
        }

        ToolButton {
            horizontal-stretch: 1;
            glyph: Glyph.volume;
            label: "AI Speech";
            clicked => { root.speak(); }
        }

        ToolButton {
            horizontal-stretch: 1;
            glyph: Glyph.settings;
            label: "Models";
            clicked => { Editor.shortcut("settings"); }
        }

        ToolButton {
            horizontal-stretch: 1;
            glyph: Glyph.export;
            label: "Export";
            clicked => { Editor.shortcut("export"); }
        }
    }
}
'''
edit("src/crates/concat/ui/timeline/tray.slint", patch_tray)

# ---------------------------------------------------------------------------
# Timeline: one clean full-width lane stack + bottom feature bar.
# No timeline tabs, track headers, add-track controls, effects, or panel picker.
# ---------------------------------------------------------------------------
def patch_timeline(s):
    start = s.index("export component TimelinePane")
    component = r'''export component TimelinePane inherits Rectangle {
    in property <[TimelineTabData]> tabs;
    in property <int> current-tab;
    callback tab-selected(index: int);
    callback tab-renamed(index: int, name: string);
    callback tab-close-requested(index: int);
    callback tab-added();
    callback tab-moved(from: int, to: int);

    in property <TimelineTool> tool: TimelineTool.select;
    in property <bool> snap: true;
    in property <bool> pan-mode: false;
    in property <int> selected-count;
    in property <string> merge-blocked-because;
    in property <bool> sound-selected;
    in property <bool> title-selected;

    callback tool-changed(tool: TimelineTool);
    callback snap-changed(snap: bool);
    callback pan-changed(on: bool);
    callback split();
    callback merge();
    callback delete-selected();
    callback captions();
    callback speak();
    callback add-track();
    callback zoom-to-fit(width: length);
    callback zoom(factor: float, anchor-seconds: float);

    in property <[TrackData]> tracks;
    in property <[ClipData]> clips;
    in property <float> playhead;
    in property <float> frame-rate: 30;
    in property <float> scroll-left;
    in property <float> seconds-per-pixel: 0.05;
    in-out property <length> track-scroll;

    callback scrubbed(seconds: float);
    callback floor-pressed();
    callback clip-pressed(id: string, additive: bool, edge: int);
    callback clip-dragged(seconds: float, pixels: length);
    callback clip-released();
    callback razored(id: string, seconds: float);
    in property <[MenuItemData]> menu-items;
    in property <length> menu-height;
    in property <int> menu-token;
    callback clip-context(id: string);
    callback menu-selected(id: string);
    callback band-selected(from-seconds: float, to-seconds: float,
        from-y: length, to-y: length, additive: bool);
    callback scrolled(seconds: float);

    in property <DropData> drop;
    callback drag-hovered(payload: string, seconds: float, y: length);
    callback dropped(payload: string, seconds: float, y: length);
    callback track-flag-changed(index: int, visible: bool, muted: bool, locked: bool);
    callback track-sized(index: int, size: TrackSize);
    callback track-removed(index: int);

    callback pane-picked(kind: PaneKind);
    in property <int> pane-seat;
    in property <bool> pane-removable: false;
    callback pane-removed();

    in-out property <length> header-width: 0px;
    in property <length> min-header: 0px;
    in property <length> ruler-height: 24px;

    property <length> stack-h: root.tracks.length > 0
        ? root.tracks[root.tracks.length - 1].top
            + root.tracks[root.tracks.length - 1].height
        : 0px;
    property <length> overflow: Math.max(0px,
        root.stack-h - Math.max(0px, lanes.height - root.ruler-height));
    property <length> at: Math.max(0px, Math.min(root.overflow, root.track-scroll));

    Pane {
        Rectangle {
            height: 1px;
            background: Theme.line;
        }

        Rectangle {
            vertical-stretch: 1;
            clip: true;

            lanes := Lanes {
                x: 0;
                y: 0;
                width: parent.width;
                height: parent.height;

                tracks: root.tracks;
                clips: root.clips;
                tool: root.tool;
                playhead: root.playhead;
                frame-rate: root.frame-rate;
                scroll-left: root.scroll-left;
                seconds-per-pixel: root.seconds-per-pixel;
                track-scroll: root.at;
                ruler-height: root.ruler-height;
                pan-mode: false;

                scrubbed(seconds) => { root.scrubbed(seconds); }
                floor-pressed => { root.floor-pressed(); }
                clip-pressed(id, additive, edge) => { root.clip-pressed(id, additive, edge); }
                clip-dragged(seconds, pixels) => { root.clip-dragged(seconds, pixels); }
                clip-released => { root.clip-released(); }
                razored(id, seconds) => { root.razored(id, seconds); }
                menu-items: root.menu-items;
                menu-height: root.menu-height;
                menu-token: root.menu-token;
                clip-context(id) => { root.clip-context(id); }
                menu-selected(id) => { root.menu-selected(id); }
                band-selected(a, b, c, d, additive) => {
                    root.band-selected(a, b, c, d, additive);
                }
                scrolled(seconds) => { root.scrolled(seconds); }
                drop: root.drop;
                drag-hovered(payload, seconds, row) => {
                    root.drag-hovered(payload, seconds, row);
                }
                dropped(payload, seconds, row) => {
                    root.dropped(payload, seconds, row);
                }
                track-scrolled(pixels) => {
                    root.track-scroll = Math.max(0px,
                        Math.min(root.overflow, root.at + pixels));
                }
                zoomed(factor, anchor) => { root.zoom(factor, anchor); }
            }
        }

        TimelineTray {
            tool: root.tool;
            snap: root.snap;
            pan-mode: false;
            selected-count: root.selected-count;
            merge-blocked-because: root.merge-blocked-because;
            sound-selected: root.sound-selected;
            title-selected: root.title-selected;
            readout: Fmt.frames-timecode(root.playhead, root.frame-rate);

            captions => { root.captions(); }
            speak => { root.speak(); }
            fit => { root.zoom-to-fit(lanes.width); }
            zoom(factor) => { root.zoom(factor, -1); }
        }
    }
}
'''
    return s[:start] + component
edit("src/crates/concat/ui/workspace/timeline-pane.slint", patch_timeline)

# ---------------------------------------------------------------------------
# Model manager: v1 already removed unrelated tabs. Restore exact tab logic,
# narrow the sidebar for phones.
# ---------------------------------------------------------------------------
def patch_settings(s):
    s = must_replace(s, "current: root.data.tab != 3;", "current: root.data.tab == 2;", "caption model tab")
    s = must_replace(s, "if root.data.tab != 3: VerticalLayout {", "if root.data.tab == 2: VerticalLayout {", "caption model page")
    s = s.replace("width: 164px;", "width: 116px;", 1)
    return s
edit("src/crates/concat/ui/dialogs/settings.slint", patch_settings)

def patch_captions(s):
    return must_replace(s, 'title: I18n.t("Captions");', 'title: "Auto Captions";', "captions title")
edit("src/crates/concat/ui/dialogs/captions.slint", patch_captions)

def patch_speech(s):
    return must_replace(s, 'title: I18n.t("Text to speech");', 'title: "AI Speech";', "speech title")
edit("src/crates/concat/ui/dialogs/speech.slint", patch_speech)

# ---------------------------------------------------------------------------
# Android project flow:
# - unique hidden project name
# - app-specific project folder
# - first imported video sets project resolution/frame rate
# - import immediately adds/selects video
# ---------------------------------------------------------------------------
def patch_studio(s):
    s = must_replace(
        s,
        '''location: home_folder(if cfg!(target_os = "android") {
                "Concat"
            } else {''',
        '''location: home_folder(if cfg!(target_os = "android") {
                "AutoCaption Local"
            } else {''',
        "android project folder",
    )

    old_name = '''        let name = self.start.name.trim().to_owned();
        let name = if name.is_empty() {
            "Untitled project".to_owned()
        } else {
            name
        };'''
    new_name = '''        let name = if cfg!(target_os = "android") {
            let stamp = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|elapsed| elapsed.as_secs())
                .unwrap_or(0);
            format!("Caption {stamp}")
        } else {
            let name = self.start.name.trim().to_owned();
            if name.is_empty() {
                "Untitled project".to_owned()
            } else {
                name
            }
        };'''
    s = must_replace(s, old_name, new_name, "unique mobile project name")

    pat = re.compile(
        r'''    /// Probes the files on a worker, imports them, and immediately places
    /// them at 0:00\. Caption-first Android builds should not make the user
    /// visit a media bin before transcription can begin\.
    pub fn import\(&mut self, paths: Vec<std::path::PathBuf>\) \{.*?\n    \}\n\n    /// Decodes art''',
        re.S,
    )
    m = pat.search(s)
    if not m:
        raise SystemExit("could not find v1 Studio::import for v2")

    new_fn = r'''    /// Imports media for the caption-first mobile editor. The first video's
    /// shape becomes the project shape, then every imported file is placed at
    /// 0:00/the first free lane and the last created clip is selected.
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
                let adapt_output = studio.timeline().clips.is_empty();
                let mut commands = Vec::new();
                let mut imported_paths = Vec::new();
                let mut first_video: Option<(u32, u32, String)> = None;
                let mut failures = Vec::new();

                for result in results {
                    match result {
                        Ok(summary) => {
                            if first_video.is_none() {
                                first_video = summary.video.as_ref().map(|video| {
                                    (
                                        video.width,
                                        video.height,
                                        video.frame_rate_fraction.clone(),
                                    )
                                });
                            }
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

                    if adapt_output
                        && let Some((width, height, rate)) = first_video
                        && let Some(session) = studio.session.as_ref()
                    {
                        let mut video = session.video();
                        video.width = width;
                        video.height = height;
                        if let Some((num, den)) = rate.split_once('/')
                            && let (Ok(num), Ok(den)) =
                                (num.parse::<i64>(), den.parse::<i64>())
                            && num > 0
                            && den > 0
                        {
                            video.rate_num = num;
                            video.rate_den = den;
                        }
                        let timeline_id = studio.project().active_timeline_id.clone();
                        studio.apply(Command::SetTimelineVideo { timeline_id, video });
                    }

                    let mut selected = None;
                    for path in imported_paths {
                        let media_id = studio
                            .project()
                            .media
                            .iter()
                            .find(|item| item.path == path)
                            .map(|item| item.id.clone());
                        if let Some(media_id) = media_id
                            && let Some(clip_id) = studio.apply(Command::AddClipAtFirstFree {
                                media_id,
                                start: 0.0,
                            })
                        {
                            selected = Some(clip_id);
                        }
                    }
                    if let Some(clip_id) = selected {
                        studio.selection = vec![clip_id];
                    }
                }

                if let Some(error) = failures.first() {
                    studio.notify(&crate::host::probe_error(error), true);
                } else if added > 0 {
                    studio.notify("Video ready — choose Captions or AI Speech", false);
                }
            },
        );
    }

    /// Decodes art'''
    return s[:m.start()] + new_fn + s[m.end():]

edit("src/crates/concat/src/studio.rs", patch_studio)

# ---------------------------------------------------------------------------
# Wiring:
# - New Project immediately opens Android file picker
# - always use compact preview/timeline dock
# - Models button opens on Auto Captions tab
# ---------------------------------------------------------------------------
def patch_lib(s):
    s = must_replace(
        s,
        '''    app.on_start_create(on_window!(|state| {
        state.create_project();
    }));''',
        '''    app.on_start_create(on_window!(|state| {
        state.create_project();
        platform::pick_files_async(&i18n::t("Choose a video"), None, |paths| {
            on_ui(move |studio, _, _| studio.import(paths))
        });
    }));''',
        "new project opens file picker",
    )

    old_resize = '''    editor.on_workspace_resized(on_dock!(|state, width: f32, height: f32| {
        state.workspace = (width, height);
        // A narrow window - a phone, a tablet held upright, a desktop
        // window squeezed - gets the compact dock: two seats, the monitor
        // over the timeline, with the switcher on each to bring the
        // library or the inspector into it. The wide dock waits, whole,
        // for the window to widen again; every dock operation works on
        // whichever is showing.
        state.set_compact(width < studio::COMPACT_WIDTH);
    }));'''
    new_resize = '''    editor.on_workspace_resized(on_dock!(|state, width: f32, height: f32| {
        state.workspace = (width, height);
        state.set_compact(true);
    }));'''
    s = must_replace(s, old_resize, new_resize, "force mobile workspace")

    s = must_replace(
        s,
        '''                        "settings" => {
                            state.refresh_models();
                            state.settings.open = true;
                        }''',
        '''                        "settings" => {
                            state.refresh_models();
                            state.settings.tab = 2;
                            state.settings.open = true;
                        }''',
        "menu models default tab",
    )

    s = must_replace(
        s,
        '''    app.on_open_settings(on_window!(|state| {
        state.refresh_models();
        state.settings.open = true;
    }));''',
        '''    app.on_open_settings(on_window!(|state| {
        state.refresh_models();
        state.settings.tab = 2;
        state.settings.open = true;
    }));''',
        "top models default tab",
    )
    return s

edit("src/crates/concat/src/lib.rs", patch_lib)

print("AutoCaption Local v2 mobile UI patch complete")
