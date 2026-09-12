// ===== ELEMENTOS =====
const modal = document.getElementById('modal-cadastro');
const abrirCadastro = document.getElementById('abrir-cadastro');
const fecharCadastro = document.getElementById('fechar-cadastro');
const loginForm = document.querySelector('.login-form');
const registerForm = document.querySelector('.register-form');

// ===== CONTROLE DO MODAL =====

// Abrir modal de cadastro
abrirCadastro.addEventListener('click', (e) => {
    e.preventDefault();
    modal.classList.add('active');
});

// Fechar modal (botão "Voltar ao Login")
fecharCadastro.addEventListener('click', (e) => {
    e.preventDefault();
    modal.classList.remove('active');
});

// Fechar modal com a tecla Esc
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal.classList.contains('active')) {
        modal.classList.remove('active');
    }
});


// ===== MÁSCARA DE TELEFONE =====

const telefoneInput = document.getElementById('telefone');

telefoneInput.addEventListener('input', () => {
    let valor = telefoneInput.value.replace(/\D/g, ''); // remove tudo que não é número
    valor = valor.slice(0, 11); // limita a 11 dígitos (DDD + 9 números)

    if (valor.length > 6) {
        valor = valor.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3');
    } else if (valor.length > 2) {
        valor = valor.replace(/^(\d{2})(\d{0,5})/, '($1) $2');
    } else if (valor.length > 0) {
        valor = valor.replace(/^(\d{0,2})/, '($1');
    }

    telefoneInput.value = valor;
});


// ===== FUNÇÕES DE VALIDAÇÃO =====

function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

function mostrarErro(input, mensagem) {
    limparErro(input);
    input.classList.add('input-erro');

    const erroEl = document.createElement('span');
    erroEl.classList.add('mensagem-erro');
    erroEl.textContent = mensagem;

    input.parentElement.appendChild(erroEl);
}

function limparErro(input) {
    input.classList.remove('input-erro');
    const erroExistente = input.parentElement.querySelector('.mensagem-erro');
    if (erroExistente) {
        erroExistente.remove();
    }
}


// ===== SUBMIT: LOGIN =====

loginForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const email = document.getElementById('email');
    const senha = document.getElementById('senha');
    let valido = true;

    limparErro(email);
    limparErro(senha);

    if (!validarEmail(email.value.trim())) {
        mostrarErro(email, 'Digite um e-mail válido.');
        valido = false;
    }

    if (senha.value.trim().length < 6) {
        mostrarErro(senha, 'A senha deve ter no mínimo 6 caracteres.');
        valido = false;
    }

    if (!valido) return;

    const dadosLogin = {
        email: email.value.trim(),
        senha: senha.value
    };

    // Simulação local (sem backend por enquanto)
    console.log('Dados prontos para envio (login):', dadosLogin);
});


// ===== SUBMIT: CADASTRO =====

registerForm.addEventListener('submit', (e) => {
    e.preventDefault();

    const nome = document.getElementById('nome-completo');
    const telefone = document.getElementById('telefone');
    const emailCad = document.getElementById('email-cad');
    const senhaCad = document.getElementById('senha-cad');
    let valido = true;

    [nome, telefone, emailCad, senhaCad].forEach(limparErro);

    if (nome.value.trim().length < 3) {
        mostrarErro(nome, 'Digite seu nome completo.');
        valido = false;
    }

    if (telefone.value.trim().length < 10) {
        mostrarErro(telefone, 'Digite um número de telefone válido.');
        valido = false;
    }

    if (!validarEmail(emailCad.value.trim())) {
        mostrarErro(emailCad, 'Digite um e-mail válido.');
        valido = false;
    }

    if (senhaCad.value.trim().length < 6) {
        mostrarErro(senhaCad, 'A senha deve ter no mínimo 6 caracteres.');
        valido = false;
    }

    if (!valido) return;

    const dadosCadastro = {
        nome: nome.value.trim(),
        telefone: telefone.value.trim(),
        email: emailCad.value.trim(),
        senha: senhaCad.value
    };

    // Simulação local (sem backend por enquanto)
    console.log('Dados prontos para envio (cadastro):', dadosCadastro);

    modal.classList.remove('active');
    registerForm.reset();
});