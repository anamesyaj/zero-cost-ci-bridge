from pathlib import Path

ROOT = Path("upstream")

def edit(rel, fn):
    p = ROOT / rel
    s = p.read_text()
    n = fn(s)
    if n == s:
        raise SystemExit(f"v6 patch made no change: {rel}")
    p.write_text(n)
    print("v6 patched", rel)

def must_replace(s, old, new, label):
    if old not in s:
        raise SystemExit(f"missing v6 anchor: {label}")
    return s.replace(old, new, 1)

# 1) Wire the visible mobile Delete button all the way through TimelinePane.
def patch_timeline(s):
    old = '''            captions => { root.captions(); }
            speak => { root.speak(); }
            fit => { root.zoom-to-fit(lanes.width); }'''
    new = '''            delete-selected => { root.delete-selected(); }
            captions => { root.captions(); }
            speak => { root.speak(); }
            fit => { root.zoom-to-fit(lanes.width); }'''
    return must_replace(s, old, new, "TimelineTray delete forwarding")

edit("src/crates/concat/ui/workspace/timeline-pane.slint", patch_timeline)

# 2) Consume Android/Slint Key.Back when not on Home.
def patch_app(s):
    old = '''    callback start-forget-recent(path: string);
    callback start-dismiss-error();
'''
    new = '''    callback start-forget-recent(path: string);
    callback start-dismiss-error();
    // Android system Back: close a sheet or return the current project Home.
    callback navigate-back();
'''
    s = must_replace(s, old, new, "navigate-back callback")

    old = '''        key-pressed(event) => {
            if (root.on-start) {
                return reject;
            }
'''
    new = '''        key-pressed(event) => {
            // Slint maps Android 14+ predictive/system Back to Key.Back.
            // Accept it while a project is open so Android does not finish
            // the Activity. On Home it remains unhandled, which exits normally.
            if (event.text == Key.Back) {
                if (root.on-start) {
                    return reject;
                }
                root.navigate-back();
                return accept;
            }
            if (root.on-start) {
                return reject;
            }
'''
    return must_replace(s, old, new, "Key.Back handling")

edit("src/crates/concat/ui/app.slint", patch_app)

# 3) Give navigate-back normal mobile navigation semantics.
def patch_lib(s):
    anchor = '''    app.on_start_forget_recent(on_window!(|state, path: SharedString| {
        state.forget_recent(path.as_str());
    }));
'''
    replacement = '''    app.on_start_forget_recent(on_window!(|state, path: SharedString| {
        state.forget_recent(path.as_str());
    }));

    app.on_navigate_back(on_window!(|state| {
        if state.export.open {
            state.handle(Msg::Export(ExportMsg::Close));
        } else if state.settings.open {
            state.settings.open = false;
        } else if state.project_sheet.open {
            state.project_sheet.open = false;
        } else if state.captions.open {
            state.captions_cancel();
        } else if state.speech.open {
            state.speech_cancel();
        } else {
            // close_project saves first, then returns to the launch/home screen.
            state.close_project();
        }
    }));
'''
    return must_replace(s, anchor, replacement, "navigate-back Rust handler")

edit("src/crates/concat/src/lib.rs", patch_lib)

print("AutoCaption Local v6 delete + Android Back navigation patch complete")
