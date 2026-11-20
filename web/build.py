"""Monta as páginas finais em backend/app/static a partir das fontes em web/."""
import pathlib
w = pathlib.Path(__file__).parent
out = w.parent / "backend" / "app" / "static"
out.mkdir(parents=True, exist_ok=True)
css, core, ui, api = [(w / f).read_text() for f in ("shared.css", "core.js", "ui.js", "api.js")]
HEAD = '<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
for nome in ("gestor", "campo", "entrar", "admin", "ajuda"):
    h = (w / f"{nome}.html").read_text().replace("/*SHARED_CSS*/", css).replace("/*CORE*/", core).replace("/*UI*/", ui).replace("/*API*/", api)
    i = h.index("</style>") + len("</style>")
    h = HEAD + h[:i] + "\n</head>\n<body>\n" + h[i:] + "\n</body>\n</html>\n"
    (out / f"{nome}.html").write_text(h)
    print(nome, len(h))
