import json
from html import escape as esc
from datetime import date, timedelta
from pyscript import document, window
from pyodide.ffi import create_proxy

KEY = "biblioteca_demo_v1"
DIAS_EMPRESTIMO = 14
MULTA_DIA = 0.50
TABS = [("dash", "Painel"), ("livros", "Livros"), ("membros", "Membros"), ("emp", "Empréstimos")]
state = {"tab": "dash", "q": ""}


# ---------- dados ----------
def seed():
    hoje = date.today()
    return {
        "books": [
            {"id": 1, "titulo": "Dom Casmurro", "autor": "Machado de Assis", "cat": "Romance", "copias": 3},
            {"id": 2, "titulo": "Grande Sertão: Veredas", "autor": "Guimarães Rosa", "cat": "Romance", "copias": 2},
            {"id": 3, "titulo": "O Cortiço", "autor": "Aluísio Azevedo", "cat": "Romance", "copias": 1},
            {"id": 4, "titulo": "Python Fluente", "autor": "Luciano Ramalho", "cat": "Tecnologia", "copias": 2},
            {"id": 5, "titulo": "Sapiens", "autor": "Yuval Harari", "cat": "História", "copias": 2},
        ],
        "members": [
            {"id": 1, "nome": "Ana Souza", "email": "ana@exemplo.com"},
            {"id": 2, "nome": "Bruno Lima", "email": "bruno@exemplo.com"},
        ],
        "loans": [
            {"id": 1, "book": 3, "member": 1, "saida": str(hoje - timedelta(days=20)),
             "venc": str(hoje - timedelta(days=6)), "devol": None, "multa": 0},
            {"id": 2, "book": 4, "member": 2, "saida": str(hoje - timedelta(days=3)),
             "venc": str(hoje + timedelta(days=11)), "devol": None, "multa": 0},
        ],
    }


