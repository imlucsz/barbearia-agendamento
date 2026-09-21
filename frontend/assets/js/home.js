// js da home (index.html)
// por enquanto tá tudo mockado aqui em cima mesmo.
// TODO: quando o backend ficar pronto, trocar esses arrays por fetch() lá no api.js

const servicos = [
  { id: 1, nome: 'Corte Clássico', preco: 'R$ 80', duracao: '60 min', categoria: 'Corte', desc: 'Corte preciso com acabamento impecável. Inclui lavagem e finalização.' },
  { id: 2, nome: 'Barba & Bigode', preco: 'R$ 60', duracao: '45 min', categoria: 'Barba', desc: 'Modelagem artesanal com navalha quente, toalha quente e bálsamo hidratante.' },
  { id: 3, nome: 'Corte + Barba', preco: 'R$ 130', duracao: '90 min', categoria: 'Combo', desc: 'O combo completo — corte e barba com tratamento exclusivo.' },
  { id: 4, nome: 'Coloração', preco: 'A partir de R$ 150', duracao: '120 min', categoria: 'Cor', desc: 'Tintura profissional com produtos premium. Consulta inclusa.' },
  { id: 5, nome: 'Hidratação', preco: 'R$ 90', duracao: '60 min', categoria: 'Tratamento', desc: 'Tratamento intensivo para cabelos danificados. Brilho e maciez imediatos.' },
  { id: 6, nome: 'Ritual Completo', preco: 'R$ 220', duracao: '150 min', categoria: 'Combo', desc: 'Corte, barba, hidratação e massagem capilar. A experiência definitiva.' },
];

const categorias = ['Todos', 'Corte', 'Barba', 'Combo', 'Cor', 'Tratamento'];

const avaliacoes = [
  { nome: 'Carlos Mendes', servico: 'Corte Clássico', nota: 5, data: '2026-08-12', texto: 'Nunca fui a outro lugar depois que conheci o Nobre. O atendimento é de outro nível.' },
  { nome: 'Rafaela Souza', servico: 'Coloração', nota: 5, data: '2026-08-03', texto: 'A coloração ficou perfeita! A equipe entendeu exatamente o que eu queria.' },
  { nome: 'André Ferreira', servico: 'Ritual Completo', nota: 5, data: '2026-07-21', texto: 'O ritual completo é uma experiência que você não esquece. Saio renovado toda vez.' },
  { nome: 'Juliana Costa', servico: 'Hidratação', nota: 4, data: '2026-07-09', texto: 'Excelente serviço, muito cuidadoso e preciso. Voltarei com certeza.' },
];

// começa no domingo (0) pq o Date.getDay() funciona assim, senão eu ia me perder depois
const horarios = [
  { dia: 'Domingo', horas: 'Fechado' },
  { dia: 'Segunda-feira', horas: '09:00 – 20:00' },
  { dia: 'Terça-feira', horas: '09:00 – 20:00' },
  { dia: 'Quarta-feira', horas: '09:00 – 20:00' },
  { dia: 'Quinta-feira', horas: '09:00 – 20:00' },
  { dia: 'Sexta-feira', horas: '09:00 – 20:00' },
  { dia: 'Sábado', horas: '09:00 – 18:00' },
];


// ---------- navbar ----------
// (pesquisei um pouco e o jeito mais fácil foi só ligar/desligar uma classe no css)
const navbar = document.getElementById('navbar');
const menuBtn = document.getElementById('menu-btn');

// depois que rola um pouco a barra fica mais escura, senão o texto se perde na foto
window.addEventListener('scroll', function () {
  navbar.classList.toggle('rolou', window.scrollY > 40);
});

// botão do hamburguer: abre e fecha o menu
// (troca o ícone de tres linhas horizntais por × pra pessoa saber que dá pra fechar)
menuBtn.addEventListener('click', function () {
  const aberto = navbar.classList.toggle('aberto');
  menuBtn.innerHTML = aberto ? '&times;' : '&#9776;';
  menuBtn.setAttribute('aria-expanded', aberto);
});

// se clicou num link fecha o menu, senão ele fica aberto na cara da pessoa
document.querySelectorAll('.nav-links a').forEach(function (link) {
  link.addEventListener('click', function () {
    navbar.classList.remove('aberto');
    menuBtn.innerHTML = '&#9776;';
    menuBtn.setAttribute('aria-expanded', false);
  });
});


// ---------- serviços ----------
// monta os cards na mão mesmo, com template string (crase), fica bem tranquilo de mexer
const listaServicos = document.getElementById('lista-servicos');
const filtros = document.getElementById('filtros');

