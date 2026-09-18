from pathlib import Path

ROOT = Path("upstream")

def edit(rel, fn):
    p = ROOT / rel
    s = p.read_text()
    n = fn(s)
    if n == s:
        raise SystemExit(f"caption-render patch made no change: {rel}")
    p.write_text(n)
    print("patched", rel)

# Android may expose no discoverable system fonts to fontdb. Always preload
# one font already shipped by Concat so title/caption rendering cannot fail
# with NoFont on phones.
def patch_text_renderer(s):
    old = '''    pub fn new() -> Fonts {
        let mut db = fontdb::Database::new();
        db.load_system_fonts();
        Fonts { db }
    }'''
    new = '''    pub fn new() -> Fonts {
        let mut db = fontdb::Database::new();
        db.load_system_fonts();

        // A packaged fallback is essential on Android: fontdb's system font
        // scan can be empty even though Android itself has UI fonts. Synonym
        // is already shipped with Concat and licensed for app embedding.
        db.load_font_data(
            include_bytes!("../../concat/ui/fonts/Synonym-SemiBold.ttf").to_vec()
        );

        Fonts { db }
    }'''
    if old not in s:
        raise SystemExit("Fonts::new anchor missing")
    return s.replace(old, new, 1)

edit("src/crates/concat-text/src/lib.rs", patch_text_renderer)

# Make generated captions explicitly use the packaged face. Add a modest
# outline and width cap so they remain readable over bright/mobile footage.
def patch_caption_style(s):
    old = '''            style: Some(TextStyle {
                content: text,
                font_family: "Helvetica Neue".to_owned(),
                font_size,
                font_weight: 600.0,
                ..TextStyle::default()
            }),'''
    new = '''            style: Some(TextStyle {
                content: text,
                font_family: "Synonym".to_owned(),
                font_size,
                font_weight: 600.0,
                color: "#ffffff".to_owned(),
                stroke_width: 0.0025,
                stroke_color: "#000000".to_owned(),
                shadow: true,
                max_width: 0.88,
                ..TextStyle::default()
            }),'''
    if old not in s:
        raise SystemExit("caption style anchor missing")
    return s.replace(old, new, 1)

edit("src/crates/concat/src/studio.rs", patch_caption_style)

print("AutoCaption Local bundled caption-font/render patch complete")