def load():
    try:
        raw = window.localStorage.getItem(KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return seed()


def save():
    try:
        window.localStorage.setItem(KEY, json.dumps(db))
    except Exception:
        pass


db = load()


def next_id(lst):
    return max([x["id"] for x in lst], default=0) + 1


def brl(v):
    return "R$ " + f"{v:.2f}".replace(".", ",")


def fmt(d):
    return date.fromisoformat(d).strftime("%d/%m/%Y") if d else "—"


def ativos(book_id=None):
    return [l for l in db["loans"] if not l["devol"] and (book_id is None or l["book"] == book_id)]


def disponiveis(b):
    return b["copias"] - len(ativos(b["id"]))


def multa_atual(l):
    if l["devol"]:
        return l["multa"]
    atraso = (date.today() - date.fromisoformat(l["venc"])).days
    return max(0, atraso) * MULTA_DIA


def livro(i):
    return next((b for b in db["books"] if b["id"] == i), None)


def membro(i):
    return next((m for m in db["members"] if m["id"] == i), None)


def val(i):
    return document.getElementById(i).value.strip()


def msg(t):
    document.getElementById("msg").innerText = t


# ---------- ações ----------
def a_tab(arg):
    state["tab"] = arg
    state["q"] = ""
    msg("")
    render()


def a_add_book(_):
    t, a, c, n = val("f-titulo"), val("f-autor"), val("f-cat"), val("f-copias")
    if not t or not a or not n.isdigit() or int(n) < 1:
        return msg("Preencha título, autor e um número de exemplares válido.")
    db["books"].append({"id": next_id(db["books"]), "titulo": t, "autor": a,
                        "cat": c or "Geral", "copias": int(n)})
    save(); msg("Livro cadastrado."); render()


def a_del_book(arg):
    i = int(arg)
    if ativos(i):
        return msg("Não é possível remover: há exemplares emprestados.")
    db["books"] = [b for b in db["books"] if b["id"] != i]
    save(); msg("Livro removido."); render()


def a_add_member(_):
    n, e = val("f-nome"), val("f-email")
    if not n:
        return msg("Informe o nome do membro.")
    db["members"].append({"id": next_id(db["members"]), "nome": n, "email": e})
    save(); msg("Membro cadastrado."); render()


def a_del_member(arg):
    i = int(arg)
    if any(l["member"] == i for l in ativos()):
        return msg("Não é possível remover: membro com empréstimo ativo.")
    db["members"] = [m for m in db["members"] if m["id"] != i]
    save(); msg("Membro removido."); render()


def a_lend(_):
    b, m = val("s-book"), val("s-member")
    if not b or not m:
        return msg("Selecione um livro e um membro.")
    hoje = date.today()
    db["loans"].append({"id": next_id(db["loans"]), "book": int(b), "member": int(m),
                        "saida": str(hoje), "venc": str(hoje + timedelta(days=DIAS_EMPRESTIMO)),
                        "devol": None, "multa": 0})
    save(); msg(f"Empréstimo registrado. Devolução em {DIAS_EMPRESTIMO} dias."); render()


def a_return(arg):
    for l in db["loans"]:
        if l["id"] == int(arg):
            l["multa"] = multa_atual(l)
            l["devol"] = str(date.today())
            m = f" Multa: {brl(l['multa'])}." if l["multa"] else ""
            msg("Devolução registrada." + m)
    save(); render()


def a_reset(_):
    global db
    db = seed(); save(); msg("Dados de demonstração restaurados."); render()


ACTIONS = {"tab": a_tab, "add-book": a_add_book, "del-book": a_del_book,
           "add-member": a_add_member, "del-member": a_del_member,
           "lend": a_lend, "return": a_return, "reset": a_reset}


# ---------- telas ----------
def v_dash():
    total = sum(b["copias"] for b in db["books"])
    emp = len(ativos())
    atras = [l for l in ativos() if date.fromisoformat(l["venc"]) < date.today()]
    multas = sum(multa_atual(l) for l in db["loans"])
    stats = [(len(db["books"]), "Títulos"), (total - emp, "Exemplares disponíveis"),
             (emp, "Emprestados"), (len(atras), "Em atraso"), (brl(multas), "Multas (total)")]
    h = '<div class="grid">' + "".join(
        f'<div class="stat"><b>{v}</b><span>{k}</span></div>' for v, k in stats) + "</div>"
    h += '<div class="card" style="margin-top:16px"><h2>Empréstimos em atraso</h2>'
    if atras:
        h += '<div class="wrap"><table><tr><th>Livro</th><th>Membro</th><th>Venceu em</th><th>Multa</th></tr>'
        for l in atras:
            h += (f'<tr><td>{esc(livro(l["book"])["titulo"])}</td><td>{esc(membro(l["member"])["nome"])}</td>'
                  f'<td>{fmt(l["venc"])}</td><td>{brl(multa_atual(l))}</td></tr>')
        h += "</table></div>"
    else:
        h += '<span class="sub">Nenhum atraso. 🎉</span>'
    h += '</div><button data-action="reset">Restaurar dados de demonstração</button>'
    return h


def linhas_livros():
    q = state["q"].lower()
    h = ""
    for b in db["books"]:
        if q and q not in (b["titulo"] + b["autor"] + b["cat"]).lower():
            continue
        d = disponiveis(b)
        tag = f'<span class="tag">{d} de {b["copias"]}</span>' if d else '<span class="tag bad">esgotado</span>'
        h += (f'<tr><td>{esc(b["titulo"])}</td><td>{esc(b["autor"])}</td><td>{esc(b["cat"])}</td>'
              f'<td>{tag}</td><td><button class="del" data-action="del-book" data-id="{b["id"]}">Remover</button></td></tr>')
    return h or '<tr><td colspan="5" class="sub">Nenhum livro encontrado.</td></tr>'


def v_livros():
    return f'''<div class="card"><h2>Novo livro</h2><div class="row">
      <input id="f-titulo" placeholder="Título"><input id="f-autor" placeholder="Autor">
      <input id="f-cat" placeholder="Categoria"><input id="f-copias" type="number" min="1" value="1" style="width:90px">
      <button class="pri" data-action="add-book">Cadastrar</button></div></div>
    <div class="card"><div class="row"><h2 style="margin:0">Acervo</h2>
      <input id="q" placeholder="Buscar…" value="{esc(state["q"])}" style="margin-left:auto"></div>
      <div class="wrap"><table><tr><th>Título</th><th>Autor</th><th>Categoria</th><th>Disponíveis</th><th></th></tr>
      <tbody id="rows">{linhas_livros()}</tbody></table></div></div>'''


def v_membros():
    h = '''<div class="card"><h2>Novo membro</h2><div class="row">
      <input id="f-nome" placeholder="Nome"><input id="f-email" placeholder="E-mail">
      <button class="pri" data-action="add-member">Cadastrar</button></div></div>
      <div class="card"><div class="wrap"><table><tr><th>Nome</th><th>E-mail</th><th>Empréstimos ativos</th><th></th></tr>'''
    for m in db["members"]:
        n = len([l for l in ativos() if l["member"] == m["id"]])
        h += (f'<tr><td>{esc(m["nome"])}</td><td>{esc(m["email"])}</td><td>{n}</td>'
              f'<td><button class="del" data-action="del-member" data-id="{m["id"]}">Remover</button></td></tr>')
    return h + "</table></div></div>"


def v_emp():
    lb = "".join(f'<option value="{b["id"]}">{esc(b["titulo"])} ({disponiveis(b)} disp.)</option>'
                 for b in db["books"] if disponiveis(b) > 0)
    lm = "".join(f'<option value="{m["id"]}">{esc(m["nome"])}</option>' for m in db["members"])
    h = f'''<div class="card"><h2>Novo empréstimo</h2><div class="row">
      <select id="s-book"><option value="">Livro…</option>{lb}</select>
      <select id="s-member"><option value="">Membro…</option>{lm}</select>
      <button class="pri" data-action="lend">Emprestar</button></div></div>
      <div class="card"><div class="wrap"><table><tr><th>Livro</th><th>Membro</th><th>Saída</th><th>Vencimento</th><th>Status</th><th>Multa</th><th></th></tr>'''
    for l in sorted(db["loans"], key=lambda x: (x["devol"] is not None, x["venc"])):
        b, m = livro(l["book"]), membro(l["member"])
        if l["devol"]:
            st, acao = f'<span class="tag">devolvido {fmt(l["devol"])}</span>', ""
        elif date.fromisoformat(l["venc"]) < date.today():
            st = '<span class="tag bad">atrasado</span>'
            acao = f'<button data-action="return" data-id="{l["id"]}">Devolver</button>'
        else:
            st = '<span class="tag">em dia</span>'
            acao = f'<button data-action="return" data-id="{l["id"]}">Devolver</button>'
        h += (f'<tr><td>{esc(b["titulo"] if b else "(removido)")}</td><td>{esc(m["nome"] if m else "(removido)")}</td>'
              f'<td>{fmt(l["saida"])}</td><td>{fmt(l["venc"])}</td><td>{st}</td>'
              f'<td>{brl(multa_atual(l))}</td><td>{acao}</td></tr>')
    return h + "</table></div></div>"


VIEWS = {"dash": v_dash, "livros": v_livros, "membros": v_membros, "emp": v_emp}


def render():
    document.getElementById("nav").innerHTML = "".join(
        f'<button class="{"on" if k == state["tab"] else ""}" data-action="tab" data-id="{k}">{n}</button>'
        for k, n in TABS)
    document.getElementById("view").innerHTML = VIEWS[state["tab"]]()


# ---------- eventos ----------
def on_click(ev):
    el = ev.target.closest("[data-action]")
    if el:
        ACTIONS[el.getAttribute("data-action")](el.getAttribute("data-id"))


def on_input(ev):
    if ev.target.id == "q":
        state["q"] = ev.target.value
        document.getElementById("rows").innerHTML = linhas_livros()


document.addEventListener("click", create_proxy(on_click))
document.addEventListener("input", create_proxy(on_input))
render()