function mostrarServicos(categoria) {
  let lista = servicos;
  if (categoria !== 'Todos') {
    lista = servicos.filter(function (s) {
      return s.categoria === categoria;
    });
  }

  let html = '';
  lista.forEach(function (s) {
    html += `
      <div class="card">
        <div class="card-topo">
          <span class="tag">${s.categoria}</span>
          <span class="preco">${s.preco}</span>
        </div>
        <h3>${s.nome}</h3>
        <p>${s.desc}</p>
        <div class="card-rodape">
          <span class="duracao">${s.duracao}</span>
          <a href="schedule.html?servico=${s.id}" class="btn-agendar">Agendar</a>
        </div>
      </div>
    `;
  });
  listaServicos.innerHTML = html;
}

// cria os botões de filtro (Todos, Corte, Barba...)
// e já deixa o "Todos" marcado no começo
categorias.forEach(function (cat) {
  const btn = document.createElement('button');
  btn.className = 'filtro';
  btn.textContent = cat;
  if (cat === 'Todos') btn.classList.add('ativo');

  btn.addEventListener('click', function () {
    filtros.querySelectorAll('.filtro').forEach(function (b) {
      b.classList.remove('ativo');
    });
    btn.classList.add('ativo');
    mostrarServicos(cat);
  });

  filtros.appendChild(btn);
});

mostrarServicos('Todos');


// ---------- avaliações bem falsas ----------
function estrelas(nota) {
  let html = '';
  for (let i = 1; i <= 5; i++) {
    html += i <= nota ? '★' : '<span class="vazia">★</span>';
  }
  return html;
}

function mostrarAvaliacoes() {
  // média das notas (soma tudo e divide pela quantidade)
  let soma = 0;
  avaliacoes.forEach(function (a) { soma += a.nota; });
  const media = avaliacoes.length ? soma / avaliacoes.length : 0;

  document.getElementById('media-nota').textContent = media.toFixed(1);
  document.getElementById('media-estrelas').innerHTML = estrelas(Math.round(media));
  document.getElementById('total-avaliacoes').textContent = avaliacoes.length + ' avaliações';

  // barrinhas de 5 até 1 estrela, cada uma com a % de quem deu aquela nota
  let barras = '';
  for (let n = 5; n >= 1; n--) {
    const qtd = avaliacoes.filter(function (a) { return a.nota === n; }).length;
    const pct = avaliacoes.length ? (qtd / avaliacoes.length) * 100 : 0;
    barras += `
      <div class="barra-linha">
        <span>${n} ★</span>
        <div class="barra"><div style="width: ${pct}%"></div></div>
        <span>${qtd}</span>
      </div>
    `;
  }
  document.getElementById('barras').innerHTML = barras;

  // os comentários em si
  let lista = '';
  avaliacoes.forEach(function (a) {
    // pega a inicial do nome pro "avatar" (Carlos Mendes vira CM)
    const iniciais = a.nome.split(' ').map(function (p) { return p[0]; }).slice(0, 2).join('');
    const data = new Date(a.data + 'T12:00:00').toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });

    lista += `
      <div class="avaliacao">
        <div class="avaliacao-topo">
          <div class="pessoa">
            <div class="avatar">${iniciais}</div>
            <div>
              <p class="nome">${a.nome}</p>
              <p class="servico">${a.servico}</p>
              <div class="estrelas">${estrelas(a.nota)}</div>
            </div>
          </div>
          <span class="data">${data}</span>
        </div>
        <blockquote>"${a.texto}"</blockquote>
      </div>
    `;
  });
  document.getElementById('lista-avaliacoes').innerHTML = lista;
}

mostrarAvaliacoes();


// ---------- horários de funcionamento ----------
// vê que dia é hoje e destaca ele na lista
function mostrarHorarios() {
  const hoje = new Date().getDay();
  // no site a lista começa na segunda, então o domingo (0) vai pro final
  const ordem = [1, 2, 3, 4, 5, 6, 0];

  let html = '';
  ordem.forEach(function (i) {
    const h = horarios[i];
    const ehHoje = i === hoje;
    const fechado = h.horas === 'Fechado';

    html += `
      <div class="horario ${ehHoje ? 'hoje' : ''}">
        <span>${h.dia}${ehHoje ? ' (hoje)' : ''}</span>
        <span class="horas ${fechado ? 'fechado' : ''}">${h.horas}</span>
      </div>
    `;
  });
  document.getElementById('horarios').innerHTML = html;
}

mostrarHorarios();
