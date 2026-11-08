# A híbrida — identidade tradicional + Entrelinhas

Pedido: preservar a identidade afetiva da HOME e sua animação de scroll, incorporando a composição da direção A. Ainda é uma prévia, não autorização para substituir todas as telas.

- Manter marca B., frase “O clássico nunca sai de cena”, tokens quentes de `installation.css`, símbolos existentes em escala editorial, Ritual e personagem existentes.
- Trazer de A a tipografia Fraunces, hierarquia, margens, catálogo assimétrico e uma faixa clara entre momentos escuros. Não limitar a proposta à troca de cores.
- Reusar `createVideoRitual`, `createRuntime`, GSAP, WebM e poster existentes, sem modificar arquivos funcionais. A Estrelinha continua cameo decorativo.
- Prévia independente `prototypes/part2/a-hybrid.html`. Servidor de leitura com allowlist de assets em 127.0.0.1:4194. Three.js local já instalado pode ser usado pela prévia; ausência mantém a página utilizável. Não instalar pacote.
- Verificar Chromium desktop/mobile, scrub contínuo e reversível, capítulos, reduced motion, fallback de vídeo, CTA/menu/modal e screenshots. Testes do servidor garantem que não expõe API, segredos ou diretórios.
- Parar para avaliação visual da combinação, sem commit ou mudança na aplicação funcional.

Estado: prévia concluída e seis capturas inspecionadas; Chromium 39/39, Node 6/6, Python 5/5. Revisão visual do usuário pendente. Problema de Range corrigido no servidor de prévia; módulos funcionais preservados.

Ajuste posterior solicitado — Hero e intro:
- [x] Recuperar referência `3aa7a80`, sem reverter tipografia, cores, botões ou demais seções.
- [x] Retirar quadro/arco e restaurar poste/tesoura originais em composição responsiva.
- [x] Adaptar abertura por sessão com GSAP existente, reduced motion, interrupção e limite de execução.
- [x] Demonstrar falha antes (10 verificações) e aprovação depois (49/49), inspecionar capturas desktop/mobile e intro, repetir regressões do Ritual (39/39) e Node (6/6).
- [x] Manter implementação isolada para aprovação visual; sem commit ou alteração do produto.
