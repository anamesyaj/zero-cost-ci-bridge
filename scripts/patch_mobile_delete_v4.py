from pathlib import Path

ROOT = Path("upstream")
p = ROOT / "src/crates/concat/ui/timeline/tray.slint"
s = p.read_text()

old = '''component ToolButton inherits Rectangle {
    in property <Glyph> glyph;
    in property <string> label;
    in property <bool> accent;
    callback clicked();

    height: 66px;
    border-radius: 10px;
    background: touch.pressed ? Theme.field-active
        : touch.has-hover ? Theme.field-hover : Colors.transparent;
'''
new = '''component ToolButton inherits Rectangle {
    in property <Glyph> glyph;
    in property <string> label;
    in property <bool> accent;
    in property <bool> enabled: true;
    callback clicked();

    height: 66px;
    border-radius: 10px;
    opacity: root.enabled ? 1.0 : 0.38;
    background: root.enabled && touch.pressed ? Theme.field-active
        : root.enabled && touch.has-hover ? Theme.field-hover : Colors.transparent;
'''
if old not in s:
    raise SystemExit("ToolButton anchor missing")
s = s.replace(old, new, 1)

old = '''    touch := TouchArea {
        clicked => { root.clicked(); }
    }
}'''
new = '''    touch := TouchArea {
        enabled: root.enabled;
        clicked => { root.clicked(); }
    }
}'''
if old not in s:
    raise SystemExit("TouchArea anchor missing")
s = s.replace(old, new, 1)

old = '''        ToolButton {
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
'''
new = '''        ToolButton {
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
            glyph: Glyph.trash;
            label: "Delete";
            enabled: root.selected-count > 0;
            clicked => { root.delete-selected(); }
        }
'''
if old not in s:
    raise SystemExit("toolbar insertion anchor missing")
s = s.replace(old, new, 1)

p.write_text(s)
print("Added mobile timeline Delete action")
