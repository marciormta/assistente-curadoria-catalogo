// Assistente de Curadoria do Catálogo — frontend mínimo (sem framework).

const $conversa = document.getElementById("conversa");
const $pergunta = document.getElementById("pergunta");
const $enviar = document.getElementById("enviar");
const $api = document.getElementById("api");

// Auto-resize do textarea
$pergunta.addEventListener("input", () => {
  $pergunta.style.height = "auto";
  $pergunta.style.height = $pergunta.scrollHeight + "px";
});

// Enter envia, Shift+Enter quebra linha
$pergunta.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    enviar();
  }
});
$enviar.addEventListener("click", enviar);

// Sugestões clicáveis
document.querySelectorAll("#sugestoes button").forEach((b) => {
  b.addEventListener("click", () => {
    $pergunta.value = b.textContent;
    enviar();
  });
});

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

function addUsuario(texto) {
  const div = document.createElement("div");
  div.className = "msg usuario";
  div.innerHTML = `<div class="bolha">${escapeHtml(texto)}</div>`;
  $conversa.appendChild(div);
  scrollFim();
}

function addCarregando() {
  const div = document.createElement("div");
  div.className = "msg assistente";
  div.innerHTML = `<div class="bolha carregando">Consultando o catálogo…</div>`;
  $conversa.appendChild(div);
  scrollFim();
  return div;
}

function renderResposta(div, data) {
  const refsHtml = (data.referencias || [])
    .map((r) => {
      const autores = (r.autores || []).join(", ");
      const generos = (r.generos || []).join(", ");
      const ano = r.ano_publicacao ? ` · ${r.ano_publicacao}` : "";
      return `<div class="ref-card">
        <div class="rt">${escapeHtml(r.titulo)}</div>
        <div class="rm">${escapeHtml(autores)}${ano}${generos ? " · " + escapeHtml(generos) : ""} · ${escapeHtml(r.id)}</div>
      </div>`;
    })
    .join("");

  const filtros =
    data.filtros && Object.keys(data.filtros).length
      ? Object.entries(data.filtros)
          .map(([k, v]) => `<span class="tag">${escapeHtml(k)}: ${escapeHtml(String(v))}</span>`)
          .join("")
      : "";

  div.innerHTML = `
    <div class="bolha">
      <p>${escapeHtml(data.resposta).replace(/\n/g, "<br>")}</p>
      ${refsHtml ? `<div class="refs"><div class="refs-titulo">Livros usados</div>${refsHtml}</div>` : ""}
      <div class="meta">Intenção: <span class="tag">${escapeHtml(data.intencao || "—")}</span>${filtros}</div>
    </div>`;
  scrollFim();
}

function renderErro(div, msg) {
  div.classList.add("erro");
  div.innerHTML = `<div class="bolha">Não consegui responder agora. ${escapeHtml(msg)}</div>`;
  scrollFim();
}

function scrollFim() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
}

async function enviar() {
  const texto = $pergunta.value.trim();
  if (!texto) return;

  const intro = document.querySelector(".msg.intro");
  if (intro) intro.remove();

  addUsuario(texto);
  $pergunta.value = "";
  $pergunta.style.height = "auto";
  $enviar.disabled = true;

  const $load = addCarregando();
  const base = ($api.value || "http://localhost:8000").replace(/\/$/, "");

  try {
    const resp = await fetch(`${base}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta: texto }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    renderResposta($load, data);
  } catch (err) {
    renderErro($load, String(err.message || err));
  } finally {
    $enviar.disabled = false;
    $pergunta.focus();
  }
}
