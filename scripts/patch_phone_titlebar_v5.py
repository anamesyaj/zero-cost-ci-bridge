from pathlib import Path

p = Path("upstream/src/crates/concat/ui/title-bar.slint")
s = p.read_text()

old = '                text: root.minimal ? "AutoCaption" : root.project-name;'
if old not in s:
    raise SystemExit("title text anchor missing")
s = s.replace(old, '                text: "AutoCaption";', 1)

old = '''        models := Rectangle {
            width: 38px;
            height: 32px;'''
new = '''        models := Rectangle {
            visible: false;
            width: 0px;
            height: 0px;'''
if old not in s:
    raise SystemExit("models button anchor missing")
s = s.replace(old, new, 1)

p.write_text(s)
print("Simplified Android title bar: AutoCaption + Export only")
